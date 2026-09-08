from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from jose import JWTError, jwt

from database.connection import get_db
from models.member import UserModel
from schemas.member import (
    UserDeleteItem,
    UserLoginItem,
    UserSignupItem,
    UserUpdateItem,
)
from fortune.services.daily_fortune_service import delete_daily_fortune
from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    ACCESS_SECRET,
    ALGORITHM,
    get_current_user,
)

member_router = APIRouter()
security = HTTPBearer(auto_error=False)

# 1. 회원가입
@member_router.post("/signup")
async def signup(item: UserSignupItem, db: Session = Depends(get_db)):
    # 이메일 중복 체크
    if db.query(UserModel).filter(UserModel.email == item.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 이메일입니다."
        )

    # login_id가 없으면 이메일 아이디 부분으로 기본 지정
    login_id = item.loginId if item.loginId else item.email.split("@")[0]

    # login_id 중복 체크
    if db.query(UserModel).filter(UserModel.login_id == login_id).first():
        login_id = f"{login_id}_{item.phone[-4:]}"

    new_user = UserModel(
        login_id=login_id,
        email=item.email,
        password_hash=hash_password(item.pwd),
        name=item.name,
        phone=item.phone,
        birth_date=item.birthDate
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"isSignup": True, "message": "회원가입이 완료되었습니다."}

# 2. 로그인
@member_router.post("/login")
async def login(item: UserLoginItem, response: Response, db: Session = Depends(get_db)):
    # 1. DB에서 이메일로 사용자 조회
    user = db.query(UserModel).filter(UserModel.email == item.email).first()

    # 2. 사용자가 없거나 비밀번호가 틀린 경우
    if not user or not verify_password(item.pwd, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다."
        )

    # 3. 토큰 발급
    access_token = create_access_token(user.email, user.role if hasattr(user, 'role') else "USER")
    refresh_token = create_refresh_token(user.email, user.role if hasattr(user, 'role') else "USER")

    # 4. Refresh Token 쿠키 설정 (로그인 유지 체크 여부에 따른 분기)
    cookie_params = {
        "key": "refreshToken",
        "value": refresh_token,
        "httponly": True,
        "samesite": "lax",
        "secure": False,
    }

    # '로그인 유지'를 체크한 경우에만 7일간 유지, 체크 안 하면 세션 쿠키(브라우저 닫으면 삭제)
    if getattr(item, "remember", False):
        cookie_params["max_age"] = 60 * 60 * 24 * 7

    response.set_cookie(**cookie_params)

    # 5. 응답 반환
    return {
        "isLogin": True,
        "accessToken": access_token,
        "user": {
            "userId": user.user_id,
            "loginId": user.login_id,
            "email": user.email,
            "name": user.name
        }
    }

#3. 내 정보 조회 (토큰 검증)
@member_router.get("/me")
async def get_my_info(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 정보가 없습니다."
        )

    try:
        payload = jwt.decode(credentials.credentials, ACCESS_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 만료된 토큰입니다."
        )

    user = db.query(UserModel).filter(UserModel.email == payload.get("sub")).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다."
        )

    return {
        "email": user.email,
        "name": user.name,
        "birth_date": user.birth_date,
        "phone": user.phone,
        "role": payload.get("role", "USER"),
        "hasFortuneAccess": user.has_fortune_access,
    }


@member_router.put("/me")
async def update_my_info(
    item: UserUpdateItem,
    response: Response,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    duplicate_email = (
        db.query(UserModel)
        .filter(
            UserModel.email == item.email,
            UserModel.user_id != user.user_id,
        )
        .first()
    )
    if duplicate_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 이메일입니다.",
        )

    email_changed = user.email != item.email
    birth_date_changed = user.birth_date != item.birthDate

    user.email = item.email
    user.name = item.name
    user.phone = item.phone
    user.birth_date = item.birthDate
    if item.password:
        user.password_hash = hash_password(item.password)

    if birth_date_changed:
        today = datetime.now(ZoneInfo("Asia/Seoul")).date()
        delete_daily_fortune(db, user.user_id, today)

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 회원 정보입니다.",
        ) from error
    except Exception:
        db.rollback()
        raise

    access_token = None
    if email_changed:
        role = user.role if hasattr(user, "role") else "USER"
        access_token = create_access_token(user.email, role)
        refresh_token = create_refresh_token(user.email, role)
        response.set_cookie(
            key="refreshToken",
            value=refresh_token,
            httponly=True,
            samesite="lax",
            secure=False,
            max_age=60 * 60 * 24 * 7,
        )

    return {
        "message": "회원 정보가 수정되었습니다.",
        "accessToken": access_token,
        "user": {
            "userId": user.user_id,
            "loginId": user.login_id,
            "email": user.email,
            "name": user.name,
            "birthDate": user.birth_date,
            "phone": user.phone,
        },
    }


@member_router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    item: UserDeleteItem,
    response: Response,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(item.pwd, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비밀번호가 올바르지 않습니다.",
        )

    try:
        db.delete(user)
        db.commit()
    except Exception:
        db.rollback()
        raise

    response.delete_cookie(
        key="refreshToken",
        httponly=True,
        samesite="lax",
        secure=False,
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response

#4. 로그아웃
@member_router.post("/logout")
async def logout(response: Response):
    # 쿠키에 저장된 refreshToken 삭제 (max_age=0 및 과거 만료일 설정)
    response.set_cookie(
        key="refreshToken",
        value="",
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=0,
        expires=datetime.now(timezone.utc) - timedelta(days=1)
    )
    return {"isLogout": True, "message": "성공적으로 로그아웃되었습니다."}

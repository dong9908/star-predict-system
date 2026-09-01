from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt

from database.connection import get_db
from models.member import UserModel
from schemas.member import UserSignupItem, UserLoginItem
from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    ACCESS_SECRET,
    ALGORITHM
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

    # 4. Refresh Token 쿠키 설정
    response.set_cookie(
        key="refreshToken",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 7
    )

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
#3. 로그아웃
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
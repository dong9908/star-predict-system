from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.connection import get_db
from models.member import UserModel
from payment.models import PaymentModel
from sqlalchemy import func
from models.constellation import ConstellationModel  # 별자리 모델 임포트
from schemas.admin import ConstellationCreateUpdateSchema  # 분리한 스키마 임포트

admin_router = APIRouter()

@admin_router.get("/users")
def get_all_users(db: Session = Depends(get_db)):
    """전체 회원 목록 조회 (관리자 계정 제외)"""
    users = db.query(UserModel).filter(UserModel.email != "admin@naver.com").all()
    
    return [
        {
            "user_id": user.user_id,
            "email": user.email,
            "name": user.name,
            "created_at": None 
        }
        for user in users
    ]

@admin_router.get("/payments")
def get_all_payments(db: Session = Depends(get_db)):
    """전체 카카오페이 결제 내역 조회 (관리자 전용)"""
    payments = db.query(PaymentModel).all()
    return [
        {
            "tid": pay.tid,
            "user_id": pay.user_id,
            "item_name": pay.item_name,
            "total_amount": pay.amount,
            "status": pay.status.value if hasattr(pay.status, "value") else pay.status,
            "created_at": str(pay.created_at) if pay.created_at else None
        }
        for pay in payments
    ]

@admin_router.delete("/users/{user_id}")
def delete_user_by_admin(user_id: int, db: Session = Depends(get_db)):
    """관리자에 의한 회원 강제 탈퇴(삭제)"""
    user = db.query(UserModel).filter(UserModel.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="해당 회원을 찾을 수 없습니다.")
    
    db.delete(user)
    db.commit()
    return {"message": "회원이 성공적으로 삭제되었습니다."}

@admin_router.post("/constellations")
def create_constellation(data: ConstellationCreateUpdateSchema, db: Session = Depends(get_db)):
    """마지막 별자리 ID를 조회하여 +1 한 값으로 새로운 별자리 추가"""
    
    # 1. 현재 테이블에 존재하는 가장 큰 constellation_id 조회 (없으면 0)
    max_id = db.query(func.max(ConstellationModel.constellation_id)).scalar() or 0
    next_id = max_id + 1

    # 2. 다음 ID(+1)를 적용하여 별자리 생성
    new_constellation = ConstellationModel(
        constellation_id=next_id,
        name_ko=data.name_ko,
        name_en=data.name_en,
        description=data.description,
        mythology=data.mythology,
        difficulty=data.difficulty,
        image_url=data.image_url,
        abbreviation=data.abbreviation
    )
    db.add(new_constellation)
    db.commit()
    db.refresh(new_constellation)
    
    return {"message": f"ID {next_id}번으로 별자리가 성공적으로 추가되었습니다.", "constellation": new_constellation}

@admin_router.put("/constellations/{constellation_id}")
def update_constellation(constellation_id: int, data: ConstellationCreateUpdateSchema, db: Session = Depends(get_db)):
    """기존 별자리 정보 수정 (관리자 전용)"""
    constellation = db.query(ConstellationModel).filter(ConstellationModel.constellation_id == constellation_id).first()
    if not constellation:
        raise HTTPException(status_code=404, detail="해당 별자리를 찾을 수 없습니다.")
    
    constellation.name_ko = data.name_ko
    constellation.name_en = data.name_en
    constellation.description = data.description
    constellation.mythology = data.mythology
    constellation.difficulty = data.difficulty
    constellation.image_url = data.image_url
    constellation.abbreviation = data.abbreviation
    
    db.commit()
    return {"message": "별자리 정보가 성공적으로 수정되었습니다.", "constellation": constellation}

@admin_router.delete("/constellations/{constellation_id}")
def delete_constellation(constellation_id: int, db: Session = Depends(get_db)):
    """특정 별자리 삭제 (관리자 전용)"""
    constellation = db.query(ConstellationModel).filter(ConstellationModel.constellation_id == constellation_id).first()
    if not constellation:
        raise HTTPException(status_code=404, detail="해당 별자리를 찾을 수 없습니다.")
    
    db.delete(constellation)
    db.commit()
    return {"message": "별자리가 성공적으로 삭제되었습니다."}
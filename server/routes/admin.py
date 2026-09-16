from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.connection import get_db
from models.member import UserModel
from payment.models import PaymentModel  # PaymentModel 클래스 임포트

admin_router = APIRouter()

@admin_router.get("/users")
def get_all_users(db: Session = Depends(get_db)):
    """전체 회원 목록 조회 (관리자 계정 제외)"""
    # 이메일이 'admin@naver.com'인 계정을 제외하고 조회합니다.
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
            "total_amount": pay.amount,  # PaymentModel의 컬럼명인 amount로 매핑
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
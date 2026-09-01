from pydantic import BaseModel, EmailStr, field_validator
from datetime import date, datetime
from typing import Optional

# 회원가입 요청 DTO
class UserSignupItem(BaseModel):
    loginId: Optional[str] = None
    email: EmailStr
    pwd: str
    name: str
    phone: str
    birthDate: date

    @field_validator("birthDate", mode="before")
    def parse_birth_date(cls, v):
        if isinstance(v, str):
            v = v.strip()
            # 8자리 숫자(YYYYMMDD)로 들어올 경우 YYYY-MM-DD로 변환
            if len(v) == 8 and v.isdigit():
                return date(int(v[:4]), int(v[4:6]), int(v[6:8]))
        return v

# 로그인 요청 DTO
class UserLoginItem(BaseModel):
    email: EmailStr
    pwd: str

# 사용자 응답 DTO
class UserResponse(BaseModel):
    user_id: int
    login_id: str
    email: str
    name: str
    phone: str
    birth_date: date
    created_at: datetime
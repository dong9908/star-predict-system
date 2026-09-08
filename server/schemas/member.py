from pydantic import BaseModel, EmailStr, Field, field_validator
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
    remember: Optional[bool] = False


class UserUpdateItem(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=50)
    phone: str = Field(min_length=10, max_length=20)
    birthDate: date
    password: Optional[str] = Field(default=None, min_length=8, max_length=72)

    @field_validator("name", "phone", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        digits = "".join(character for character in value if character.isdigit())
        if len(digits) not in (10, 11):
            raise ValueError("유효한 휴대폰 번호를 입력해주세요.")
        return value

    @field_validator("birthDate")
    @classmethod
    def validate_birth_date(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("생년월일은 미래 날짜일 수 없습니다.")
        return value


class UserDeleteItem(BaseModel):
    pwd: str = Field(min_length=1, max_length=72)

# 사용자 응답 DTO
class UserResponse(BaseModel):
    user_id: int
    login_id: str
    email: str
    name: str
    phone: str
    birth_date: date
    created_at: datetime

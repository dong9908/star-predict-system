import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv
import bcrypt
from jose import jwt

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

ACCESS_SECRET = os.getenv("ACCESS_SECRET", "dev-access-secret-key-astra-2026")
REFRESH_SECRET = os.getenv("REFRESH_SECRET", "dev-refresh-secret-key-astra-2026")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

def hash_password(password: str) -> str:
    """bcrypt를 이용해 비밀번호 해시화 (72바이트 초과 방지 처리 포함)"""
    # 72바이트 초과 시 잘라내기 처리
    pwd_bytes = password.encode('utf-8')
    if len(pwd_bytes) > 72:
        pwd_bytes = pwd_bytes[:72]
    
    hashed = bcrypt.hashpw(pwd_bytes, bcrypt.gensalt())
    return hashed.decode('utf-8')

def verify_password(raw_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    pwd_bytes = raw_password.encode('utf-8')
    if len(pwd_bytes) > 72:
        pwd_bytes = pwd_bytes[:72]
    
    return bcrypt.checkpw(pwd_bytes, hashed_password.encode('utf-8'))

def _create_token(subject: str, role: str, secret: str, expires_delta: timedelta) -> str:
    payload = {
        "sub": subject,
        "role": role,
        "exp": datetime.now(timezone.utc) + expires_delta,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)

def create_access_token(email: str, role: str = "USER") -> str:
    return _create_token(email, role, ACCESS_SECRET, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

def create_refresh_token(email: str, role: str = "USER") -> str:
    return _create_token(email, role, REFRESH_SECRET, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
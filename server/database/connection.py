import os
from pathlib import Path
from collections.abc import Generator
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} 환경변수가 설정되지 않았습니다.")
    return value


DB_USER = _required_env("DB_USER")
DB_PASSWORD = _required_env("DB_PASSWORD")
DB_HOST = _required_env("DB_HOST")
DB_NAME = _required_env("DB_NAME")

try:
    DB_PORT = int(_required_env("DB_PORT"))
except ValueError as error:
    raise RuntimeError("DB_PORT는 정수여야 합니다.") from error
if not 1 <= DB_PORT <= 65535:
    raise RuntimeError("DB_PORT는 1부터 65535 사이여야 합니다.")

DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    query={"charset": "utf8mb4"},
)

engine = create_engine(
    DATABASE_URL,
    echo=True,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

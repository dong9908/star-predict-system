import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.connection import engine, Base
from routes.member import member_router
from routes.constellation import constellation_router
from fortune.router import fortune_router
from payment.router import payment_router

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# DB 테이블 자동 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ASTRA Backend Server")

# CORS 미들웨어 설정
raw_origins = os.getenv("FRONT_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 회원 라우터 등록
app.include_router(member_router, prefix="/api/member", tags=["Auth & Member"])

# 운세 라우터 등록
app.include_router(fortune_router, prefix="/api/fortune", tags=["Fortune"])

# 결제 라우터 등록
app.include_router(payment_router, prefix="/api/payment", tags=["Payment"])

# 별자리 위치 조회 라우터 등록
app.include_router(constellation_router, prefix="/api/constellation", tags=["Constellation"])

@app.get("/")
def root():
    return {"message": "ASTRA Server is Running"}

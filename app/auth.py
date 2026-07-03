"""인증 모듈 - JWT 기반"""
import os
import hashlib
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from app.models import Counselor

SECRET_KEY = "healthcare-counseling-ai-jwt-secret-key-2026-very-secure-and-long-enough-for-hs256"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 72


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


def create_token(counselor_id: int, email: str, name: str) -> str:
    payload = {
        "sub": str(counselor_id),
        "email": email,
        "name": name,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


def get_current_counselor_id(request: Request) -> int:
    """헤더에서 토큰 추출 → counselor_id 반환"""
    auth = request.headers.get("authorization")
    if not auth:
        raise HTTPException(status_code=401, detail="No authorization header")
    token = auth.replace("Bearer ", "")
    payload = decode_token(token)
    return int(payload["sub"])

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import Counselor
from app.auth import hash_password, verify_password, create_token, get_current_counselor_id

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    license_type: str = ""
    organization: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register")
def register(data: RegisterRequest, db: DBSession = Depends(get_db)):
    """상담사 회원가입"""
    existing = db.query(Counselor).filter(Counselor.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다")

    counselor = Counselor(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        license_type=data.license_type,
        organization=data.organization,
    )
    db.add(counselor)
    db.commit()
    db.refresh(counselor)

    token = create_token(counselor.id, counselor.email, counselor.name)
    return {
        "token": token,
        "counselor": {
            "id": counselor.id,
            "email": counselor.email,
            "name": counselor.name,
            "organization": counselor.organization,
        }
    }


@router.post("/login")
def login(data: LoginRequest, db: DBSession = Depends(get_db)):
    """상담사 로그인"""
    counselor = db.query(Counselor).filter(Counselor.email == data.email).first()
    if not counselor or not verify_password(data.password, counselor.password_hash):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다")

    token = create_token(counselor.id, counselor.email, counselor.name)
    return {
        "token": token,
        "counselor": {
            "id": counselor.id,
            "email": counselor.email,
            "name": counselor.name,
            "organization": counselor.organization,
        }
    }


@router.get("/me")
def get_me(counselor_id: int = Depends(get_current_counselor_id), db: DBSession = Depends(get_db)):
    """현재 로그인한 상담사 정보"""
    counselor = db.query(Counselor).filter(Counselor.id == counselor_id).first()
    if not counselor:
        raise HTTPException(status_code=404, detail="Counselor not found")
    return {
        "id": counselor.id,
        "email": counselor.email,
        "name": counselor.name,
        "license_type": counselor.license_type,
        "organization": counselor.organization,
    }

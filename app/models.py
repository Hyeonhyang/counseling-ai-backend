from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from app.database import Base


class Counselor(Base):
    """상담사"""
    __tablename__ = "counselors"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    license_type = Column(String, default="")  # 자격증 종류
    organization = Column(String, default="")  # 소속 기관
    created_at = Column(DateTime, default=datetime.utcnow)


class Client(Base):
    """내담자"""
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    counselor_id = Column(Integer, nullable=False, index=True)  # 담당 상담사
    name = Column(String, nullable=False)
    age = Column(Integer)
    gender = Column(String)
    presenting_issue = Column(Text, default="")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class Session(Base):
    """상담 세션 (회차별 기록)"""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, nullable=False, index=True)
    session_number = Column(Integer, nullable=False)
    raw_text = Column(Text, nullable=False)
    # AI 추출 점수
    depression_score = Column(Float, default=0)
    anxiety_score = Column(Float, default=0)
    anger_score = Column(Float, default=0)
    self_esteem_score = Column(Float, default=0)
    # AI 추출 메타
    key_persons = Column(Text, default="[]")  # JSON array
    defense_mechanisms = Column(Text, default="[]")  # JSON array
    ai_summary = Column(Text, default="")
    # 상담 기법
    technique_used = Column(String, default="")
    # 타임스탬프
    session_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

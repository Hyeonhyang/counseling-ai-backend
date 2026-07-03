import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Session as SessionModel
from app.schemas import CompareRequest, ParseRequest, RAGRequest
from app.ai_parser import parse_counseling_text, generate_insight, generate_rag_recommendation

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("/parse")
async def parse_text(data: ParseRequest):
    """텍스트를 AI로 분석 (저장 없이 미리보기)"""
    result = await parse_counseling_text(data.text)
    return result


@router.post("/compare")
async def compare_sessions(data: CompareRequest, db: Session = Depends(get_db)):
    """선택된 회차들 비교 + AI 인사이트"""
    sessions = db.query(SessionModel).filter(
        SessionModel.client_id == data.client_id,
        SessionModel.session_number.in_(data.session_numbers)
    ).order_by(SessionModel.session_number).all()

    if len(sessions) < 2:
        raise HTTPException(status_code=400, detail="비교하려면 2개 이상의 세션이 필요합니다")

    sessions_data = []
    for s in sessions:
        sessions_data.append({
            "session_number": s.session_number,
            "session_date": s.session_date,
            "depression_score": s.depression_score,
            "anxiety_score": s.anxiety_score,
            "anger_score": s.anger_score,
            "self_esteem_score": s.self_esteem_score,
            "key_persons": json.loads(s.key_persons) if s.key_persons else [],
            "defense_mechanisms": json.loads(s.defense_mechanisms) if s.defense_mechanisms else [],
            "counseling_technique": s.counseling_technique,
        })

    insight = await generate_insight(sessions_data)

    return {
        "sessions": sessions_data,
        "insight": insight,
    }


@router.post("/recommend")
async def get_recommendation(data: RAGRequest, db: Session = Depends(get_db)):
    """유사 케이스 기반 추천 (RAG)"""
    session = db.query(SessionModel).filter(SessionModel.id == data.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    current_state = {
        "depression_score": session.depression_score,
        "anxiety_score": session.anxiety_score,
        "anger_score": session.anger_score,
        "self_esteem_score": session.self_esteem_score,
        "key_persons": json.loads(session.key_persons) if session.key_persons else [],
        "counseling_technique": session.counseling_technique,
    }

    # TODO: 실제 ChromaDB 검색으로 교체
    # 지금은 Mock 유사 케이스
    similar_cases = [
        {
            "case_id": "CASE-2024-0042",
            "similarity": 87,
            "initial_depression": 75,
            "final_depression": 35,
            "technique": "수용전념치료(ACT)",
            "sessions_to_improvement": 6,
        },
        {
            "case_id": "CASE-2024-0118",
            "similarity": 72,
            "initial_depression": 80,
            "final_depression": 45,
            "technique": "인지행동치료(CBT) + 마음챙김",
            "sessions_to_improvement": 8,
        },
    ]

    recommendation = await generate_rag_recommendation(current_state, similar_cases)

    return {
        "current_state": current_state,
        "similar_cases": similar_cases,
        "recommendation": recommendation,
    }

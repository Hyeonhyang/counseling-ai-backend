"""RAG Engine - 유사 케이스 추천"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import Session, Client
from app.ai_parser import generate_rag_suggestion

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.get("/recommend/{client_id}")
def get_recommendation(client_id: int, db: DBSession = Depends(get_db)):
    """현재 내담자와 유사한 과거 성공 케이스 추천"""
    # 현재 내담자의 최근 세션 가져오기
    latest_session = db.query(Session).filter(
        Session.client_id == client_id
    ).order_by(Session.session_number.desc()).first()

    if not latest_session:
        raise HTTPException(status_code=404, detail="No sessions found for this client")

    current_state = {
        "depression": latest_session.depression_score,
        "anxiety": latest_session.anxiety_score,
        "anger": latest_session.anger_score,
        "self_esteem": latest_session.self_esteem_score,
        "technique": latest_session.technique_used,
        "key_persons": json.loads(latest_session.key_persons) if latest_session.key_persons else [],
    }

    # 다른 내담자들의 세션에서 유사한 패턴 찾기
    all_sessions = db.query(Session).filter(
        Session.client_id != client_id,
        Session.depression_score > 0  # 분석 완료된 세션만
    ).all()

    if not all_sessions:
        return {
            "current_state": current_state,
            "recommendations": [],
            "suggestion": "아직 비교할 수 있는 다른 케이스가 없습니다. 더 많은 데이터가 쌓이면 추천이 가능합니다.",
        }

    # 간단한 유사도 계산 (유클리드 거리 기반)
    scored_sessions = []
    for s in all_sessions:
        distance = (
            (s.depression_score - current_state["depression"]) ** 2 +
            (s.anxiety_score - current_state["anxiety"]) ** 2 +
            (s.anger_score - current_state["anger"]) ** 2 +
            (s.self_esteem_score - current_state["self_esteem"]) ** 2
        ) ** 0.5

        similarity = max(0, 100 - distance)  # 거리가 가까울수록 유사도 높음
        scored_sessions.append({
            "session": s,
            "similarity": round(similarity, 1),
        })

    # 상위 3개 유사 케이스
    scored_sessions.sort(key=lambda x: x["similarity"], reverse=True)
    top_cases = scored_sessions[:3]

    similar_cases = []
    for case in top_cases:
        s = case["session"]
        client = db.query(Client).filter(Client.id == s.client_id).first()
        similar_cases.append({
            "case_id": f"내담자 #{s.client_id}",
            "similarity": case["similarity"],
            "technique_used": s.technique_used or "미기록",
            "depression": s.depression_score,
            "anxiety": s.anxiety_score,
            "session_number": s.session_number,
        })

    # AI에게 추천 요청
    suggestion = generate_rag_suggestion(current_state, similar_cases)

    return {
        "current_state": current_state,
        "recommendations": similar_cases,
        "suggestion": suggestion,
    }

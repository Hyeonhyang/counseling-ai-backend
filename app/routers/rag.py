"""RAG Engine - ChromaDB 벡터 검색 기반 유사 케이스 추천"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import Session, Client
from app.ai_parser import generate_rag_suggestion
from app.vector_store import search_similar_sessions, get_collection_count

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.get("/recommend/{client_id}")
def get_recommendation(client_id: int, db: DBSession = Depends(get_db)):
    """현재 내담자와 유사한 과거 성공 케이스 추천 (ChromaDB 벡터 검색)"""
    # 현재 내담자의 최근 세션 가져오기
    latest_session = db.query(Session).filter(
        Session.client_id == client_id
    ).order_by(Session.session_number.desc()).first()

    if not latest_session:
        raise HTTPException(status_code=404, detail="No sessions found for this client")

    current_state = {
        "depression_score": latest_session.depression_score,
        "anxiety_score": latest_session.anxiety_score,
        "anger_score": latest_session.anger_score,
        "self_esteem_score": latest_session.self_esteem_score,
        "technique_used": latest_session.technique_used,
        "key_persons": latest_session.key_persons or "[]",
        "defense_mechanisms": latest_session.defense_mechanisms or "[]",
        "ai_summary": latest_session.ai_summary or "",
        "raw_text": latest_session.raw_text[:500] if latest_session.raw_text else "",
        "session_number": latest_session.session_number,
    }

    # ChromaDB 벡터 검색
    vector_count = get_collection_count()
    similar_cases = []

    if vector_count > 0:
        similar_cases = search_similar_sessions(current_state, client_id, top_k=3)

    # 벡터 DB에 데이터가 없으면 기존 SQL 기반 fallback
    if not similar_cases:
        all_sessions = db.query(Session).filter(
            Session.client_id != client_id,
            Session.depression_score > 0
        ).all()

        for s in all_sessions[:20]:
            distance = (
                (s.depression_score - current_state["depression_score"]) ** 2 +
                (s.anxiety_score - current_state["anxiety_score"]) ** 2 +
                (s.anger_score - current_state["anger_score"]) ** 2 +
                (s.self_esteem_score - current_state["self_esteem_score"]) ** 2
            ) ** 0.5
            similarity = max(0, round(100 - distance, 1))
            similar_cases.append({
                "case_id": f"내담자 #{s.client_id}",
                "similarity": similarity,
                "technique_used": s.technique_used or "미기록",
                "depression": s.depression_score,
                "anxiety": s.anxiety_score,
                "session_number": s.session_number,
            })

        similar_cases.sort(key=lambda x: x["similarity"], reverse=True)
        similar_cases = similar_cases[:3]

    # AI에게 추천 요청
    suggestion = generate_rag_suggestion(
        {"depression": current_state["depression_score"],
         "anxiety": current_state["anxiety_score"],
         "anger": current_state["anger_score"],
         "self_esteem": current_state["self_esteem_score"],
         "technique": current_state["technique_used"]},
        similar_cases
    )

    return {
        "current_state": {
            "depression": current_state["depression_score"],
            "anxiety": current_state["anxiety_score"],
            "anger": current_state["anger_score"],
            "self_esteem": current_state["self_esteem_score"],
            "technique": current_state["technique_used"],
        },
        "recommendations": similar_cases,
        "suggestion": suggestion,
        "vector_db_count": vector_count,
        "search_method": "vector" if vector_count > 0 and similar_cases else "fallback",
    }


@router.post("/index-all")
def index_all_sessions(db: DBSession = Depends(get_db)):
    """기존 모든 세션을 ChromaDB에 인덱싱 (1회 실행)"""
    from app.vector_store import upsert_session

    sessions = db.query(Session).filter(Session.depression_score > 0).all()
    count = 0
    for s in sessions:
        upsert_session(s.id, s.client_id, {
            "session_number": s.session_number,
            "depression_score": s.depression_score,
            "anxiety_score": s.anxiety_score,
            "anger_score": s.anger_score,
            "self_esteem_score": s.self_esteem_score,
            "technique_used": s.technique_used or "",
            "key_persons": s.key_persons or "[]",
            "defense_mechanisms": s.defense_mechanisms or "[]",
            "ai_summary": s.ai_summary or "",
            "raw_text": s.raw_text[:500] if s.raw_text else "",
        })
        count += 1

    return {"indexed": count, "total_in_vector_db": get_collection_count()}

"""벡터 검색 - PostgreSQL 기반 (배포 환경 호환)
ChromaDB 대신 PostgreSQL의 trigram 유사도 + 점수 가중치 기반 검색 사용.
Supabase에서도 안정적으로 동작.
"""
import json
from sqlalchemy import text
from app.database import SessionLocal


def build_search_profile(session_data: dict) -> str:
    """세션 데이터를 검색용 프로파일 텍스트로 변환"""
    parts = []
    technique = session_data.get("technique_used", "")
    if technique:
        parts.append(f"기법:{technique}")

    persons = session_data.get("key_persons", "[]")
    if persons and persons != "[]":
        try:
            p_list = json.loads(persons) if isinstance(persons, str) else persons
            parts.append(f"인물:{','.join(p_list)}")
        except:
            pass

    defenses = session_data.get("defense_mechanisms", "[]")
    if defenses and defenses != "[]":
        try:
            d_list = json.loads(defenses) if isinstance(defenses, str) else defenses
            parts.append(f"방어기제:{','.join(d_list)}")
        except:
            pass

    summary = session_data.get("ai_summary", "")
    if summary:
        parts.append(summary)

    return " ".join(parts)


def search_similar_sessions(current_session: dict, current_client_id: int, top_k: int = 3) -> list:
    """
    복합 유사도 검색:
    1. 점수 유사도 (유클리드 거리)
    2. 기법 매칭 보너스
    3. 핵심 인물 매칭 보너스
    """
    db = SessionLocal()
    try:
        from app.models import Session, Client

        # 현재 상태
        dep = current_session.get("depression_score", 0)
        anx = current_session.get("anxiety_score", 0)
        ang = current_session.get("anger_score", 0)
        est = current_session.get("self_esteem_score", 0)
        technique = current_session.get("technique_used", "")
        persons = current_session.get("key_persons", "[]")

        # 다른 내담자의 분석 완료된 세션만 조회
        all_sessions = db.query(Session).filter(
            Session.client_id != current_client_id,
            Session.depression_score > 0
        ).all()

        scored = []
        for s in all_sessions:
            # 1. 점수 유사도 (역 유클리드 거리, 0~100)
            distance = (
                (s.depression_score - dep) ** 2 +
                (s.anxiety_score - anx) ** 2 +
                (s.anger_score - ang) ** 2 +
                (s.self_esteem_score - est) ** 2
            ) ** 0.5
            score_similarity = max(0, 100 - distance * 0.5)

            # 2. 기법 매칭 보너스 (+15)
            technique_bonus = 15 if (technique and s.technique_used and
                                     technique.lower() == s.technique_used.lower()) else 0

            # 3. 핵심 인물 매칭 보너스 (겹치는 인물당 +5, 최대 +15)
            person_bonus = 0
            try:
                current_persons = json.loads(persons) if isinstance(persons, str) else persons
                session_persons = json.loads(s.key_persons) if s.key_persons else []
                overlap = set(current_persons) & set(session_persons)
                person_bonus = min(15, len(overlap) * 5)
            except:
                pass

            # 4. 방어기제 매칭 보너스 (겹치면 +10)
            defense_bonus = 0
            try:
                current_def = json.loads(current_session.get("defense_mechanisms", "[]"))
                session_def = json.loads(s.defense_mechanisms) if s.defense_mechanisms else []
                if set(current_def) & set(session_def):
                    defense_bonus = 10
            except:
                pass

            total_similarity = min(100, score_similarity + technique_bonus + person_bonus + defense_bonus)

            scored.append({
                "session": s,
                "similarity": round(total_similarity, 1),
                "factors": {
                    "score_match": round(score_similarity, 1),
                    "technique_match": technique_bonus > 0,
                    "person_overlap": person_bonus > 0,
                    "defense_overlap": defense_bonus > 0,
                }
            })

        # 유사도 높은 순 정렬
        scored.sort(key=lambda x: x["similarity"], reverse=True)

        results = []
        for item in scored[:top_k]:
            s = item["session"]
            results.append({
                "case_id": f"내담자 #{s.client_id}",
                "session_number": s.session_number,
                "similarity": item["similarity"],
                "technique_used": s.technique_used or "미기록",
                "depression": s.depression_score,
                "anxiety": s.anxiety_score,
                "anger": s.anger_score,
                "self_esteem": s.self_esteem_score,
                "match_factors": item["factors"],
            })

        return results

    finally:
        db.close()


def get_collection_count() -> int:
    """검색 가능한 세션 수"""
    db = SessionLocal()
    try:
        from app.models import Session
        return db.query(Session).filter(Session.depression_score > 0).count()
    finally:
        db.close()

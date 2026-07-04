"""ChromaDB Vector Store - 유사 케이스 검색용"""
import os
import chromadb
from chromadb.config import Settings

# ChromaDB 클라이언트 (로컬 영구 저장)
CHROMA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_data")
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

# 컬렉션: 세션별 임베딩
collection = chroma_client.get_or_create_collection(
    name="counseling_sessions",
    metadata={"hnsw:space": "cosine"}  # 코사인 유사도 사용
)


def build_session_document(session_data: dict) -> str:
    """세션 데이터를 검색용 문서 텍스트로 변환"""
    parts = []

    # 점수 정보
    parts.append(f"우울:{session_data.get('depression_score', 0)} 불안:{session_data.get('anxiety_score', 0)} 분노:{session_data.get('anger_score', 0)} 자존감:{session_data.get('self_esteem_score', 0)}")

    # 기법
    technique = session_data.get("technique_used", "")
    if technique:
        parts.append(f"사용기법:{technique}")

    # 핵심 인물
    persons = session_data.get("key_persons", "")
    if persons and persons != "[]":
        parts.append(f"핵심인물:{persons}")

    # 방어기제
    defenses = session_data.get("defense_mechanisms", "")
    if defenses and defenses != "[]":
        parts.append(f"방어기제:{defenses}")

    # 요약
    summary = session_data.get("ai_summary", "")
    if summary:
        parts.append(summary)

    # 원문 일부 (처음 500자)
    raw = session_data.get("raw_text", "")
    if raw:
        parts.append(raw[:500])

    return " ".join(parts)


def upsert_session(session_id: int, client_id: int, session_data: dict):
    """세션을 벡터 DB에 추가/업데이트"""
    doc_text = build_session_document(session_data)
    doc_id = f"session_{session_id}"

    metadata = {
        "session_id": session_id,
        "client_id": client_id,
        "session_number": session_data.get("session_number", 0),
        "depression_score": float(session_data.get("depression_score", 0)),
        "anxiety_score": float(session_data.get("anxiety_score", 0)),
        "anger_score": float(session_data.get("anger_score", 0)),
        "self_esteem_score": float(session_data.get("self_esteem_score", 0)),
        "technique_used": session_data.get("technique_used", ""),
    }

    collection.upsert(
        ids=[doc_id],
        documents=[doc_text],
        metadatas=[metadata],
    )


def search_similar_sessions(query_session_data: dict, current_client_id: int, top_k: int = 5) -> list:
    """현재 세션과 유사한 다른 내담자의 세션 검색"""
    query_text = build_session_document(query_session_data)

    # 검색 (현재 내담자 제외를 위해 더 많이 가져옴)
    results = collection.query(
        query_texts=[query_text],
        n_results=top_k + 10,  # 필터링 후 top_k 남기기 위해 여유분
    )

    if not results or not results["ids"] or not results["ids"][0]:
        return []

    similar = []
    for i, doc_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i] if results["metadatas"] else {}
        distance = results["distances"][0][i] if results["distances"] else 1.0

        # 현재 내담자 자신의 세션은 제외
        if meta.get("client_id") == current_client_id:
            continue

        similarity = round((1 - distance) * 100, 1)  # 코사인 거리 → 유사도 %

        similar.append({
            "session_id": meta.get("session_id"),
            "client_id": meta.get("client_id"),
            "case_id": f"내담자 #{meta.get('client_id', '?')}",
            "session_number": meta.get("session_number", 0),
            "similarity": similarity,
            "technique_used": meta.get("technique_used", "미기록"),
            "depression": meta.get("depression_score", 0),
            "anxiety": meta.get("anxiety_score", 0),
            "anger": meta.get("anger_score", 0),
            "self_esteem": meta.get("self_esteem_score", 0),
        })

        if len(similar) >= top_k:
            break

    return similar


def get_collection_count() -> int:
    """벡터 DB에 저장된 세션 수"""
    return collection.count()

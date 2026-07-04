import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import Session
from app.schemas import SessionCreate, SessionResponse, SessionUpdateScores, AIParseResult
from app.ai_parser import parse_counseling_text, generate_comparison_insight, detect_risk_level
from groq import Groq
import os
import tempfile

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("/client/{client_id}", response_model=list[SessionResponse])
def get_sessions_by_client(client_id: int, db: DBSession = Depends(get_db)):
    return db.query(Session).filter(
        Session.client_id == client_id
    ).order_by(Session.session_number).all()


@router.post("", response_model=SessionResponse)
def create_session(data: SessionCreate, db: DBSession = Depends(get_db)):
    session = Session(
        client_id=data.client_id,
        session_number=data.session_number,
        raw_text=data.raw_text,
        technique_used=data.technique_used,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/upload")
async def upload_session_file(
    client_id: int = Form(...),
    session_number: int = Form(...),
    technique_used: str = Form(""),
    file: UploadFile = File(...)
):
    """텍스트 파일 업로드로 세션 생성"""
    content = await file.read()
    text = content.decode("utf-8")
    return {"raw_text": text, "client_id": client_id, "session_number": session_number}


@router.post("/parse-text")
def parse_text_only(data: dict):
    """텍스트만 AI 분석 (DB 저장 없이) + 위기 감지"""
    text = data.get("text", "")
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text is empty")

    result = parse_counseling_text(text)
    risk = detect_risk_level(text)

    return {
        "depression_score": result["depression_score"],
        "anxiety_score": result["anxiety_score"],
        "anger_score": result["anger_score"],
        "self_esteem_score": result["self_esteem_score"],
        "key_persons": result.get("key_persons", []),
        "defense_mechanisms": result.get("defense_mechanisms", []),
        "summary": result.get("summary", ""),
        "risk_level": risk["level"],
        "risk_keywords": risk["keywords"],
    }


@router.post("/soap")
def generate_soap(data: dict):
    """상담 내용을 SOAP 형식으로 변환"""
    from app.ai_parser import generate_soap_note
    text = data.get("text", "")
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text is empty")
    return generate_soap_note(text)


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """음성 파일을 텍스트로 변환 (Groq Whisper)"""
    try:
        # 임시 파일로 저장
        suffix = ".webm" if "webm" in (file.content_type or "") else ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Groq Whisper 호출
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        with open(tmp_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio_file,
                language="ko",
            )

        # 임시 파일 삭제
        os.unlink(tmp_path)

        return {"text": transcription.text}
    except Exception as e:
        return {"text": "", "error": str(e)}


@router.post("/{session_id}/parse", response_model=AIParseResult)
def parse_session(session_id: int, db: DBSession = Depends(get_db)):
    """AI로 세션 텍스트 분석"""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    result = parse_counseling_text(session.raw_text)

    return AIParseResult(
        depression_score=result["depression_score"],
        anxiety_score=result["anxiety_score"],
        anger_score=result["anger_score"],
        self_esteem_score=result["self_esteem_score"],
        key_persons=result.get("key_persons", []),
        defense_mechanisms=result.get("defense_mechanisms", []),
        summary=result.get("summary", ""),
    )


@router.patch("/{session_id}/scores", response_model=SessionResponse)
def update_scores(session_id: int, data: SessionUpdateScores, db: DBSession = Depends(get_db)):
    """AI 분석 결과 확정 (수동 보정 후 저장)"""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.depression_score = data.depression_score
    session.anxiety_score = data.anxiety_score
    session.anger_score = data.anger_score
    session.self_esteem_score = data.self_esteem_score
    session.key_persons = data.key_persons
    session.defense_mechanisms = data.defense_mechanisms
    if data.ai_summary:
        session.ai_summary = data.ai_summary
    if data.soap_subjective:
        session.soap_subjective = data.soap_subjective
    if data.soap_objective:
        session.soap_objective = data.soap_objective
    if data.soap_assessment:
        session.soap_assessment = data.soap_assessment
    if data.soap_plan:
        session.soap_plan = data.soap_plan
    if data.risk_level:
        session.risk_level = data.risk_level
    if data.risk_keywords:
        session.risk_keywords = data.risk_keywords
    db.commit()
    db.refresh(session)

    # 벡터 DB에도 업데이트
    try:
        from app.vector_store import upsert_session
        upsert_session(session.id, session.client_id, {
            "session_number": session.session_number,
            "depression_score": session.depression_score,
            "anxiety_score": session.anxiety_score,
            "anger_score": session.anger_score,
            "self_esteem_score": session.self_esteem_score,
            "technique_used": session.technique_used or "",
            "key_persons": session.key_persons or "[]",
            "defense_mechanisms": session.defense_mechanisms or "[]",
            "ai_summary": session.ai_summary or "",
            "raw_text": session.raw_text[:500] if session.raw_text else "",
        })
    except Exception as e:
        print(f"Vector DB upsert error: {e}")

    return session


@router.delete("/{session_id}")
def delete_session(session_id: int, db: DBSession = Depends(get_db)):
    """세션 삭제"""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"success": True}


@router.put("/{session_id}", response_model=SessionResponse)
def update_session(session_id: int, data: SessionCreate, db: DBSession = Depends(get_db)):
    """세션 내용 수정 (텍스트, 회차, 기법 등)"""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.raw_text = data.raw_text
    session.session_number = data.session_number
    session.technique_used = data.technique_used
    db.commit()
    db.refresh(session)
    return session


@router.get("/compare")
def compare_sessions(client_id: int, session_numbers: str, db: DBSession = Depends(get_db)):
    """다중 세션 비교 + AI 인사이트"""
    nums = [int(n.strip()) for n in session_numbers.split(",")]

    sessions = db.query(Session).filter(
        Session.client_id == client_id,
        Session.session_number.in_(nums)
    ).order_by(Session.session_number).all()

    if not sessions:
        raise HTTPException(status_code=404, detail="No sessions found")

    sessions_data = [
        {
            "session_number": s.session_number,
            "depression": s.depression_score,
            "anxiety": s.anxiety_score,
            "anger": s.anger_score,
            "self_esteem": s.self_esteem_score,
            "key_persons": json.loads(s.key_persons) if s.key_persons else [],
            "technique": s.technique_used,
            "summary": s.ai_summary,
        }
        for s in sessions
    ]

    insight = generate_comparison_insight(sessions_data)

    return {
        "sessions": sessions_data,
        "insight": insight,
    }

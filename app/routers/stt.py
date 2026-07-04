"""Speech-to-Text (음성 → 텍스트 변환) - Groq Whisper"""
import os
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException
from groq import Groq

router = APIRouter(prefix="/api/stt", tags=["stt"])

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """음성 파일을 텍스트로 변환 (Groq Whisper)"""
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")

    # 지원 포맷 확인
    allowed_types = ["audio/webm", "audio/wav", "audio/mp3", "audio/mpeg",
                     "audio/mp4", "audio/m4a", "audio/ogg", "audio/flac",
                     "video/webm", "audio/x-m4a"]
    # content_type 체크 (느슨하게)
    if file.content_type and not any(t in file.content_type for t in ["audio", "video/webm"]):
        raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식입니다: {file.content_type}")

    try:
        # 임시 파일로 저장 (Groq SDK가 파일 경로를 요구)
        content = await file.read()
        suffix = ".webm"
        if file.filename:
            if file.filename.endswith(".wav"):
                suffix = ".wav"
            elif file.filename.endswith(".mp3"):
                suffix = ".mp3"
            elif file.filename.endswith(".m4a"):
                suffix = ".m4a"
            elif file.filename.endswith(".flac"):
                suffix = ".flac"
            elif file.filename.endswith(".ogg"):
                suffix = ".ogg"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # Groq Whisper로 변환
        client = Groq(api_key=GROQ_API_KEY)
        with open(tmp_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio_file,
                language="ko",
                response_format="text",
            )

        # 임시 파일 삭제
        os.unlink(tmp_path)

        text = transcription if isinstance(transcription, str) else transcription.text

        return {"text": text.strip(), "status": "success"}

    except Exception as e:
        # 임시 파일 정리
        try:
            os.unlink(tmp_path)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"음성 변환 실패: {str(e)}")

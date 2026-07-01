"""Voice endpoints: transcribe + extract structured invoice."""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from core.auth import get_current_user
from core.config import UPLOAD_DIR
from core.llm import VOICE_EXTRACT_PROMPT, llm_extract, whisper_transcribe

router = APIRouter(prefix="/voice", tags=["voice"])


def _save(file: UploadFile) -> tuple[str, str]:
    ext = Path(file.filename or "").suffix or ".webm"
    fname = f"voice-{uuid.uuid4().hex}{ext}"
    fpath = UPLOAD_DIR / fname
    return fname, str(fpath)


@router.post("/transcribe")
async def voice_transcribe(file: UploadFile = File(...), language: str = Form("hi"),
                            current=Depends(get_current_user)):
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Audio too large (max 25MB)")
    fname, fpath = _save(file)
    with open(fpath, "wb") as f:
        f.write(data)
    try:
        text = await whisper_transcribe(fpath, language=language or "hi")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
    return {"text": text, "audio_url": f"/api/uploads/{fname}"}


@router.post("/extract")
async def voice_extract(file: UploadFile = File(...), language: str = Form("hi"),
                         current=Depends(get_current_user)):
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Audio too large (max 25MB)")
    fname, fpath = _save(file)
    with open(fpath, "wb") as f:
        f.write(data)
    try:
        text = await whisper_transcribe(fpath, language=language or "hi")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
    parsed = await llm_extract(VOICE_EXTRACT_PROMPT, f"Transcript: {text}\n\nExtract JSON.")
    parsed["transcript"] = text
    parsed["audio_url"] = f"/api/uploads/{fname}"
    return parsed


@router.post("/extract-text")
async def voice_extract_text(payload: dict, current=Depends(get_current_user)):
    text = (payload or {}).get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    parsed = await llm_extract(VOICE_EXTRACT_PROMPT, f"Transcript: {text}\n\nExtract JSON.")
    parsed["transcript"] = text
    return parsed

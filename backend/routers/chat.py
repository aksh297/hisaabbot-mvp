"""Chat playground router."""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends

from core.auth import get_current_user
from core.db import db
from core.llm import CHAT_SYSTEM_PROMPT, OCR_SYSTEM_PROMPT, llm_chat, llm_extract
from core.models import ChatMessageReq

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message")
async def chat_message(req: ChatMessageReq, current=Depends(get_current_user)):
    session_id = req.session_id or f"chat-{current['_id']}"
    from datetime import timezone as _tz
    await db.chat_messages.insert_one({
        "user_id": str(current["_id"]),
        "session_id": session_id,
        "role": "user",
        "text": req.message,
        "has_image": bool(req.image_base64),
        "created_at": datetime.now(_tz.utc),
    })

    system_prompt = CHAT_SYSTEM_PROMPT
    if current.get("business_name"):
        system_prompt += (f"\n\nUser's business: {current['business_name']}. "
                           f"GSTIN: {current.get('gstin') or 'not set'}. "
                           f"Language pref: {current.get('language','hi')}.")

    if req.image_base64:
        ocr = await llm_extract(OCR_SYSTEM_PROMPT, "Extract invoice fields from this image.", image_b64=req.image_base64)
        preview = json.dumps({k: v for k, v in ocr.items() if k not in ("_raw", "_error", "line_items")}, ensure_ascii=False)
        user_text = f"{req.message}\n\n[System note: user uploaded an invoice. OCR extracted: {preview}. Ask user to confirm before saving.]"
        reply = await llm_chat(session_id, system_prompt, user_text, image_b64=req.image_base64)
    else:
        reply = await llm_chat(session_id, system_prompt, req.message)

    await db.chat_messages.insert_one({
        "user_id": str(current["_id"]),
        "session_id": session_id,
        "role": "assistant",
        "text": reply,
        "created_at": datetime.now(_tz.utc),
    })
    return {"session_id": session_id, "reply": reply}


@router.get("/history")
async def chat_history(session_id: Optional[str] = None, current=Depends(get_current_user)):
    q: dict = {"user_id": str(current["_id"])}
    if session_id:
        q["session_id"] = session_id
    cur = db.chat_messages.find(q).sort("created_at", 1)
    out = []
    async for d in cur:
        d["_id"] = str(d["_id"])
        d["created_at"] = d["created_at"].isoformat() if isinstance(d.get("created_at"), datetime) else d.get("created_at")
        out.append(d)
    return out

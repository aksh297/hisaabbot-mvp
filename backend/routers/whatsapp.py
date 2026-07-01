"""WhatsApp router — Gupshup webhook + test send + status."""
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Depends, HTTPException

from core.auth import get_current_user
from core.config import gupshup_enabled, GUPSHUP_APP_NAME, GUPSHUP_SOURCE
from core.db import db
from core.llm import CHAT_SYSTEM_PROMPT, llm_chat
from core.whatsapp_client import parse_inbound, wa_send_text, wa_send_template

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.get("/status")
async def wa_status():
    return {
        "enabled": gupshup_enabled(),
        "app_name": GUPSHUP_APP_NAME,
        "source": GUPSHUP_SOURCE if gupshup_enabled() else None,
        "mode": "live" if gupshup_enabled() else "simulated",
        "hint": ("Live Gupshup wired. Callback: /api/whatsapp/webhook"
                 if gupshup_enabled()
                 else "Set GUPSHUP_API_KEY + GUPSHUP_SOURCE (+ optional GUPSHUP_APP_NAME) in backend/.env to activate."),
    }


@router.post("/webhook")
async def webhook(request: Request):
    """Gupshup inbound webhook. Persists event, routes to chat pipeline for text messages,
    and echoes an intelligent reply back (session-window, free) when possible.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {"raw_body": (await request.body()).decode(errors="ignore")}

    await db.whatsapp_events.insert_one({
        "raw": payload,
        "received_at": datetime.now(timezone.utc),
    })

    parsed = parse_inbound(payload) if isinstance(payload, dict) else None
    if not parsed or not parsed.get("from"):
        return {"ok": True, "routed": False}

    sender = parsed["from"]

    # Ensure a shadow user exists for this phone (for chat history)
    user = await db.users.find_one({"phone": sender}) or await db.users.find_one({"wa_phone": sender})
    if not user:
        # create a lightweight shadow user
        from core.auth import hash_password
        import uuid as _u
        res = await db.users.insert_one({
            "email": f"wa-{_u.uuid4().hex[:8]}@hisaabbot.in",
            "password_hash": hash_password(_u.uuid4().hex),
            "name": f"WA {sender[-4:]}",
            "role": "vendor",
            "phone": sender,
            "wa_phone": sender,
            "language": "hi",
            "created_at": datetime.now(timezone.utc),
        })
        user = await db.users.find_one({"_id": res.inserted_id})

    session_id = f"wa-{sender}"
    if parsed["type"] == "text" and parsed.get("text"):
        # Log user message
        await db.chat_messages.insert_one({
            "user_id": str(user["_id"]), "session_id": session_id,
            "role": "user", "text": parsed["text"], "channel": "whatsapp",
            "created_at": datetime.now(timezone.utc),
        })
        reply = await llm_chat(session_id, CHAT_SYSTEM_PROMPT, parsed["text"])
        await db.chat_messages.insert_one({
            "user_id": str(user["_id"]), "session_id": session_id,
            "role": "assistant", "text": reply, "channel": "whatsapp",
            "created_at": datetime.now(timezone.utc),
        })
        # Send reply back
        send_res = await wa_send_text(to=sender, text=reply)
        return {"ok": True, "routed": True, "reply_preview": reply[:80], "send": send_res}

    # Media / other types — acknowledge for now
    ack = "Aapka message mila. HisaabBot dashboard pe details process ho rahe hain."
    await wa_send_text(to=sender, text=ack)
    return {"ok": True, "routed": True, "type": parsed["type"]}


@router.get("/webhook")
async def webhook_verify():
    """Verification GET for BSP setup."""
    return {"status": "verified"}


@router.post("/send-test")
async def send_test(payload: dict, current=Depends(get_current_user)):
    """Authenticated test-send endpoint. Body: {to: '+91...', text: 'hello'}.
    In simulated mode returns dry_run=true. In live mode sends via Gupshup.
    """
    to = (payload or {}).get("to")
    text = (payload or {}).get("text", "Namaste from HisaabBot!")
    if not to:
        raise HTTPException(status_code=400, detail="'to' phone required")
    return await wa_send_text(to=to, text=text)


@router.post("/send-template")
async def send_template(payload: dict, current=Depends(get_current_user)):
    """Send an approved template message.
    Body: {to: '+91...', template_id: 'hisaabbot_welcome', params: ['Ramesh']}.
    """
    to = (payload or {}).get("to")
    template_id = (payload or {}).get("template_id")
    params = (payload or {}).get("params") or []
    if not to or not template_id:
        raise HTTPException(status_code=400, detail="'to' and 'template_id' required")
    return await wa_send_template(to=to, template_id=template_id, params=params)

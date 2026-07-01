"""Gupshup WhatsApp Business API wire-ready client.
When credentials are absent, all send functions gracefully degrade to logging
into `wa_send_log` collection so the app remains fully functional.
"""
import json
import os
from datetime import datetime, timezone
from typing import List, Optional

import httpx

from .config import GUPSHUP_API_KEY, GUPSHUP_APP_NAME, GUPSHUP_SOURCE, gupshup_enabled
from .db import db


async def _log_send(action: str, to: str, body: dict, response: dict, dry_run: bool):
    await db.wa_send_log.insert_one({
        "action": action, "to": to, "body": body,
        "response": response, "dry_run": dry_run,
        "created_at": datetime.now(timezone.utc),
    })


async def wa_send_text(to: str, text: str) -> dict:
    """Session (free) text message within 24-hour window.
    Returns {ok, dry_run, response}.  In dry-run (no creds), returns simulated ack.
    """
    body = {"channel": "whatsapp", "to": to, "text": text}
    if not gupshup_enabled():
        resp = {"status": "simulated", "message_id": f"SIM-{datetime.now().timestamp()}"}
        await _log_send("send_text", to, body, resp, dry_run=True)
        return {"ok": True, "dry_run": True, "response": resp}
    url = "https://api.gupshup.io/wa/api/v1/msg"
    headers = {"apikey": GUPSHUP_API_KEY, "Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "channel": "whatsapp",
        "source": GUPSHUP_SOURCE,
        "destination": to,
        "message": json.dumps({"type": "text", "text": text}),
        "src.name": GUPSHUP_APP_NAME,
    }
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(url, headers=headers, data=data)
        try:
            resp = r.json()
        except Exception:
            resp = {"status_code": r.status_code, "text": r.text}
    await _log_send("send_text", to, body, resp, dry_run=False)
    return {"ok": r.status_code < 400, "dry_run": False, "response": resp}


async def wa_send_template(to: str, template_id: str, params: List[str]) -> dict:
    """Send an approved template message (utility/marketing)."""
    body = {"template_id": template_id, "to": to, "params": params}
    if not gupshup_enabled():
        resp = {"status": "simulated", "template": template_id, "params": params,
                "message_id": f"SIM-TPL-{datetime.now().timestamp()}"}
        await _log_send("send_template", to, body, resp, dry_run=True)
        return {"ok": True, "dry_run": True, "response": resp}
    url = "https://api.gupshup.io/wa/api/v1/template/msg"
    headers = {"apikey": GUPSHUP_API_KEY, "Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "source": GUPSHUP_SOURCE,
        "destination": to,
        "template": json.dumps({"id": template_id, "params": params}),
        "src.name": GUPSHUP_APP_NAME,
    }
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(url, headers=headers, data=data)
        try:
            resp = r.json()
        except Exception:
            resp = {"status_code": r.status_code, "text": r.text}
    await _log_send("send_template", to, body, resp, dry_run=False)
    return {"ok": r.status_code < 400, "dry_run": False, "response": resp}


def parse_inbound(payload: dict) -> Optional[dict]:
    """Best-effort parser for Gupshup inbound webhook payloads.
    Returns {from, type, text, media_url} or None if not a message event.
    """
    try:
        if payload.get("type") == "message":
            p = payload.get("payload", {})
            sender = (p.get("sender") or {}).get("phone") or p.get("source")
            ptype = p.get("type")
            text = None
            media_url = None
            if ptype == "text":
                text = p.get("payload", {}).get("text")
            elif ptype in ("image", "audio", "video", "document"):
                media_url = p.get("payload", {}).get("url")
                text = p.get("payload", {}).get("caption")
            return {"from": sender, "type": ptype, "text": text, "media_url": media_url}
    except Exception:
        return None
    return None

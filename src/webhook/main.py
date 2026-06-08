"""
HisaabBot — WhatsApp Webhook Handler
=====================================
Entry point for all inbound WhatsApp messages.

Supported message types:
  - text  : User typed a query in Hindi/English/Hinglish
  - image : User sent an invoice photo
  - audio : User sent a Hindi voice note

Router sends each message type to the correct processing module.
"""

import logging
import hmac
import hashlib
import os
from typing import Annotated, Optional

from fastapi import FastAPI, Request, HTTPException, Header, Query, status
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Logging setup — structured logs for every inbound message
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("hisaabbot.webhook")

# ---------------------------------------------------------------------------
# App init
# ---------------------------------------------------------------------------
app = FastAPI(
    title="HisaabBot Webhook",
    description="WhatsApp webhook handler for HisaabBot — Apna CA, WhatsApp pe 🇮🇳",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Environment config
# ---------------------------------------------------------------------------
# Verify token used during WhatsApp webhook registration (GET verification)
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "hisaabbot_verify_2026")

# Optional: HMAC secret for payload signature verification (recommended in prod)
WHATSAPP_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class WhatsAppMessage(BaseModel):
    """Normalised inbound message — provider-agnostic internal representation."""
    sender_phone: str = Field(..., description="Sender's phone number in E.164 format")
    message_type: str = Field(..., description="text | image | audio | video | document")
    text_body: Optional[str] = Field(None, description="Text content (if type=text)")
    media_url: Optional[str] = Field(None, description="Media URL (if type=image/audio/video)")
    media_mime: Optional[str] = Field(None, description="MIME type of the media, e.g. image/jpeg")
    message_id: Optional[str] = Field(None, description="Provider message ID for dedup")


# ---------------------------------------------------------------------------
# Placeholder processors — replace with real implementations in later sprints
# ---------------------------------------------------------------------------

async def process_invoice_photo(media_url: str, sender_phone: str) -> dict:
    """
    Sprint 2: OCR pipeline
    ----------------------
    Invoice photo URL bhejo → Google Vision OCR → structured invoice data
    (vendor name, GSTIN, amount, HSN code, tax)
    """
    logger.info("📸 Invoice photo received | sender=%s | url=%s", sender_phone, media_url)
    # TODO: Hand off to src/ocr/invoice_extractor.py
    return {
        "status": "queued",
        "message": "Invoice photo received. Processing kar rahe hain... 🔄",
        "media_url": media_url,
    }


async def process_voice_note(media_url: str, sender_phone: str) -> dict:
    """
    Sprint 2: Voice transcription pipeline
    ---------------------------------------
    Hindi voice note URL bhejo → OpenAI Whisper (Hindi) → text → NLP intent
    """
    logger.info("🎤 Voice note received | sender=%s | url=%s", sender_phone, media_url)
    # TODO: Hand off to src/nlp/voice_processor.py (Whisper + intent detection)
    return {
        "status": "queued",
        "message": "Voice note mila. Transcription ho raha hai... 🎧",
        "media_url": media_url,
    }


async def process_text_query(text: str, sender_phone: str) -> dict:
    """
    Sprint 1: Text NLP handler
    --------------------------
    Hindi/English/Hinglish text → intent detection → GST / bookkeeping / UPI router
    Example intents:
      - gst_status    : "Mera GST kab file karna hai?"
      - invoice_create: "₹25000 ka bill banao Raj Traders ko"
      - ifc_query     : "ITC kitna bacha hai?"
      - monthly_report: "Mahine ka hisaab bhejo"
    """
    logger.info("💬 Text query received | sender=%s | text='%s'", sender_phone, text[:120])
    # TODO: Hand off to src/nlp/intent_router.py
    return {
        "status": "processed",
        "message": f"Query mili: '{text}' — Intent detection ho raha hai... 🤖",
        "sender": sender_phone,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _verify_signature(raw_body: bytes, signature_header: Optional[str]) -> bool:
    """
    Verify HMAC-SHA256 signature from WhatsApp Cloud API.
    Skip verification if WHATSAPP_APP_SECRET is not configured (dev mode).
    """
    if not WHATSAPP_APP_SECRET:
        return True  # Dev mode — skip signature check

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(
        WHATSAPP_APP_SECRET.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)


def _parse_whatsapp_cloud_payload(payload: dict) -> Optional[WhatsAppMessage]:
    """
    Parse WhatsApp Cloud API (Meta) webhook payload format.
    Reference: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/payload-examples
    """
    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        if "messages" not in value:
            return None  # Delivery receipt or status update — ignore

        msg = value["messages"][0]
        sender_phone = msg["from"]
        message_id = msg["id"]
        msg_type = msg["type"]

        text_body = None
        media_url = None
        media_mime = None

        if msg_type == "text":
            text_body = msg["text"]["body"]

        elif msg_type == "image":
            media_url = msg["image"].get("id")  # Cloud API: use media ID, not direct URL
            media_mime = msg["image"].get("mime_type", "image/jpeg")

        elif msg_type == "audio":
            media_url = msg["audio"].get("id")
            media_mime = msg["audio"].get("mime_type", "audio/ogg")

        elif msg_type == "document":
            media_url = msg["document"].get("id")
            media_mime = msg["document"].get("mime_type", "application/pdf")

        return WhatsAppMessage(
            sender_phone=sender_phone,
            message_type=msg_type,
            text_body=text_body,
            media_url=media_url,
            media_mime=media_mime,
            message_id=message_id,
        )

    except (KeyError, IndexError) as exc:
        logger.warning("Payload parse error (Cloud API format): %s", exc)
        return None


def _parse_gupshup_payload(payload: dict) -> Optional[WhatsAppMessage]:
    """
    Parse Gupshup WhatsApp Business API webhook payload.
    Gupshup is the recommended Indian provider for HisaabBot.
    Reference: https://docs.gupshup.io/docs/receive-message-webhook
    """
    try:
        msg = payload.get("payload", {})
        sender_phone = payload.get("sender", {}).get("phone", "unknown")
        msg_type = msg.get("type", "text")

        text_body = None
        media_url = None
        media_mime = None

        if msg_type == "text":
            text_body = msg.get("payload", {}).get("text", "")

        elif msg_type == "image":
            inner = msg.get("payload", {})
            media_url = inner.get("url")
            media_mime = "image/jpeg"

        elif msg_type == "audio":
            inner = msg.get("payload", {})
            media_url = inner.get("url")
            media_mime = "audio/ogg"

        elif msg_type == "document":
            inner = msg.get("payload", {})
            media_url = inner.get("url")
            media_mime = inner.get("contentType", "application/pdf")

        return WhatsAppMessage(
            sender_phone=sender_phone,
            message_type=msg_type,
            text_body=text_body,
            media_url=media_url,
            media_mime=media_mime,
            message_id=payload.get("messageId"),
        )

    except (KeyError, TypeError) as exc:
        logger.warning("Payload parse error (Gupshup format): %s", exc)
        return None


def _detect_provider_and_parse(payload: dict) -> Optional[WhatsAppMessage]:
    """
    Auto-detect WhatsApp provider from payload shape and parse accordingly.
    Supports: Meta Cloud API | Gupshup
    """
    # Meta Cloud API has a nested 'entry' key
    if "entry" in payload:
        return _parse_whatsapp_cloud_payload(payload)

    # Gupshup uses 'sender' + 'payload' at root level
    if "sender" in payload and "payload" in payload:
        return _parse_gupshup_payload(payload)

    logger.warning("Unknown WhatsApp provider payload shape. Keys: %s", list(payload.keys()))
    return None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
async def root():
    """Health check — confirms the webhook server is live."""
    return {"status": "ok", "service": "HisaabBot Webhook", "message": "Jai Hind! 🇮🇳"}


@app.get("/webhook", tags=["WhatsApp Verification"], response_class=PlainTextResponse)
async def verify_webhook(
    hub_mode: Annotated[Optional[str], Query(alias="hub.mode")] = None,
    hub_verify_token: Annotated[Optional[str], Query(alias="hub.verify_token")] = None,
    hub_challenge: Annotated[Optional[str], Query(alias="hub.challenge")] = None,
):
    """
    WhatsApp webhook verification (GET).
    Meta/Cloud API sends a GET request with hub.challenge when you register the webhook.
    This endpoint echoes back the challenge if the verify token matches.
    """
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        logger.info("✅ Webhook verified successfully by WhatsApp.")
        return hub_challenge or ""

    logger.warning("❌ Webhook verification failed. Token mismatch or wrong mode.")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification failed")


@app.post("/webhook", tags=["WhatsApp Messages"])
async def receive_message(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(default=None),
):
    """
    Main inbound webhook endpoint (POST).

    All WhatsApp messages from users arrive here.
    Flow:
      1. Parse raw body + verify HMAC signature (prod)
      2. Auto-detect provider (Meta Cloud API or Gupshup)
      3. Normalise into WhatsAppMessage model
      4. Route to correct processor: image → OCR | audio → Whisper | text → NLP
      5. Return 200 OK immediately (WhatsApp requires fast ACK)

    HisaabBot ke saare messages yahan aate hain 📨
    """
    raw_body = await request.body()

    # --- Step 1: Signature verification ---
    if not _verify_signature(raw_body, x_hub_signature_256):
        logger.warning("⚠️  Invalid HMAC signature. Rejecting request.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    # --- Step 2: Parse JSON body ---
    try:
        payload = await request.json()
    except Exception:
        logger.error("❌ Could not parse request body as JSON.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        )

    logger.debug("Raw payload received: %s", payload)

    # --- Step 3: Detect provider and normalise message ---
    message = _detect_provider_and_parse(payload)

    if message is None:
        # Could be a WhatsApp status update (read receipt, delivered, etc.) — safe to ignore
        logger.info("ℹ️  Non-message payload received (status update or unknown). Skipping.")
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ignored"})

    logger.info(
        "📨 Message received | from=%s | type=%s | id=%s",
        message.sender_phone,
        message.message_type,
        message.message_id,
    )

    # --- Step 4: Route to correct processor ---
    result: dict = {}

    if message.message_type == "image":
        # Invoice ki photo aayi → OCR pipeline
        if not message.media_url:
            logger.warning("Image message has no media URL | sender=%s", message.sender_phone)
            result = {"status": "error", "message": "Media URL missing in image message"}
        else:
            result = await process_invoice_photo(message.media_url, message.sender_phone)

    elif message.message_type == "audio":
        # Hindi voice note aayi → Whisper transcription
        if not message.media_url:
            logger.warning("Audio message has no media URL | sender=%s", message.sender_phone)
            result = {"status": "error", "message": "Media URL missing in audio message"}
        else:
            result = await process_voice_note(message.media_url, message.sender_phone)

    elif message.message_type == "text":
        # Text query aayi → NLP intent router
        query = message.text_body or ""
        if not query.strip():
            logger.warning("Empty text message | sender=%s", message.sender_phone)
            result = {"status": "ignored", "message": "Empty message"}
        else:
            result = await process_text_query(query, message.sender_phone)

    elif message.message_type == "document":
        # PDF invoice → treat same as image for now (Sprint 2: dedicated PDF parser)
        result = await process_invoice_photo(message.media_url or "", message.sender_phone)

    else:
        # Unsupported types (video, sticker, location, contacts, etc.)
        logger.info(
            "⚠️  Unsupported message type '%s' | sender=%s",
            message.message_type,
            message.sender_phone,
        )
        result = {
            "status": "unsupported",
            "message": f"Message type '{message.message_type}' is not supported yet.",
        }

    # --- Step 5: Return 200 immediately (WhatsApp requires fast ACK < 20s) ---
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ok", "result": result})

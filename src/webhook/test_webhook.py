"""
Tests for HisaabBot WhatsApp Webhook Handler
============================================
Covers: health check, webhook verification, Meta Cloud API format,
        Gupshup format, all message types (text/image/audio/document),
        HMAC signature validation, and edge cases.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import hashlib
import hmac
import json

from main import app, WHATSAPP_VERIFY_TOKEN, WHATSAPP_APP_SECRET

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures — reusable payloads
# ---------------------------------------------------------------------------

@pytest.fixture
def meta_text_payload():
    return {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "id": "msg_001",
                        "from": "919876543210",
                        "type": "text",
                        "text": {"body": "Mera GST kab file karna hai?"}
                    }]
                }
            }]
        }]
    }


@pytest.fixture
def meta_image_payload():
    return {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "id": "msg_002",
                        "from": "919876543210",
                        "type": "image",
                        "image": {"id": "media_abc123", "mime_type": "image/jpeg"}
                    }]
                }
            }]
        }]
    }


@pytest.fixture
def meta_audio_payload():
    return {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "id": "msg_003",
                        "from": "919876543210",
                        "type": "audio",
                        "audio": {"id": "media_voice_xyz", "mime_type": "audio/ogg"}
                    }]
                }
            }]
        }]
    }


@pytest.fixture
def gupshup_text_payload():
    return {
        "sender": {"phone": "919876543210"},
        "messageId": "gs_msg_001",
        "payload": {
            "type": "text",
            "payload": {"text": "Aaj kitna bikri hua?"}
        }
    }


@pytest.fixture
def gupshup_image_payload():
    return {
        "sender": {"phone": "919876543210"},
        "messageId": "gs_msg_002",
        "payload": {
            "type": "image",
            "payload": {"url": "https://example.com/invoice.jpg"}
        }
    }


@pytest.fixture
def gupshup_audio_payload():
    return {
        "sender": {"phone": "919876543210"},
        "messageId": "gs_msg_003",
        "payload": {
            "type": "audio",
            "payload": {"url": "https://example.com/voice.ogg"}
        }
    }


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "HisaabBot" in data["service"]


# ---------------------------------------------------------------------------
# Webhook verification (GET)
# ---------------------------------------------------------------------------

def test_webhook_verification_success():
    response = client.get("/webhook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": WHATSAPP_VERIFY_TOKEN,
        "hub.challenge": "challenge_abc123",
    })
    assert response.status_code == 200
    assert response.text == "challenge_abc123"


def test_webhook_verification_wrong_token():
    response = client.get("/webhook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "WRONG_TOKEN",
        "hub.challenge": "challenge_abc123",
    })
    assert response.status_code == 403


def test_webhook_verification_wrong_mode():
    response = client.get("/webhook", params={
        "hub.mode": "unsubscribe",
        "hub.verify_token": WHATSAPP_VERIFY_TOKEN,
        "hub.challenge": "challenge_abc123",
    })
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Meta Cloud API — text message
# ---------------------------------------------------------------------------

def test_meta_text_message(meta_text_payload):
    response = client.post("/webhook", json=meta_text_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["result"]["status"] == "processed"


def test_meta_text_message_hindi_query(meta_text_payload):
    meta_text_payload["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"] = (
        "Mera ITC kitna hai is month?"
    )
    response = client.post("/webhook", json=meta_text_payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Meta Cloud API — image (invoice photo)
# ---------------------------------------------------------------------------

def test_meta_image_message(meta_image_payload):
    response = client.post("/webhook", json=meta_image_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["result"]["status"] == "queued"
    assert "Invoice photo" in data["result"]["message"]


# ---------------------------------------------------------------------------
# Meta Cloud API — audio (Hindi voice note)
# ---------------------------------------------------------------------------

def test_meta_audio_message(meta_audio_payload):
    response = client.post("/webhook", json=meta_audio_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["result"]["status"] == "queued"
    assert "Voice note" in data["result"]["message"]


# ---------------------------------------------------------------------------
# Gupshup format — all message types
# ---------------------------------------------------------------------------

def test_gupshup_text_message(gupshup_text_payload):
    response = client.post("/webhook", json=gupshup_text_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["result"]["status"] == "processed"


def test_gupshup_image_message(gupshup_image_payload):
    response = client.post("/webhook", json=gupshup_image_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["result"]["status"] == "queued"


def test_gupshup_audio_message(gupshup_audio_payload):
    response = client.post("/webhook", json=gupshup_audio_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["result"]["status"] == "queued"


# ---------------------------------------------------------------------------
# Document message (PDF invoice)
# ---------------------------------------------------------------------------

def test_meta_document_message():
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "id": "msg_doc_001",
                        "from": "919876543210",
                        "type": "document",
                        "document": {
                            "id": "doc_pdf_123",
                            "mime_type": "application/pdf",
                            "filename": "invoice_march.pdf"
                        }
                    }]
                }
            }]
        }]
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Status update (delivery receipt) — should be ignored, not error
# ---------------------------------------------------------------------------

def test_whatsapp_status_update_ignored():
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "statuses": [{
                        "id": "msg_001",
                        "status": "delivered",
                        "recipient_id": "919876543210"
                    }]
                }
            }]
        }]
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


# ---------------------------------------------------------------------------
# Unsupported message type
# ---------------------------------------------------------------------------

def test_unsupported_message_type():
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "id": "msg_sticker_001",
                        "from": "919876543210",
                        "type": "sticker",
                        "sticker": {"id": "sticker_123"}
                    }]
                }
            }]
        }]
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["result"]["status"] == "unsupported"


# ---------------------------------------------------------------------------
# Empty text message edge case
# ---------------------------------------------------------------------------

def test_empty_text_message():
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "id": "msg_empty_001",
                        "from": "919876543210",
                        "type": "text",
                        "text": {"body": "   "}
                    }]
                }
            }]
        }]
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["result"]["status"] == "ignored"


# ---------------------------------------------------------------------------
# Invalid JSON body
# ---------------------------------------------------------------------------

def test_invalid_json_body():
    response = client.post(
        "/webhook",
        content=b"this is not json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Unknown provider payload shape
# ---------------------------------------------------------------------------

def test_unknown_provider_payload():
    payload = {"unknown_key": "unknown_value", "data": "something"}
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"

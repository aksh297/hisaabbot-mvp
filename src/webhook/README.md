# HisaabBot — WhatsApp Webhook Handler

> **"Apna CA, WhatsApp pe" 🇮🇳**  
> This is the front door of HisaabBot. Every invoice photo, Hindi voice note, and GST query from a vendor hits this endpoint first.

---

## What This Does

| Message Type | What Happens |
|---|---|
| 📸 Image (invoice photo) | Routed to OCR pipeline → extracts vendor, GSTIN, amount, HSN |
| 🎤 Audio (Hindi voice note) | Routed to Whisper transcription → intent detection |
| 💬 Text (Hindi/English query) | Routed to NLP intent router → GST / bookkeeping / UPI action |
| 📄 Document (PDF invoice) | Routed to OCR pipeline (same as image) |

---

## Tech Stack

- **Framework:** FastAPI (Python 3.11+)
- **Server:** Uvicorn (async ASGI)
- **Provider Support:** Meta WhatsApp Cloud API + Gupshup (auto-detected)
- **Signature Verification:** HMAC-SHA256 (optional in dev, required in prod)

---

## Local Setup

### 1. Install dependencies

```bash
cd src/webhook
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set environment variables

Create a `.env` file (never commit this):

```env
WHATSAPP_VERIFY_TOKEN=hisaabbot_verify_2026
WHATSAPP_APP_SECRET=your_app_secret_here   # Optional in dev
```

### 3. Run the server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Server will start at: `http://localhost:8000`

Health check: `GET http://localhost:8000/` → `{"status": "ok"}`

---

## Testing with ngrok (Local WhatsApp Testing)

Since WhatsApp requires a **public HTTPS URL** for webhooks, you need a tunnel from `localhost` to the internet during development.

### Step 1: Install ngrok

```bash
# macOS
brew install ngrok

# Linux / Windows: https://ngrok.com/download
```

### Step 2: Authenticate ngrok (one-time)

```bash
ngrok config add-authtoken YOUR_NGROK_TOKEN
```

Get your token at: https://dashboard.ngrok.com/get-started/your-authtoken

### Step 3: Start tunnel

```bash
ngrok http 8000
```

ngrok will give you a URL like:
```
Forwarding: https://abc123.ngrok-free.app → http://localhost:8000
```

Your webhook URL is:
```
https://abc123.ngrok-free.app/webhook
```

### Step 4: Register webhook with Meta (Cloud API)

Go to [Meta Developer Console](https://developers.facebook.com/) → Your App → WhatsApp → Configuration:

- **Callback URL:** `https://abc123.ngrok-free.app/webhook`
- **Verify Token:** `hisaabbot_verify_2026` (from your `.env`)

Click **Verify and Save**. Meta sends a GET request; this server will respond with the challenge automatically.

### Step 5: Register webhook with Gupshup (Recommended for India)

In [Gupshup Dashboard](https://www.gupshup.io/developer/dashboard):
- Go to your app → Settings → Callback URL
- Set: `https://abc123.ngrok-free.app/webhook`

> 💡 **Why Gupshup for India?** Indian company, competitive pricing (₹0.20–₹0.30/message vs Meta's ₹0.86), local support, and faster Green Tick approval in India.

---

## Manual Testing (Without WhatsApp)

Use `curl` or Postman to simulate messages directly:

### Simulate a text message (Meta Cloud API format)

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "id": "msg_001",
            "from": "919876543210",
            "type": "text",
            "text": { "body": "Mera GST kab file karna hai?" }
          }]
        }
      }]
    }]
  }'
```

Expected response:
```json
{
  "status": "ok",
  "result": {
    "status": "processed",
    "message": "Query mili: 'Mera GST kab file karna hai?' — Intent detection ho raha hai... 🤖",
    "sender": "919876543210"
  }
}
```

### Simulate an invoice image (Gupshup format)

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "sender": { "phone": "919876543210" },
    "messageId": "msg_002",
    "payload": {
      "type": "image",
      "payload": {
        "url": "https://example.com/invoice.jpg"
      }
    }
  }'
```

Expected response:
```json
{
  "status": "ok",
  "result": {
    "status": "queued",
    "message": "Invoice photo received. Processing kar rahe hain... 🔄",
    "media_url": "https://example.com/invoice.jpg"
  }
}
```

### Simulate a Hindi voice note

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "sender": { "phone": "919876543210" },
    "messageId": "msg_003",
    "payload": {
      "type": "audio",
      "payload": {
        "url": "https://example.com/voice_note.ogg"
      }
    }
  }'
```

---

## Interactive API Docs

When the server is running, visit:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `WHATSAPP_VERIFY_TOKEN` | Yes | `hisaabbot_verify_2026` | Token used during webhook registration |
| `WHATSAPP_APP_SECRET` | Prod only | _(empty)_ | HMAC secret for payload signature verification |

---

## What's Next (Sprint 2)

This webhook handler is the entry point. The next modules to build are:

| Module | Path | Description |
|---|---|---|
| OCR Engine | `src/ocr/` | Invoice photo → structured JSON (Google Vision + GPT-4o) |
| Voice Processor | `src/nlp/` | Hindi audio → text → intent (Whisper + Claude) |
| GST Engine | `src/gst/` | GSTR-1/3B calculation, HSN mapping, due dates |
| Bookkeeping | `src/bookkeeping/` | Purchase/sales register, daily P&L |
| UPI Reconciliation | `src/upi/` | UPI transaction ↔ invoice matching |

---

## Project Architecture

```
WhatsApp (User sends invoice/voice/text)
        │
        ▼
┌──────────────────────┐
│  /webhook (POST)      │  ← You are here
│  src/webhook/main.py  │
└──────────┬───────────┘
           │
    ┌─────┴─────┐
    │  Auto-detect│
    │  provider   │
    │  (Meta/Gupshup)
    └─────┬─────┘
           │
   ┌───────┴────────────────┐
   │        Message Type?   │
   ├────────────────────────┤
   │ 📸 image  → src/ocr/   │
   │ 🎤 audio  → src/nlp/   │
   │ 💬 text   → src/nlp/   │
   │ 📄 doc    → src/ocr/   │
   └────────────────────────┘

---

*Built with ❤️ for Bharat's 1.6 crore small vendors — HisaabBot Team*
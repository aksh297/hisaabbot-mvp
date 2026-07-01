# Gupshup WhatsApp BSP — Production Rollout Guide (2026)

This document explains **exactly** what the founder needs to do to take HisaabBot from a simulated chat playground → live WhatsApp Business API via **Gupshup**. All code hooks are already in place in `backend/server.py`.

---

## 1. Prerequisites (User action required)

| # | Item | Where | Time |
|---|------|-------|------|
| 1 | A **dedicated phone number** never used on WhatsApp Personal/Business App (or plan a migration). | Any Indian mobile SIM | 1 day |
| 2 | **Meta Business Manager** account with Business Verification submitted (GST cert + address proof). | [business.facebook.com](https://business.facebook.com) | 2–7 days |
| 3 | Approved **Display Name** (e.g., "HisaabBot" or your registered LLP name). | Meta Business Manager | included above |
| 4 | Gupshup account. | [gupshup.io](https://www.gupshup.io) → sign up → contact sales for BSP quote | 1–3 days |
| 5 | Pre-paid **wallet balance** (start with USD $50 ≈ ₹4,200). | Gupshup dashboard → Billing | same-day |

Gupshup is generally faster than Interakt/AiSensy for Indian BSPs (10–15 min BSP setup once Meta verification is done). 2026 pricing is per-message pay-as-you-go: **Marketing ≈ ₹1.09** · **Utility/Auth ≈ ₹0.145** · **Service (24-hour window) = free**.

---

## 2. Templates you must submit for approval

Meta requires all outbound business-initiated messages to use pre-approved templates. Submit these **five** on Gupshup dashboard → *Templates → Create*.

### Template 1 · `hisaabbot_welcome` (Utility · Hindi/English)
```
Namaste {{1}}! 🙏 Main HisaabBot hoon — aapka digital CA.

Aap chaahein toh:
📷 Invoice ki photo bhejein
🎤 Voice note bolein
💬 Sirf type karein (Hindi/English)

Shuru karne ke liye apna GSTIN bhejiye.
```
**Variables**: `{{1}}` = User's first name.

### Template 2 · `hisaabbot_gstin_verified` (Utility)
```
✅ GSTIN Verified

Business: {{1}}
State: {{2}}

Ab aap invoices bhej sakte hain. Pehli invoice photo bhejein.
```
Variables: `{{1}}` = business name, `{{2}}` = state.

### Template 3 · `hisaabbot_deadline_reminder` (Utility)
```
⏰ GST Filing Reminder

{{1}} ki last date hai *{{2}}*.
Aapke paas {{3}} din baaki hain.

Filing status dekhne ke liye 'STATUS' likhein.
```
Variables: `{{1}}` = GSTR-1/GSTR-3B, `{{2}}` = date, `{{3}}` = days left.

### Template 4 · `hisaabbot_payment_received` (Utility)
```
💰 UPI Payment Received

Amount: ₹{{1}}
From: {{2}}
Ref: {{3}}

{{4}}
```
Variables: `{{1}}` = amount, `{{2}}` = payer, `{{3}}` = UPI ref, `{{4}}` = "Auto-matched to Invoice #{{invoice_num}}" or "Match not found — reply MATCH #<invoice> to link".

### Template 5 · `hisaabbot_monthly_summary` (Marketing)
```
📊 {{1}} ka summary

Bikri: ₹{{2}}
Khareedari: ₹{{3}}
Profit: ₹{{4}}
GST payable: ₹{{5}}

Full report: {{6}}
```
Variables: `{{1}}` = month name, `{{2..5}}` = amounts, `{{6}}` = dashboard link.

**Rejection avoidance tips**:
- Always include variables (`{{n}}`) — Meta rejects static promos.
- Use category **Utility** for reminders / status / receipts (₹0.145 rate).
- Use **Marketing** only for the monthly summary teaser (₹1.09 rate).
- No emojis in `{{variables}}` themselves.

---

## 3. Webhook wiring

In your Gupshup dashboard → *Settings → Callback URL*, set the callback to:

```
https://<your-hisaabbot-domain>/api/whatsapp/webhook
```

The endpoint is already implemented at `backend/server.py :: whatsapp_webhook`. It receives all inbound messages and logs them into the `whatsapp_events` collection. For production, extend it to:
1. Identify the sender by mobile number → lookup or create a `users` doc.
2. Route the payload to the OCR / voice-extract / chat pipeline (all already built).
3. Send outbound reply via Gupshup Send API.

## 4. Outbound send helper (drop-in code)

Save your Gupshup API key + source number into `backend/.env`:

```
GUPSHUP_API_KEY=xxx
GUPSHUP_APP_NAME=hisaabbot
GUPSHUP_SOURCE=+91XXXXXXXXXX
```

Then use this helper — a stub is already present as `whatsapp_webhook`; add the sender next:

```python
import httpx

async def wa_send_text(to: str, text: str):
    """Send a session (free) text message within the 24-hour window."""
    url = "https://api.gupshup.io/wa/api/v1/msg"
    headers = {"apikey": os.environ["GUPSHUP_API_KEY"],
               "Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "channel": "whatsapp",
        "source": os.environ["GUPSHUP_SOURCE"],
        "destination": to,
        "message": json.dumps({"type": "text", "text": text}),
        "src.name": os.environ["GUPSHUP_APP_NAME"],
    }
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(url, headers=headers, data=data)
        return r.json()

async def wa_send_template(to: str, template_name: str, params: list[str]):
    """Send an approved template message (paid — utility ₹0.145 or marketing ₹1.09)."""
    url = "https://api.gupshup.io/wa/api/v1/template/msg"
    headers = {"apikey": os.environ["GUPSHUP_API_KEY"],
               "Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "source": os.environ["GUPSHUP_SOURCE"],
        "destination": to,
        "template": json.dumps({"id": template_name, "params": params}),
        "src.name": os.environ["GUPSHUP_APP_NAME"],
    }
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(url, headers=headers, data=data)
        return r.json()
```

## 5. Onboarding sequence (once live)

1. User sends any message → webhook fires.
2. Backend checks `users` collection by phone; if none → send `hisaabbot_welcome` template.
3. User replies GSTIN → backend calls `/api/gstin/verify` → sends `hisaabbot_gstin_verified`.
4. User sends invoice photo → backend fetches media, runs `/api/invoices/ocr` → replies with structured summary asking to confirm.
5. User says "haan" / "yes" → backend saves invoice to DB.

## 6. Cost projection (100 users, 30 msgs/day/user each)

- 30 × 100 × 30 days = **90,000 msgs/mo** — mostly session (free) once user replies first.
- 5 utility reminders × 100 users × 4 weeks = **2,000 utility × ₹0.145 ≈ ₹290/mo**
- 1 marketing monthly summary × 100 users = **100 × ₹1.09 ≈ ₹110/mo**
- Total variable cost: **≈ ₹400/mo for 100 users** — safe within Rs.999/mo Starter unit-economics.

---

## Status inside HisaabBot codebase

| Component | Status |
|-----------|--------|
| `POST /api/whatsapp/webhook` receiver | ✅ Live (logs to Mongo) |
| Outbound send helpers (`wa_send_text` / `wa_send_template`) | ⏳ Draft included above — activate on go-live |
| Template messages | ⏳ Draft ready — submit to Gupshup |
| Chat pipeline (GPT-4o + OCR + Whisper) | ✅ Same code path serves both playground and live WhatsApp |

Once user provides `GUPSHUP_API_KEY` + `GUPSHUP_SOURCE`, wiring the sender is a **30-minute** change.

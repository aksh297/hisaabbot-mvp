# HisaabBot — Invoice OCR Engine

> **"Invoice ki photo bhejo, hum baaki sambhal lenge" 📸**
> Send an invoice photo, we'll handle the rest.

This module powers HisaabBot's ability to read Indian GST tax invoices from photos and extract structured financial data — vendor name, GSTIN, amounts, tax breakdown, HSN codes — ready for bookkeeping and GSTR filing.

---

## Architecture

```
Invoice Image (URL or local path)
          │
          ▼
┌─────────────────────────┐
│  Google Cloud Vision    │  ← Reads text from any image (even handwritten)
│  Document Text Detection│    Handles skewed, blurry, low-light photos
└────────────┬────────────┘
             │  Raw OCR text
             ▼
┌─────────────────────────┐
│  GPT-4o (Bharat-first)  │  ← Understands Hindi/Hinglish labels
│  Structured Extraction  │    GSTIN validation, Indian number format
└────────────┬────────────┘
             │  JSON
             ▼
┌─────────────────────────┐
│  InvoiceData (Pydantic) │  ← Type-safe, validated output
│  + Heuristic fallback   │    Works without OpenAI key in dev
└─────────────────────────┘
```

---

## Quick Start

### 1. Clone and set up environment

```bash
cd src/ocr
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure credentials

Create a `.env` file in `src/ocr/` (never commit this file):

```env
# ── Google Cloud Vision ──────────────────────────────────────
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/gcp-service-account.json

# ── OpenAI (GPT-4o for structured extraction) ────────────────
OPENAI_API_KEY=sk-proj-...

# ── Dev mode (set to "1" to skip real API calls) ─────────────
HISAABBOT_OCR_MOCK=0
```

### 3. Use in code

```python
from invoice_extractor import InvoiceExtractor

extractor = InvoiceExtractor()

# From a WhatsApp media URL
result = extractor.extract("https://cdn.whatsapp.net/invoice_xyz.jpg")

# From a local file path
result = extractor.extract("/tmp/sharma_textiles_invoice.jpg")

print(result.model_dump_json(indent=2))
```

**Output example:**
```json
{
  "vendor_name": "Sharma Textiles Pvt. Ltd.",
  "vendor_gstin": "08AABCU9603R1ZM",
  "buyer_name": "Patel Garments",
  "buyer_gstin": "24AADCP3456Q1ZR",
  "invoice_number": "ST/2526/001247",
  "invoice_date": "2026-06-15",
  "place_of_supply": "Gujarat (24)",
  "subtotal_amount": 70000.0,
  "total_amount": 78400.0,
  "tax": {
    "cgst_rate": null,
    "cgst_amount": null,
    "sgst_rate": null,
    "sgst_amount": null,
    "igst_rate": 12.0,
    "igst_amount": 8400.0,
    "cess_amount": null,
    "total_tax_amount": 8400.0
  },
  "hsn_codes": ["5208", "5512"],
  "confidence": "high",
  "parse_warnings": []
}
```

---

## Setting Up Google Cloud Vision

### Step 1: Create a GCP Project

1. Go to https://console.cloud.google.com/
2. Create a new project: `hisaabbot-prod`
3. Enable the **Cloud Vision API**:
   - Navigate to **APIs & Services → Library**
   - Search "Cloud Vision API" → Click **Enable**

### Step 2: Create a Service Account

1. Go to **IAM & Admin → Service Accounts**
2. Click **Create Service Account**
   - Name: `hisaabbot-ocr`
   - Role: `Cloud Vision API User`
3. Click on the service account → **Keys** tab → **Add Key → JSON**
4. Download the JSON key file

### Step 3: Configure the key path

```bash
# Set in your shell or .env file:
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/hisaabbot-ocr-key.json"
```

### Cost estimate

| Volume | Cost |
|---|---|
| 1,000 invoices/month | Free (Vision free tier: 1,000 units/month) |
| 10,000 invoices/month | ~$15/month ($1.50 per 1,000 after free tier) |
| 1 lakh invoices/month | ~$150/month |

> 💡 At ₹999/month per user, Vision OCR costs are < 0.2% of revenue at scale.

---

## Setting Up OpenAI API Key

### Step 1: Create an OpenAI account

1. Go to https://platform.openai.com/
2. Sign up / Log in
3. Navigate to **API Keys** → **Create new secret key**
4. Name it: `hisaabbot-invoice-parser`

### Step 2: Set billing limits

In **Settings → Billing**, set a monthly hard limit (recommended: $50/month to start).

### Step 3: Configure the key

```bash
export OPENAI_API_KEY="sk-proj-your-key-here"
```

### Cost estimate (GPT-4o)

| Volume | Tokens per invoice | Cost |
|---|---|---|
| 1,000 invoices/month | ~800 tokens | ~$2/month |
| 10,000 invoices/month | ~800 tokens | ~$20/month |
| 1 lakh invoices/month | ~800 tokens | ~$200/month |

> 💡 GPT-4o pricing as of 2026: ~$2.50/1M input tokens, $10/1M output tokens.

---

## Development Without API Keys

The module is fully functional without any real credentials using **mock mode**:

```python
# Auto-enabled when GOOGLE_APPLICATION_CREDENTIALS is not set
extractor = InvoiceExtractor()   # mock_mode=True automatically

# Or force mock mode explicitly
extractor = InvoiceExtractor(mock_mode=True)

# Or via environment variable
# HISAABBOT_OCR_MOCK=1
```

In mock mode:
- `extract_raw_text()` returns a realistic Indian GST invoice fixture
- `parse_with_llm()` uses the heuristic regex parser (no LLM call)
- All tests pass without any cloud credentials

---

## Running Tests

```bash
cd src/ocr
python -m pytest test_invoice_extractor.py -v
```

---

## Indian GST Invoice Formats Supported

| Format | Source | Notes |
|---|---|---|
| Tally ERP 9 / TallyPrime | Most common for MSMEs | PDF/image export |
| Busy Accounting | North Indian traders | Similar to Tally |
| Zoho Books | Tech-savvy MSMEs | Clean digital format |
| Hand-typed / Printed | Small kiranas | Handwritten amounts OK |
| Hindi-labelled invoices | Rural vendors | "विक्रेता", "दिनांक" etc. |
| Hinglish invoices | Mixed language | "Bill No.", "दिनांक" mix |
| Multi-page invoices | B2B suppliers | Only first page parsed in MVP |

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | Prod | _(empty)_ | Path to GCP service account JSON |
| `OPENAI_API_KEY` | Prod | _(empty)_ | OpenAI API key for GPT-4o |
| `HISAABBOT_OCR_MOCK` | Dev | `0` | Set to `1` to force mock mode |

---

## Integration with WhatsApp Webhook

When a vendor sends an invoice photo on WhatsApp, the webhook handler
(`src/webhook/main.py`) calls this module:

```python
# In src/webhook/main.py — process_invoice_photo()
from ocr.invoice_extractor import InvoiceExtractor

extractor = InvoiceExtractor()
invoice_data = extractor.extract(media_url)

# invoice_data.total_amount, invoice_data.vendor_gstin, etc. are now available
# → Pass to bookkeeping engine (src/bookkeeping/)
# → Validate GSTIN against GST portal (src/gst/)
```

---

## What's Next (Sprint 3)

| Feature | Description |
|---|---|
| PDF support | Multi-page PDF invoices via `pypdf2` pre-processing |
| Voice-to-invoice | Hindi voice note → Whisper transcription → same extraction |
| ITC auto-match | Match vendor GSTIN against buyer's ITC register |
| Duplicate detection | Flag if same invoice number seen before |
| Confidence threshold | Auto-reject if `confidence == "low"` and ask user to reshoot |

---

*Built with ❤️ for Bharat's 1.6 crore small vendors — HisaabBot Team*

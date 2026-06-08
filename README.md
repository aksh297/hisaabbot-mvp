# 🇮🇳 HisaabBot — Apna CA, WhatsApp pe

> **Your AI-powered CA, right on WhatsApp.**  
> GST filing, bookkeeping, and UPI reconciliation — in Hindi, for Bharat's 1.6 crore+ small vendors.

---

## 🌟 Vision: Bharat-First

India has **7.9 crore registered MSMEs** and **1.6 crore active GST taxpayers**. The vast majority are small shopkeepers, traders, and freelancers who:

- 📱 Live on **WhatsApp** — not apps, not desktops
- 🗣️ Think in **Hindi / regional languages** — not English
- 💸 Pay **₹2,000–₹5,000/month** to CAs just for basic GST compliance
- 😰 Miss filing deadlines, pay ₹50/day penalties, and fear the government portal

**HisaabBot solves this.** Send an invoice photo. Speak a voice note in Hindi. HisaabBot handles GST entry, GSTR-1/3B preparation, UPI payment matching, and deadline reminders — all inside WhatsApp for just **₹999/month**.

No app download. No English required. No complex software.

---

## 💡 The Problem

| Pain Point | Scale |
|------------|-------|
| Small vendors paying CAs ₹2,000–5,000/month for basic GST | 1.6 crore taxpayers |
| Missed GST deadlines leading to ₹50/day penalties | Thousands of crores lost annually |
| English-only tax software failing non-English speakers | 80%+ of India's MSMEs |
| Manual reconciliation of UPI payments with invoices | Daily operational pain |
| No real-time visibility into business finances | Every small vendor |

---

## ✅ The Solution: HisaabBot

```
User sends invoice photo on WhatsApp
        ↓
OCR extracts: vendor name, GSTIN, amount, HSN code, tax
        ↓
AI categorizes, maps HSN codes, updates purchase/sales register
        ↓
GST engine prepares GSTR-1 and GSTR-3B
        ↓
UPI transactions auto-matched to invoices
        ↓
Filing-ready data sent to GSP for submission
        ↓
Owner gets daily summary in Hindi: "Aaj ki bikri ₹45,000"
```

### Core Features (MVP)
- 📸 **Invoice Capture via WhatsApp** — photo, PDF, or voice note
- 📊 **Automated Bookkeeping** — real-time purchase & sales register
- 🧾 **GST Compliance Engine** — GSTR-1, GSTR-3B, ITC reconciliation
- 💳 **UPI Reconciliation** — auto-match UPI payments to invoices
- 🗣️ **Vernacular Interface** — Hindi-first, English supported, voice input
- 🔔 **Smart Reminders** — filing deadlines, penalty alerts, daily summaries

---

## 🏗️ Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| **WhatsApp API** | Gupshup (Indian) | Best pricing, Indian company, local support |
| **LLM / AI** | Claude (Anthropic) + GPT-4o | Superior Hindi understanding, structured output |
| **OCR** | Google Cloud Vision | Handles Hindi + English mixed text invoices |
| **Voice** | OpenAI Whisper | Best-in-class Hindi transcription |
| **Backend** | Python FastAPI / Node.js | Fast development, rich AI ecosystem |
| **Database** | PostgreSQL + Redis | Reliable, scalable, affordable on AWS |
| **Hosting** | AWS Mumbai (ap-south-1) | Data residency in India, low latency |
| **Payments** | Razorpay | UPI autopay, Indian compliance built-in |
| **GST Filing** | Masters India GSP API | Direct GSTN submission, GSTR auto-filing |

---

## 📂 Repository Structure

```
hisaabbot-mvp/
├── README.md                   ← You are here
├── REPORT.md                   ← Full India market research & opportunity analysis
├── PRD.md                      ← Complete Product Requirements Document
├── LANDING_PAGE_COPY.md        ← WhatsApp-first marketing copy (Hindi/Hinglish)
├── EXECUTION_CHECKLIST.md      ← 30-day actionable launch checklist
├── src/
│   ├── webhook/                ← WhatsApp webhook handler (coming soon)
│   ├── ocr/                    ← Invoice OCR pipeline (coming soon)
│   ├── gst/                    ← GST compliance engine (coming soon)
│   ├── bookkeeping/            ← Purchase/sales register logic (coming soon)
│   └── upi/                    ← UPI reconciliation module (coming soon)
├── db/
│   └── schema.sql              ← PostgreSQL schema (coming soon)
└── docs/
    └── architecture.md         ← System architecture diagram (coming soon)
```

---

## 💰 Market Opportunity (India)

| Metric | Value |
|--------|-------|
| **TAM** | ₹5,832 crore/year (1.6 crore taxpayers × ₹3,000/month avg spend) |
| **SAM** | ₹1,920 crore/year (80 lakh small vendors in ₹40L–₹5Cr turnover bracket) |
| **SOM Year 1** | ₹60 crore ARR (50,000 vendors × ₹999/month) |
| **SOM Year 2** | ₹240 crore ARR (2 lakh vendors × ₹1,199/month) |
| **Gross Margin** | 70–80% |
| **Break-even** | ~800 paying customers |

---

## 🏷️ Pricing

| Plan | Price | For |
|------|-------|-----|
| **Free** | ₹0 | 10 invoices/month, reminders only |
| **Starter** | ₹999/month | Unlimited invoices, GSTR-1 + 3B prep, UPI reconciliation |
| **Pro** | ₹1,999/month | Auto-filing, all Indian languages, ITC reconciliation |
| **CA Plan** | ₹499/client/month | Bulk dashboard, white-label, client management |

---

## 🚀 Go-to-Market (First 1,000 Users)

1. **WhatsApp Viral Loops** — GST deadline reminders as free utility, referral program
2. **Ground Sales** — Field agents in Jaipur/Noida markets, live phone demos
3. **CA Partnerships** — CAs earn ₹200/client/month as resellers
4. **YouTube Shorts / Reels** — "GST filing in 2 min on WhatsApp" in Hindi
5. **Vyapari Sangh** — Bulk onboarding at trade body meetings before GST due dates

---

## 📅 MVP Build Timeline

| Week | Milestone |
|------|----------|
| 1 | WhatsApp webhook + message routing + basic NLP |
| 2 | OCR pipeline: invoice photo → structured data |
| 3 | GST logic engine: GSTR-1/3B calculation |
| 4 | Bookkeeping module: purchase/sales register |
| 5 | Hindi NLP + voice transcription (Whisper) |
| 6 | UPI reconciliation (SMS/screenshot parsing) |
| 7 | Onboarding flow, GSTIN verification, user management |
| 8 | 50-user beta testing, accuracy tuning, bug fixes |

---

## 🤝 Competitive Edge

| Competitor | Weakness vs HisaabBot |
|-----------|----------------------|
| ClearTax | Web/app only, English-first, ₹5,000+/year, complex |
| Zoho Books | Enterprise-grade, overwhelming for small vendors |
| Tally | Desktop software, ₹18,000+ license, requires training |
| Local CA | Expensive, misses deadlines, no real-time visibility |
| Vyapar App | Good but app-based, no WhatsApp-native, limited GST depth |

**HisaabBot's moat:** The only solution that is simultaneously WhatsApp-native + vernacular + voice-first + AI-powered + GST-compliant. Zero app download required.

---

## 📋 Documents

| Document | Description |
|----------|-------------|
| [`REPORT.md`](./REPORT.md) | Full India market research, trend analysis, 3 problem evaluations |
| [`PRD.md`](./PRD.md) | Complete product spec with architecture, personas, features, GTM |
| [`LANDING_PAGE_COPY.md`](./LANDING_PAGE_COPY.md) | WhatsApp marketing copy in Hindi/Hinglish, YouTube scripts, ad copy |
| [`EXECUTION_CHECKLIST.md`](./EXECUTION_CHECKLIST.md) | 30-day actionable checklist with budget breakdown |

---

## 🌐 Built for Bharat

> "Jitna simple WhatsApp pe message karna, utna hi simple GST filing."
> *(As simple as sending a WhatsApp message, that's how simple GST filing should be.)*

---

*Built with ❤️ for India's small business owners — by Xyros Entrepreneur Mode, June 2026*

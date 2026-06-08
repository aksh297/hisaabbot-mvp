# Product Requirements Document (PRD)
# HisaabBot — WhatsApp-Native AI GST & Bookkeeping Assistant

**Version:** 1.0  
**Date:** June 9, 2026  
**Author:** Xyros (Entrepreneur Mode)

---

## 1. Product Overview

**HisaabBot** is a WhatsApp-native AI assistant that helps India's small vendors and MSMEs manage GST compliance, bookkeeping, and payment reconciliation — entirely through chat, in their preferred language.

**Tagline:** "Apna CA, WhatsApp pe" (Your CA, on WhatsApp)

---

## 2. Target User Persona

### Primary: Ramesh — Small Garment Trader, Jaipur/Noida
- **Age:** 35-50
- **Business:** Rs.80L–Rs.3Cr annual turnover
- **Tech:** Android phone (Rs.10-15K), WhatsApp daily user, UPI for payments
- **Language:** Hindi primary, limited English
- **Pain:** Doesn't understand HSN codes, forgets filing dates, can't reconcile UPI payments with invoices, fears penalties

### Secondary: Priya — CA Managing 40+ Small Clients
- **Age:** 28-40
- **Challenge:** Chasing clients for invoices every month, manual data entry from photos/PDFs
- **Need:** Automated data collection from clients, bulk filing dashboard

---

## 3. Core Features (MVP — 8 Weeks)

### 3.1 Invoice Capture via WhatsApp
- User sends **photo** of purchase/sales invoice → OCR extracts: vendor name, GSTIN, amount, tax, HSN code, date
- User sends **voice note** ("Aaj Sharma Textiles se 50,000 ka maal aaya, 12% GST") → transcription + structured extraction
- User types in **Hindi/English** → AI understands and records

**Tech Stack:** Google Cloud Vision OCR + GPT-4o for Hindi context + Whisper for voice + custom HSN classifier

### 3.2 Automated Bookkeeping
- Maintains digital purchase register and sales register
- Auto-categorizes expenses
- Daily summary: "Aaj ki bikri: Rs.45,000 | Khareedari: Rs.12,000 | UPI received: Rs.38,000"
- Monthly P&L on request ("Mahine ka hisaab bhejo")

### 3.3 GST Compliance Engine
- GSTR-1 preparation from sales register
- GSTR-3B: tax liability, ITC available, net payable
- HSN code mapping (AI suggests based on Hindi/English description)
- Due date reminders: 5 days, 2 days, and on due date
- Penalty calculator
- ITC reconciliation with supplier GSTR-1

### 3.4 UPI Payment Reconciliation
- Forward UPI confirmation screenshots → AI matches to invoices
- Highlights unmatched payments
- Daily cash flow summary

### 3.5 Vernacular Interface
- **Languages (MVP):** Hindi, English
- **Languages (V2):** Tamil, Telugu, Marathi, Gujarati, Bengali
- Full voice input support
- Handles Hinglish naturally
- Friendly, respectful tone ("aap" form)

### 3.6 Sample Onboarding Flow
```
Bot: Namaste! Main HisaabBot hoon — aapka digital CA.
     Shuru karne ke liye apna GSTIN bhejiye.
User: 08AABCU9603R1ZM
Bot: Verified! Aap "Sharma Textiles" hain, Jaipur.
     GST filing type: Monthly GSTR-1 + GSTR-3B
     Next due date: 11 July 2026 (GSTR-1)
     
     Ab se aap mujhe invoices ki photo bhej sakte hain.
     Kya shuru karein?
     1 - Invoice ki photo bhejo
     2 - Aaj ki bikri batao
     3 - GST filing status dekho
```

---

## 4. Technical Architecture

```
USER (WhatsApp)
       ↓
WhatsApp Business API (Gupshup/Wati)
- Webhook receiver, message router, media downloader
       ↓
AI Processing Layer
- OCR Engine (Google Vision)
- NLP/LLM (GPT-4o / Claude)
- Voice (Whisper)
       ↓
Business Logic Layer
- GST Engine
- Bookkeeping
- UPI Reconciliation
       ↓
Data Layer
- PostgreSQL (vendor data, invoices, transactions)
- Redis (session state, rate limiting)
- S3 (invoice images, voice recordings)
```

---

## 5. Monetization Model

| Plan | Price | Features |
|------|-------|----------|
| **Free** | Rs.0 | 10 invoices/month, GST reminders only |
| **Starter** | Rs.999/month | Unlimited invoices, GSTR-1 + 3B prep, UPI reconciliation, Hindi + English |
| **Pro** | Rs.1,999/month | Auto-filing via GSP, ITC reconciliation, all languages, priority support |
| **CA Plan** | Rs.499/client/month | Bulk dashboard, white-label, client management |

**Payment:** UPI autopay via Razorpay subscription

---

## 6. Competitive Landscape

| Competitor | Weakness vs HisaabBot |
|------------|----------------------|
| ClearTax | App/web only, English-first, Rs.5,000+/year, complex UI |
| Zoho Books | Enterprise-grade, overwhelming for small vendor, no WhatsApp |
| Tally | Desktop software, requires training, Rs.18,000+ license |
| Local CA | Expensive (Rs.2-5K/month), misses deadlines, no real-time visibility |
| Vyapar App | Good but app-based, limited GST depth, no WhatsApp-native |

**HisaabBot's moat:** Only solution that is WhatsApp-native + vernacular + voice-first + AI-powered for GST compliance.

---

## 7. Tech Stack

| Component | Tool | Reason |
|-----------|------|--------|
| WhatsApp API | Gupshup | Indian company, good support, competitive pricing |
| LLM | GPT-4o / Claude | Best Hindi understanding, structured output |
| OCR | Google Cloud Vision | Handles Hindi + English mixed text well |
| Voice | Whisper API (OpenAI) | Excellent Hindi transcription |
| Backend | Node.js / Python FastAPI | Fast development, good AI library ecosystem |
| Database | PostgreSQL + Redis | Reliable, scalable, cost-effective |
| Hosting | AWS Mumbai region | Low latency for Indian users, data residency |
| Payments | Razorpay | UPI autopay, Indian compliance built-in |
| GST Filing | Masters India GSP API | Direct GSTN submission |

---

## 8. MVP Development Timeline

| Week | Deliverable | Team |
|------|------------|------|
| 1 | WhatsApp webhook setup, message routing, basic NLP | Backend dev |
| 2 | OCR pipeline: photo to structured invoice data | AI/ML eng |
| 3 | GST logic: GSTR-1/3B calculation engine | Backend dev |
| 4 | Bookkeeping module: purchase/sales register | Backend dev |
| 5 | Hindi NLP + voice transcription integration | AI/ML eng |
| 6 | UPI reconciliation (SMS/screenshot parsing) | Backend dev |
| 7 | Onboarding flow, GSTIN verification, user management | Full-stack |
| 8 | Testing with 50 beta users, bug fixes, accuracy tuning | All |

**Team needed:** 2 backend devs, 1 AI/ML engineer, 1 product manager

---

*End of PRD v1.0*

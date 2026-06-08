# HisaabBot — Execution Checklist (First 30 Days)

## Week 1: Foundation Setup

- [ ] Register WhatsApp Business API account (via Gupshup — Indian BSP)
- [ ] Set up cloud infrastructure (AWS Mumbai — ap-south-1)
- [ ] Create PostgreSQL database schema (vendors, invoices, transactions, gst_returns)
- [ ] Build webhook receiver for WhatsApp messages
- [ ] Set up OCR pipeline: photo → Google Vision → structured JSON
- [ ] Test OCR on 50 sample Indian invoices (Hindi + English mixed)
- [ ] Register domain: hisaabbot.in / hisaabbot.com
- [ ] Create basic landing page (WhatsApp link as CTA)

## Week 2: Core AI Integration

- [ ] Integrate GPT-4o for Hindi invoice understanding + HSN code mapping
- [ ] Build voice note pipeline: download audio → Whisper transcription → NLU
- [ ] Create GST calculation engine (CGST/SGST/IGST logic)
- [ ] Build GSTR-1 JSON generation (matching GSTN format)
- [ ] Build GSTR-3B summary calculator
- [ ] Implement GSTIN verification via public API
- [ ] Create onboarding conversational flow (GSTIN → verification → welcome)

## Week 3: UPI & Bookkeeping

- [ ] Build UPI screenshot parser (extract: amount, UPI ID, date, ref number)
- [ ] Create invoice-payment matching algorithm
- [ ] Build daily summary message generator
- [ ] Create purchase register and sales register views
- [ ] Add expense categorization (auto + user confirmation)
- [ ] Build "monthly P&L" report generator
- [ ] Test with personal UPI transactions

## Week 4: Beta Launch

- [ ] Recruit 50 beta users (personal network + 2-3 Noida/Jaipur market visits)
- [ ] Set up error logging and accuracy tracking
- [ ] Create feedback collection flow (after each interaction)
- [ ] Monitor OCR accuracy, fix edge cases
- [ ] Add GST due date reminder system (cron-based)
- [ ] Create user dashboard (simple web view for checking status)
- [ ] Document all failure cases for improvement

## Parallel: Business Setup

- [ ] Register company (LLP or Pvt Ltd)
- [ ] Open business bank account
- [ ] Set up Razorpay for subscription payments
- [ ] Create UPI autopay mandate flow for ₹999/month
- [ ] Draft Terms of Service and Privacy Policy (Hindi + English)
- [ ] Get legal opinion on data handling (financial data sensitivity)

## Budget Estimate (First 3 Months)

| Item | Monthly Cost |
|------|-------------|
| WhatsApp Business API (Gupshup) | ₹5,000 base + per-message |
| AWS infrastructure | ₹15,000 |
| OpenAI API (GPT-4o + Whisper) | ₹30,000 |
| Google Cloud Vision | ₹10,000 |
| Domain + hosting | ₹500 |
| Marketing (initial) | ₹25,000 |
| Field agents (2, part-time) | ₹30,000 |
| **Total** | **~₹1,15,500/month** |

**Funding needed for 6-month runway:** ₹7-8 lakhs (bootstrappable)

---

## Decision Log

| Decision | Rationale |
|----------|----------|
| Start with Noida/Jaipur | Strong trader community, Hindi-speaking, accessible markets |
| WhatsApp-only (no app) | Zero friction adoption. 90% of target users are on WhatsApp daily. |
| Hindi-first, English-second | Target users are Hindi-primary. |
| ₹999/month pricing | 3x cheaper than average CA. High enough for unit economics. |
| Partner with CAs, not fight them | CAs are distribution channel, not competition. |
| Gupshup over Twilio | Indian company, INR billing, better India support, competitive rates. |

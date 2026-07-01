# HisaabBot — Product Requirements & Living PRD

**Last updated:** 2026-07-01

## Original Problem Statement
> Build a mobile app: Help me build this app and connect it via whatsapp and GST portal.

The user provided detailed HisaabBot PRD, README, execution checklist, and landing-page copy artefacts. HisaabBot is a WhatsApp-native AI GST & Bookkeeping Assistant for India's small vendors (Ramesh, garment trader, Jaipur; Priya, CA managing 40+ small clients).

## User Choices (Session 1)
- **Interface:** Full stack — web dashboard + WhatsApp webhook backend + simulated in-app WhatsApp chat playground.
- **WhatsApp BSP:** Gupshup (webhook stub only for MVP).
- **GST portal:** Regex-based public GSTIN verification + simulated GSTR-1/3B JSON generation. Real GSP integration (Masters India / ClearTax) deferred.
- **AI stack:** OpenAI GPT-4o (vision + text) + Whisper via Emergent Universal LLM Key.
- **Scope:** Full MVP — invoice OCR, bookkeeping (purchase/sales), GSTR-1/3B calculator, UPI reconciliation, Hindi voice notes, dashboard, simulated WhatsApp chat.

## Architecture
- **Backend:** FastAPI + Motor (MongoDB) + emergentintegrations (OpenAI wrapper). Single `server.py`.
- **Frontend:** React 18 + React Router + Tailwind CSS + Framer Motion + Sonner (toasts) + lucide-react (icons).
- **Auth:** JWT (Bearer via `localStorage.hb_token`; cookie fallback for same-origin).
- **AI models:** `gpt-4o` for OCR/chat, `whisper-1` for STT (both via `EMERGENT_LLM_KEY`).
- **Storage:** MongoDB collections — `users`, `invoices`, `upi_transactions`, `chat_messages`, `whatsapp_events`. Uploads on disk at `/app/backend/uploads`, served under `/api/uploads/`.

## What's Been Implemented
### Backend endpoints
- `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
- `POST /api/gstin/verify` — regex + state/PAN derivation.
- `POST /api/invoices/ocr` — GPT-4o vision extracts invoice fields from photo.
- `POST /api/invoices` (create), `GET /api/invoices?type=&month=`, `DELETE /api/invoices/{id}`.
- `POST /api/voice/transcribe` (Whisper), `POST /api/voice/extract` (Whisper + GPT-4o), `POST /api/voice/extract-text` (text-only fallback).
- `POST /api/upi/parse` — GPT-4o parses UPI screenshot, auto-suggests matching invoice.
- `POST /api/upi/transactions`, `GET /api/upi/transactions`.
- `GET /api/gst/summary?month=` — computes GSTR-1 + GSTR-3B locally.
- `GET /api/gst/deadlines` — next GSTR-1 (11th) & 3B (20th).
- `GET /api/dashboard/summary` — today + month + UPI + deadlines.
- `POST /api/chat/message` — GPT-4o chat with optional image (OCR + confirm), `GET /api/chat/history`.
- `POST /api/whatsapp/webhook` — Gupshup-format inbound stub.
- Seeds admin + demo vendor (`ramesh@hisaabbot.in`) with 4 sample invoices + 2 UPI txns on startup.

### Frontend pages
- `/` — Bharat-first landing page (Hindi hero "Apna CA, WhatsApp pe", phone-mock, features grid, pricing tiers, CA section).
- `/login`, `/signup` — auth with GSTIN/business fields.
- `/app` — dashboard shell with sidebar nav + topbar business/GSTIN.
- `/app` (home) — 4 stat cards, month-to-date summary, deadlines, quick actions.
- `/app/chat` — WhatsApp-styled chat playground with image attachment + quick chips.
- `/app/invoices` — OCR upload → confirm → register; manual entry; filter by type.
- `/app/gst` — GSTR-1 sales table + GSTR-3B tax liability summary; month picker; JSON export.
- `/app/upi` — Screenshot parse + suggested match + manual entry.
- `/app/voice` — Mic record OR file upload OR direct text → transcript + structured extract → save as invoice.
- `/app/settings` — profile view + GSTIN verify + Gupshup setup steps.

## Testing status
- **Backend:** 16/16 pytest cases PASS (see `/app/backend/tests/backend_test.py`).
- **Frontend:** All critical flows verified via Playwright.
- No critical bugs open.

## Backlog (P0/P1/P2)
### P0 (before production launch)
- Real Gupshup WhatsApp Business API wiring (template approval, delivery status).
- Real GSTN GSP integration (Masters India / ClearTax) for GSTR-1 & 3B filing.
- Razorpay/UPI autopay for subscriptions.

### P1
- CA Plan bulk dashboard (view all client vendors, filing status).
- Multi-language full localization (currently Hinglish/English; Marathi/Tamil/Gujarati stubs in signup).
- Refresh-token rotation + password reset flow.
- E-invoicing (IRN) integration for B2B > ₹5Cr customers.

### P2
- Split `server.py` into `routers/` and `models/` modules.
- Rich PDF invoice export.
- WhatsApp business template messages (welcome, deadline reminder, payment received).
- Analytics: monthly P&L trend chart, top vendors, tax paid over time.

## Next Actions
1. Present the MVP to user; gather feedback on chat playground UX and dashboard hierarchy.
2. If user green-lights Gupshup live integration → activate BSP account, approve templates.
3. Explore GSP shortlist (Masters India vs ClearTax vs KDK) for production filing.

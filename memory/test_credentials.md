# HisaabBot — Test Credentials

Auto-seeded on backend startup (`server.py :: startup()`).

## Demo Vendor (primary vendor test user)
- **Email:** `ramesh@hisaabbot.in`
- **Password:** `demo123`
- **Name:** Ramesh Sharma
- **Business:** Sharma Textiles, Jaipur
- **GSTIN:** `08AABCU9603R1ZM`
- **Phone:** +91 98765 43210
- **Role:** vendor
- **Language:** hi

Seeded data on first startup:
- 4 invoices in current month (2 purchases ₹68,320 total, 2 sales ₹52,080 total)
- 2 UPI transactions (₹33,600 + ₹18,480)

## Demo CA (Chartered Accountant)
- **Email:** `priya@hisaabbot.in`
- **Password:** `ca12345`
- **Name:** Priya Verma
- **Firm:** Verma & Associates, Delhi
- **Role:** ca

Auto-linked clients on first startup:
1. **Verma Traders** (Suresh Verma, Delhi · 07VERMA1234A1Z0) — GSTR-1 pending
2. **Kailash Kirana Store** (Kailash Chand, Jaipur · 08KAIL9988D1Z3) — GSTR-1 draft
3. **Bharat Kapda Mart** (Anil Bharat, Jaipur · 08BHRTK4567B1Z9) — GSTR-1 pending, ₹14,400 net payable
4. **Sharma Textiles** (Ramesh Sharma, existing vendor account) — GSTR-1 filed with ACK `AB12345678`

## Admin
- **Email:** `admin@hisaabbot.in`
- **Password:** `admin123`
- **Role:** admin

## Auth model
- JWT Bearer token (7-day access, 30-day refresh).
- Frontend stores access token in `localStorage.hb_token` and attaches via axios interceptor.
- Backend also sets HttpOnly cookies (`access_token`, `refresh_token`) as a same-origin fallback.
- Endpoint: `POST /api/auth/login` → returns `{user, access_token}`.
- Auth check: `GET /api/auth/me` with `Authorization: Bearer <token>`.

## Notes
- `EMERGENT_LLM_KEY` is already configured in `/app/backend/.env` — do NOT ask user for OpenAI keys.
- Gupshup + GSP (real GST filing) integrations are stubbed; live keys not required for MVP tests.
- CA endpoints are role-gated. A vendor calling `/api/ca/clients` gets 403.

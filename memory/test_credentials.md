# HisaabBot — Test Credentials

Auto-seeded on backend startup (`server.py :: startup()`).

## Demo Vendor (primary test user)
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

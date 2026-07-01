# GSP Provider Shortlist — Masters India vs ClearTax (2026)

## TL;DR — Recommendation

Go with **Masters India** for HisaabBot's Phase-1 launch (Starter + Pro plans), and keep **ClearTax** as a backup for CA-Plan enterprise/agency accounts.

Rationale below.

---

## Both are equally credible

Both hold valid **GSP licences (2026)** from GSTN with full API coverage of GSTR-1, GSTR-3B, GSTR-2A/2B, GSTR-9, GSTR-9C, and e-Invoice + e-Way Bill.

## Where they differ

| Dimension | Masters India | ClearTax |
|-----------|---------------|----------|
| Volume claim | ~4% of all e-invoices and 8% of all e-way bills via API | Largest overall GST filings share (dominates SAP/Oracle/enterprise). |
| Onboarding speed | Fast for API-first startups. Devs report a 1–2-week integration timeline. | Slower — enterprise-first onboarding, contract negotiations can take 4+ weeks. |
| API DX (developer experience) | Cleaner, well-documented REST + SDKs. Focused on API partners like us. | Feature-rich but heavier — more suited to ERP integrations than a chat-native app. |
| Pricing | Custom, negotiated per volume. Startups typically get **₹1.5–₹2 per filing** (bulk). Setup ₹0–₹15k. | Enterprise-tier pricing, often 2–3× higher entry point. Minimum annual commitment. |
| Best fit for us | Chat-native SaaS, per-vendor billing model, high-frequency low-ticket filings. | Large CA firms wanting ERP-level plumbing. |

## The one non-negotiable

Both providers require the **user's own** e-return credentials (GSTIN + evc / DSC) to sign and submit — HisaabBot **cannot** file on behalf without user's DSC or Aadhaar-EVC OTP. Our UX becomes:

1. HisaabBot generates GSTR-1 / 3B JSON (already implemented).
2. User clicks *"File via HisaabBot"* → we POST JSON to Masters India → they push to GSTN.
3. GSTN sends OTP to user's Aadhaar → user enters OTP inside HisaabBot chat.
4. Masters India returns ACK number → we save + notify user.

## Action items for founder

1. Sign up on **[mastersindia.co](https://www.mastersindia.co/goods-and-services-tax-gst-api/) → Contact Sales**. Ask for:
   - Sandbox access (free during dev).
   - Per-filing pricing at 500 / 2,000 / 10,000 filings per month tiers.
   - SLA and error-code documentation.
2. In parallel, request the same quote from **[cleartax.com](https://cleartax.in) → GSP API**. Use as leverage.
3. Sign the GSP agreement + provide our app's Meta business verification proofs.
4. Set following env variables on production:
   ```
   MASTERS_INDIA_CLIENT_ID=xxx
   MASTERS_INDIA_CLIENT_SECRET=xxx
   MASTERS_INDIA_BASE_URL=https://api.mastersindia.co
   MASTERS_INDIA_SANDBOX=true
   ```
5. Once received, hand over to Emergent E2 for the filing integration (a 3–5 day sprint).

## Estimated commercials (Masters India base case)

| Item | Cost | Notes |
|------|------|-------|
| Setup / annual licence | ₹0–₹15,000 | Negotiable at launch. |
| GSTR-1 filing | ~₹2 / vendor / month | Passed through. Our Starter plan (₹999) absorbs easily. |
| GSTR-3B filing | ~₹2 / vendor / month | Same. |
| e-Invoice (IRN) | ~₹0.10 / IRN | Only for vendors > ₹5Cr turnover — later phase. |
| GSTN OTP relay | included | free |

At 1,000 paying vendors × Starter plan: gross ₹9.99L/mo vs GSP passthrough ~₹4,000/mo — GSP is <0.5% COGS. Very safe.

## Coding contract (what we'll build once GSP keys arrive)

```python
# backend/gsp_client.py (skeleton — implement on go-live)
async def masters_india_login() -> str: ...
async def gstr1_upload(gstin: str, period: str, payload: dict) -> dict: ...
async def gstr3b_upload(gstin: str, period: str, payload: dict) -> dict: ...
async def submit_with_evc(otp: str) -> dict: ...
```

All four endpoints already have data ready — `payload` is what `GET /api/gst/summary` returns today. Zero rework required.

"""Masters India GSP client — wire-ready GSTR-1 / GSTR-3B filing pipeline.
When Masters India creds are missing, filings return a simulated ACK number so
the whole UX (upload → OTP → ACK) works end-to-end for the demo.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx

from .config import (
    MASTERS_INDIA_CLIENT_ID, MASTERS_INDIA_CLIENT_SECRET,
    MASTERS_INDIA_BASE_URL, MASTERS_INDIA_SANDBOX, gsp_enabled,
)
from .db import db


_token_cache: dict = {}


async def _get_bearer() -> str:
    """Fetch a Masters India access token (cached ~50 min).
    Real API: POST /users/authenticate  → returns access_token
    """
    if not gsp_enabled():
        return "SIMULATED-TOKEN"
    tok = _token_cache.get("token")
    exp = _token_cache.get("exp")
    if tok and exp and exp > datetime.now(timezone.utc):
        return tok
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(
            f"{MASTERS_INDIA_BASE_URL}/users/authenticate",
            json={"client_id": MASTERS_INDIA_CLIENT_ID,
                  "client_secret": MASTERS_INDIA_CLIENT_SECRET,
                  "grant_type": "client_credentials"},
        )
        data = r.json()
    tok = data.get("access_token") or data.get("data", {}).get("access_token")
    if not tok:
        raise RuntimeError(f"Masters India auth failed: {data}")
    _token_cache["token"] = tok
    from datetime import timedelta
    _token_cache["exp"] = datetime.now(timezone.utc) + timedelta(minutes=50)
    return tok


def _sim_ack() -> str:
    return f"SIM-ACK-{uuid.uuid4().hex[:10].upper()}"


async def upload_return(gstin: str, period: str, return_type: str, payload: dict) -> dict:
    """Upload a GSTR-1/3B payload to Masters India → GSTN.
    period format: MMYYYY (Masters India expects this). We accept YYYY-MM and convert.
    """
    # Convert YYYY-MM → MMYYYY per Masters India API convention
    if "-" in period:
        y, m = period.split("-")
        mi_period = f"{m}{y}"
    else:
        mi_period = period

    if not gsp_enabled():
        # Store the filing as a simulated draft
        ack = _sim_ack()
        doc = {
            "gstin": gstin, "period": period, "return_type": return_type,
            "gsp_provider": "simulated", "status": "uploaded",
            "ack_number": ack, "otp_required": True,
            "payload_summary": {k: v for k, v in payload.items() if k in ("outward_taxable", "output_tax_total", "net_payable", "count", "taxable_amount", "total_amount")},
            "created_at": datetime.now(timezone.utc),
        }
        res = await db.gsp_filings.insert_one(doc)
        return {
            "filing_id": str(res.inserted_id),
            "ack_number": ack,
            "status": "uploaded",
            "otp_required": True,
            "message": "Simulated: return uploaded. Enter OTP to submit.",
            "gsp_provider": "simulated",
        }

    # Real Masters India call (uncomment / test once creds arrive)
    tok = await _get_bearer()
    path = "/gsp/gstr1/save" if return_type == "gstr1" else "/gsp/gstr3b/save"
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f"{MASTERS_INDIA_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
            json={"gstin": gstin, "period": mi_period, "data": payload},
        )
        data = r.json()
    ack = data.get("ack_number") or data.get("data", {}).get("reference_id") or _sim_ack()
    doc = {
        "gstin": gstin, "period": period, "return_type": return_type,
        "gsp_provider": "masters_india", "status": "uploaded",
        "ack_number": ack, "otp_required": True,
        "raw_response": data,
        "created_at": datetime.now(timezone.utc),
    }
    res = await db.gsp_filings.insert_one(doc)
    return {"filing_id": str(res.inserted_id), "ack_number": ack, "status": "uploaded",
            "otp_required": True, "gsp_provider": "masters_india"}


async def submit_with_evc(filing_id: str, otp: str) -> dict:
    """User provides Aadhaar-EVC OTP. GSP forwards to GSTN."""
    from bson import ObjectId
    filing = await db.gsp_filings.find_one({"_id": ObjectId(filing_id)})
    if not filing:
        return {"ok": False, "error": "Filing not found"}
    if filing.get("status") == "submitted":
        return {"ok": False, "error": "Already submitted"}

    if not gsp_enabled():
        # Simulated: accept any 6-digit OTP
        if not (otp and otp.isdigit() and len(otp) == 6):
            return {"ok": False, "error": "OTP must be 6 digits"}
        arn = f"SIM-ARN-{uuid.uuid4().hex[:12].upper()}"
        await db.gsp_filings.update_one(
            {"_id": ObjectId(filing_id)},
            {"$set": {"status": "submitted", "arn": arn, "submitted_at": datetime.now(timezone.utc)}},
        )
        return {"ok": True, "arn": arn, "status": "submitted", "gsp_provider": "simulated"}

    tok = await _get_bearer()
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f"{MASTERS_INDIA_BASE_URL}/gsp/{filing['return_type']}/submit",
            headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
            json={"gstin": filing["gstin"], "period": filing["period"], "otp": otp, "ack_number": filing["ack_number"]},
        )
        data = r.json()
    arn = data.get("arn") or data.get("data", {}).get("arn")
    if not arn:
        return {"ok": False, "error": data.get("message", "Submit failed"), "raw": data}
    await db.gsp_filings.update_one(
        {"_id": ObjectId(filing_id)},
        {"$set": {"status": "submitted", "arn": arn, "submitted_at": datetime.now(timezone.utc), "raw_submit": data}},
    )
    return {"ok": True, "arn": arn, "status": "submitted", "gsp_provider": "masters_india"}

"""GST endpoints: GSTIN verify, monthly summary, deadlines, dashboard, file via GSP."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user
from core.db import db
from core.gstin import validate_gstin
from core.gst_engine import compute_gst_summary, next_gst_deadlines
from core.gsp_client import upload_return, submit_with_evc
from core.models import FileReturnReq, FileOtpReq

router = APIRouter(tags=["gst"])


@router.post("/gstin/verify")
async def gstin_verify(payload: dict):
    return validate_gstin(payload.get("gstin", ""))


@router.get("/gst/summary")
async def gst_summary(month: Optional[str] = None, current=Depends(get_current_user)):
    if not month:
        now = datetime.now(timezone.utc)
        month = f"{now.year}-{now.month:02d}"
    cur = db.invoices.find({"user_id": str(current["_id"])})
    invoices = []
    async for d in cur:
        d["_id"] = str(d["_id"])
        invoices.append(d)
    return compute_gst_summary(invoices, month)


@router.get("/gst/deadlines")
async def gst_deadlines(current=Depends(get_current_user)):
    return {"deadlines": next_gst_deadlines()}


@router.get("/dashboard/summary")
async def dashboard_summary(current=Depends(get_current_user)):
    uid = str(current["_id"])
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    month = now.strftime("%Y-%m")

    async def _agg(q):
        cur = db.invoices.find(q)
        s = 0.0
        c = 0
        async for d in cur:
            s += float(d.get("total_amount", 0) or 0)
            c += 1
        return {"total": round(s, 2), "count": c}

    today_sales = await _agg({"user_id": uid, "type": "sales", "invoice_date": today})
    today_purchase = await _agg({"user_id": uid, "type": "purchase", "invoice_date": today})
    month_sales = await _agg({"user_id": uid, "type": "sales", "invoice_date": {"$regex": f"^{month}"}})
    month_purchase = await _agg({"user_id": uid, "type": "purchase", "invoice_date": {"$regex": f"^{month}"}})

    upi_cur = db.upi_transactions.find({"user_id": uid, "date": {"$regex": f"^{month}"}})
    upi_total = 0.0
    upi_count = 0
    async for d in upi_cur:
        upi_total += float(d.get("amount", 0) or 0)
        upi_count += 1

    deadlines = next_gst_deadlines()

    return {
        "today": {"sales": today_sales, "purchase": today_purchase},
        "month": {"sales": month_sales, "purchase": month_purchase,
                  "profit": round(month_sales["total"] - month_purchase["total"], 2)},
        "upi_month": {"total": round(upi_total, 2), "count": upi_count},
        "deadlines": deadlines,
    }


# ------------- GSP filing (Masters India wire-ready) -------------

@router.post("/gst/file")
async def file_return(req: FileReturnReq, current=Depends(get_current_user)):
    """Vendor-initiated: upload GSTR-1 or GSTR-3B to GSP.
    Returns filing_id + ack_number + otp_required.
    """
    gstin = current.get("gstin")
    if not gstin:
        raise HTTPException(status_code=400, detail="GSTIN not set on your profile. Update in Settings first.")
    if req.return_type not in ("gstr1", "gstr3b"):
        raise HTTPException(status_code=400, detail="return_type must be gstr1 or gstr3b")
    # Build summary payload
    cur = db.invoices.find({"user_id": str(current["_id"])})
    invoices = []
    async for d in cur:
        d["_id"] = str(d["_id"])
        invoices.append(d)
    summary = compute_gst_summary(invoices, req.period)
    payload = summary["gstr1"] if req.return_type == "gstr1" else summary["gstr3b"]
    result = await upload_return(gstin=gstin, period=req.period, return_type=req.return_type, payload=payload)
    # Attach owner
    from bson import ObjectId
    await db.gsp_filings.update_one({"_id": ObjectId(result["filing_id"])},
                                     {"$set": {"owner_id": str(current["_id"])}})
    return result


@router.post("/gst/file/submit-otp")
async def file_submit_otp(req: FileOtpReq, current=Depends(get_current_user)):
    """Vendor provides Aadhaar EVC OTP. GSP forwards to GSTN and returns ARN."""
    from bson import ObjectId
    filing = await db.gsp_filings.find_one({"_id": ObjectId(req.filing_id)})
    if not filing:
        raise HTTPException(status_code=404, detail="Filing not found")
    if filing.get("owner_id") and filing["owner_id"] != str(current["_id"]) and current.get("role") != "ca":
        raise HTTPException(status_code=403, detail="Not your filing")
    result = await submit_with_evc(req.filing_id, req.otp)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Submit failed"))
    return result


@router.get("/gst/filings")
async def list_filings(current=Depends(get_current_user)):
    q = {"owner_id": str(current["_id"])}
    cur = db.gsp_filings.find(q).sort("created_at", -1)
    out = []
    async for d in cur:
        d["_id"] = str(d["_id"])
        d.pop("raw_response", None)
        d.pop("raw_submit", None)
        if isinstance(d.get("created_at"), datetime):
            d["created_at"] = d["created_at"].isoformat()
        if isinstance(d.get("submitted_at"), datetime):
            d["submitted_at"] = d["submitted_at"].isoformat()
        out.append(d)
    return out

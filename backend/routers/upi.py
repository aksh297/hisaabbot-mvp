"""UPI reconciliation endpoints."""
import base64
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from core.auth import get_current_user
from core.config import UPLOAD_DIR
from core.db import db
from core.llm import UPI_SYSTEM_PROMPT, llm_extract
from core.models import UpiTxnIn

router = APIRouter(prefix="/upi", tags=["upi"])


def _save(file: UploadFile) -> tuple[str, str]:
    ext = Path(file.filename or "").suffix or ".jpg"
    fname = f"upi-{uuid.uuid4().hex}{ext}"
    fpath = UPLOAD_DIR / fname
    return fname, str(fpath)


@router.post("/parse")
async def upi_parse(file: UploadFile = File(...), current=Depends(get_current_user)):
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large")
    fname, fpath = _save(file)
    with open(fpath, "wb") as f:
        f.write(data)
    b64 = base64.b64encode(data).decode("utf-8")
    parsed = await llm_extract(UPI_SYSTEM_PROMPT, "Extract UPI payment details from this screenshot.", image_b64=b64)
    parsed["image_url"] = f"/api/uploads/{fname}"
    if isinstance(parsed.get("amount"), (int, float)) and parsed.get("date"):
        try:
            dt = datetime.strptime(parsed["date"], "%Y-%m-%d")
            lower = (dt - timedelta(days=3)).strftime("%Y-%m-%d")
            upper = (dt + timedelta(days=3)).strftime("%Y-%m-%d")
            amt = float(parsed["amount"])
            match = await db.invoices.find_one({
                "user_id": str(current["_id"]),
                "type": "sales",
                "total_amount": {"$gte": amt - 1, "$lte": amt + 1},
                "invoice_date": {"$gte": lower, "$lte": upper},
            })
            if match:
                parsed["suggested_match"] = {
                    "invoice_id": str(match["_id"]),
                    "counterparty_name": match.get("counterparty_name"),
                    "invoice_number": match.get("invoice_number"),
                    "invoice_date": match.get("invoice_date"),
                    "total_amount": match.get("total_amount"),
                }
        except Exception:
            pass
    return parsed


@router.post("/transactions")
async def create_upi_txn(txn: UpiTxnIn, current=Depends(get_current_user)):
    doc = txn.model_dump()
    doc["user_id"] = str(current["_id"])
    doc["created_at"] = datetime.now(timezone.utc)
    res = await db.upi_transactions.insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    return doc


@router.get("/transactions")
async def list_upi_txns(current=Depends(get_current_user)):
    q = {"user_id": str(current["_id"])}
    cur = db.upi_transactions.find(q).sort("date", -1)
    out = []
    async for d in cur:
        d["_id"] = str(d["_id"])
        out.append(d)
    return out

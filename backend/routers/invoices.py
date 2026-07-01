"""Invoice endpoints: OCR upload, CRUD."""
import base64
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from core.auth import get_current_user
from core.config import UPLOAD_DIR
from core.db import db
from core.llm import OCR_SYSTEM_PROMPT, llm_extract
from core.models import InvoiceIn

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _save_upload(file: UploadFile, prefix: str) -> tuple[str, str]:
    ext = Path(file.filename or "").suffix or ".bin"
    fname = f"{prefix}-{uuid.uuid4().hex}{ext}"
    fpath = UPLOAD_DIR / fname
    return fname, str(fpath)


@router.post("/ocr")
async def invoice_ocr(file: UploadFile = File(...), current=Depends(get_current_user)):
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    fname, fpath = _save_upload(file, "invoice")
    with open(fpath, "wb") as f:
        f.write(data)
    b64 = base64.b64encode(data).decode("utf-8")
    parsed = await llm_extract(
        OCR_SYSTEM_PROMPT,
        "Extract invoice fields from this image. Return only JSON.",
        image_b64=b64,
    )
    parsed["image_url"] = f"/api/uploads/{fname}"
    return parsed


@router.post("")
async def create_invoice(inv: InvoiceIn, current=Depends(get_current_user)):
    if inv.type not in ("purchase", "sales"):
        raise HTTPException(status_code=400, detail="type must be purchase or sales")
    doc = inv.model_dump()
    doc["user_id"] = str(current["_id"])
    doc["created_at"] = datetime.now(timezone.utc)
    doc["counterparty_gstin"] = (doc.get("counterparty_gstin") or "").upper() or None
    res = await db.invoices.insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    return doc


@router.get("")
async def list_invoices(type: Optional[str] = None, month: Optional[str] = None,
                         current=Depends(get_current_user)):
    q: dict = {"user_id": str(current["_id"])}
    if type:
        q["type"] = type
    if month:
        q["invoice_date"] = {"$regex": f"^{re.escape(month)}"}
    cursor = db.invoices.find(q).sort("invoice_date", -1)
    out = []
    async for d in cursor:
        d["_id"] = str(d["_id"])
        out.append(d)
    return out


@router.delete("/{inv_id}")
async def delete_invoice(inv_id: str, current=Depends(get_current_user)):
    res = await db.invoices.delete_one({"_id": ObjectId(inv_id), "user_id": str(current["_id"])})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"ok": True}

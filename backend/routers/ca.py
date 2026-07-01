"""CA Plan bulk client dashboard router — includes CSV/JSON export."""
import csv
import io
import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from core.auth import get_current_user, ensure_ca, hash_password
from core.db import db
from core.gst_engine import compute_gst_summary
from core.gstin import validate_gstin
from core.models import InviteClientReq, MarkFiledReq

router = APIRouter(prefix="/ca", tags=["ca"])


async def _client_status_row(ca_id: str, vendor: dict, month: str) -> dict:
    vid = str(vendor["_id"])
    cur = db.invoices.find({"user_id": vid, "invoice_date": {"$regex": f"^{re.escape(month)}"}})
    invoices = []
    async for d in cur:
        d["_id"] = str(d["_id"])
        invoices.append(d)
    summary = compute_gst_summary(invoices, month)

    filing = await db.filings.find_one({"ca_id": ca_id, "vendor_id": vid, "period": month})
    gstr1_status = (filing or {}).get("gstr1_status", "pending")
    gstr3b_status = (filing or {}).get("gstr3b_status", "pending")

    total_sales = sum(1 for i in invoices if i.get("type") == "sales")
    total_purchase = sum(1 for i in invoices if i.get("type") == "purchase")

    return {
        "vendor_id": vid,
        "name": vendor.get("name"),
        "business_name": vendor.get("business_name"),
        "gstin": vendor.get("gstin"),
        "city": vendor.get("city"),
        "phone": vendor.get("phone"),
        "email": vendor.get("email"),
        "status": vendor.get("client_status", "active"),
        "sales_total": summary["gstr1"]["total_amount"],
        "purchase_total": summary["gstr3b"]["inward_taxable"] + summary["gstr3b"]["itc_total"],
        "output_tax": summary["gstr3b"]["output_tax_total"],
        "itc_total": summary["gstr3b"]["itc_total"],
        "net_payable": summary["gstr3b"]["net_payable"],
        "sales_count": total_sales,
        "purchase_count": total_purchase,
        "gstr1_status": gstr1_status,
        "gstr3b_status": gstr3b_status,
        "period": month,
    }


def _ca_stats(rows: List[dict]) -> dict:
    total = len(rows)
    filed_1 = sum(1 for r in rows if r["gstr1_status"] == "filed")
    filed_3b = sum(1 for r in rows if r["gstr3b_status"] == "filed")
    pending = total - min(filed_1, filed_3b)
    return {
        "total_clients": total,
        "gstr1_filed": filed_1,
        "gstr3b_filed": filed_3b,
        "pending": pending,
        "combined_output_tax": round(sum(r.get("output_tax", 0) or 0 for r in rows), 2),
        "combined_itc": round(sum(r.get("itc_total", 0) or 0 for r in rows), 2),
        "combined_net_payable": round(sum(r.get("net_payable", 0) or 0 for r in rows), 2),
        "combined_sales": round(sum(r.get("sales_total", 0) or 0 for r in rows), 2),
    }


async def _collect_rows(ca_id: str, month: str) -> List[dict]:
    links = db.client_links.find({"ca_id": ca_id})
    vendor_ids: List[str] = []
    async for link in links:
        vendor_ids.append(link["vendor_id"])
    if not vendor_ids:
        return []
    cursor = db.users.find({"_id": {"$in": [ObjectId(v) for v in vendor_ids]}})
    rows: List[dict] = []
    async for v in cursor:
        rows.append(await _client_status_row(ca_id, v, month))
    rows.sort(key=lambda r: (0 if r["gstr1_status"] == "pending" else 1, -(r["net_payable"] or 0)))
    return rows


@router.get("/clients")
async def ca_list_clients(month: Optional[str] = None, current=Depends(get_current_user)):
    ensure_ca(current)
    if not month:
        now = datetime.now(timezone.utc)
        month = f"{now.year}-{now.month:02d}"
    rows = await _collect_rows(str(current["_id"]), month)
    return {"period": month, "clients": rows, "stats": _ca_stats(rows)}


@router.post("/clients/invite")
async def ca_invite_client(req: InviteClientReq, current=Depends(get_current_user)):
    ensure_ca(current)
    if not req.email and not req.phone:
        raise HTTPException(status_code=400, detail="email or phone required")
    if req.gstin:
        v = validate_gstin(req.gstin)
        if not v["valid"]:
            raise HTTPException(status_code=400, detail=v.get("error", "Invalid GSTIN"))
    q: dict = {}
    if req.email:
        q["email"] = req.email.strip().lower()
    vendor = await db.users.find_one(q) if q else None
    if not vendor:
        vendor_doc = {
            "email": (req.email or f"invited-{uuid.uuid4().hex[:8]}@hisaabbot.in").lower(),
            "password_hash": hash_password(uuid.uuid4().hex),
            "name": req.name,
            "role": "vendor",
            "business_name": req.business_name,
            "gstin": req.gstin.upper() if req.gstin else None,
            "city": req.city,
            "phone": req.phone,
            "language": "hi",
            "client_status": "invited",
            "created_at": datetime.now(timezone.utc),
        }
        res = await db.users.insert_one(vendor_doc)
        vendor = {**vendor_doc, "_id": res.inserted_id}
    ca_id = str(current["_id"])
    vid = str(vendor["_id"])
    existing = await db.client_links.find_one({"ca_id": ca_id, "vendor_id": vid})
    if existing:
        raise HTTPException(status_code=400, detail="Already your client")
    await db.client_links.insert_one({
        "ca_id": ca_id, "vendor_id": vid, "created_at": datetime.now(timezone.utc),
    })
    return {"ok": True, "vendor_id": vid, "email": vendor.get("email")}


@router.delete("/clients/{vendor_id}")
async def ca_remove_client(vendor_id: str, current=Depends(get_current_user)):
    ensure_ca(current)
    ca_id = str(current["_id"])
    res = await db.client_links.delete_one({"ca_id": ca_id, "vendor_id": vendor_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client link not found")
    return {"ok": True}


@router.post("/filings/mark")
async def ca_mark_filed(req: MarkFiledReq, current=Depends(get_current_user)):
    ensure_ca(current)
    ca_id = str(current["_id"])
    link = await db.client_links.find_one({"ca_id": ca_id, "vendor_id": req.vendor_id})
    if not link:
        raise HTTPException(status_code=403, detail="Not your client")
    if req.return_type not in ("gstr1", "gstr3b"):
        raise HTTPException(status_code=400, detail="return_type must be gstr1 or gstr3b")
    field = f"{req.return_type}_status"
    update = {"$set": {field: req.status,
                        f"{req.return_type}_ack": req.ack_number,
                        f"{req.return_type}_at": datetime.now(timezone.utc)}}
    await db.filings.update_one(
        {"ca_id": ca_id, "vendor_id": req.vendor_id, "period": req.period},
        update, upsert=True,
    )
    return {"ok": True}


@router.get("/clients/{vendor_id}/summary")
async def ca_client_summary(vendor_id: str, month: Optional[str] = None, current=Depends(get_current_user)):
    ensure_ca(current)
    ca_id = str(current["_id"])
    link = await db.client_links.find_one({"ca_id": ca_id, "vendor_id": vendor_id})
    if not link:
        raise HTTPException(status_code=403, detail="Not your client")
    vendor = await db.users.find_one({"_id": ObjectId(vendor_id)})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    if not month:
        now = datetime.now(timezone.utc)
        month = f"{now.year}-{now.month:02d}"
    cur = db.invoices.find({"user_id": vendor_id, "invoice_date": {"$regex": f"^{re.escape(month)}"}})
    invoices = []
    async for d in cur:
        d["_id"] = str(d["_id"])
        invoices.append(d)
    summary = compute_gst_summary(invoices, month)
    row = await _client_status_row(ca_id, vendor, month)
    return {"vendor": row, "gstr1": summary["gstr1"], "gstr3b": summary["gstr3b"], "invoices": invoices}


# ------------- Export (CSV / JSON) -------------
EXPORT_COLUMNS = [
    ("business_name", "Business"),
    ("name", "Contact name"),
    ("gstin", "GSTIN"),
    ("city", "City"),
    ("phone", "Phone"),
    ("email", "Email"),
    ("sales_count", "Sales count"),
    ("sales_total", "Sales total (INR)"),
    ("purchase_count", "Purchase count"),
    ("purchase_total", "Purchase total (INR)"),
    ("output_tax", "Output tax (INR)"),
    ("itc_total", "ITC (INR)"),
    ("net_payable", "Net GST payable (INR)"),
    ("gstr1_status", "GSTR-1 status"),
    ("gstr3b_status", "GSTR-3B status"),
]


@router.get("/export")
async def ca_export(month: Optional[str] = None, format: str = Query("csv", pattern="^(csv|json)$"),
                     current=Depends(get_current_user)):
    ensure_ca(current)
    if not month:
        now = datetime.now(timezone.utc)
        month = f"{now.year}-{now.month:02d}"
    rows = await _collect_rows(str(current["_id"]), month)

    if format == "json":
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "ca_email": current.get("email"),
            "ca_business": current.get("business_name"),
            "period": month,
            "stats": _ca_stats(rows),
            "clients": rows,
        }
        return payload

    # CSV
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["HisaabBot CA Export"])
    writer.writerow(["Generated", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")])
    writer.writerow(["CA", current.get("business_name") or current.get("name"), current.get("email")])
    writer.writerow(["Period", month])
    stats = _ca_stats(rows)
    writer.writerow([])
    writer.writerow(["Summary"])
    writer.writerow(["Total clients", stats["total_clients"]])
    writer.writerow(["GSTR-1 filed", stats["gstr1_filed"]])
    writer.writerow(["GSTR-3B filed", stats["gstr3b_filed"]])
    writer.writerow(["Combined sales (INR)", stats["combined_sales"]])
    writer.writerow(["Combined output tax (INR)", stats["combined_output_tax"]])
    writer.writerow(["Combined ITC (INR)", stats["combined_itc"]])
    writer.writerow(["Combined net payable (INR)", stats["combined_net_payable"]])
    writer.writerow([])
    writer.writerow([label for _, label in EXPORT_COLUMNS])
    for r in rows:
        writer.writerow([r.get(k, "") for k, _ in EXPORT_COLUMNS])
    buf.seek(0)
    filename = f"hisaabbot-ca-export-{month}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

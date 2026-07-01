"""Startup seeding — admin, demo vendor, CA, sample data.
Extracted from the monolithic startup() for readability.
"""
import uuid
from datetime import datetime, timezone

from .auth import hash_password, verify_password
from .config import ADMIN_EMAIL, ADMIN_PASSWORD, DEMO_EMAIL, DEMO_PASSWORD
from .db import db


async def seed_admin():
    admin = await db.users.find_one({"email": ADMIN_EMAIL})
    if not admin:
        await db.users.insert_one({
            "email": ADMIN_EMAIL,
            "password_hash": hash_password(ADMIN_PASSWORD),
            "name": "Admin",
            "role": "admin",
            "language": "en",
            "created_at": datetime.now(timezone.utc),
        })
    else:
        if not verify_password(ADMIN_PASSWORD, admin["password_hash"]):
            await db.users.update_one({"email": ADMIN_EMAIL},
                                       {"$set": {"password_hash": hash_password(ADMIN_PASSWORD)}})


async def seed_demo_vendor():
    demo = await db.users.find_one({"email": DEMO_EMAIL})
    if demo:
        return
    res = await db.users.insert_one({
        "email": DEMO_EMAIL,
        "password_hash": hash_password(DEMO_PASSWORD),
        "name": "Ramesh Sharma",
        "role": "vendor",
        "business_name": "Sharma Textiles",
        "gstin": "08AABCU9603R1ZM",
        "city": "Jaipur",
        "phone": "+919876543210",
        "language": "hi",
        "created_at": datetime.now(timezone.utc),
    })
    uid = str(res.inserted_id)
    now = datetime.now(timezone.utc)
    this_month = now.strftime("%Y-%m")
    sample_invoices = [
        {"user_id": uid, "type": "purchase", "counterparty_name": "Kailash Textiles",
         "counterparty_gstin": "08AAACK1234A1Z5", "invoice_number": "KT-0421",
         "invoice_date": f"{this_month}-05", "hsn_code": "5208",
         "line_items": [{"description": "Cotton fabric bales", "hsn": "5208", "qty": 10, "rate": 4500, "amount": 45000, "tax_rate": 12}],
         "taxable_amount": 45000, "cgst": 2700, "sgst": 2700, "igst": 0,
         "total_tax": 5400, "total_amount": 50400, "created_at": now},
        {"user_id": uid, "type": "sales", "counterparty_name": "Bharat Kapda Mart",
         "counterparty_gstin": "08BHRTK4567B1Z9", "invoice_number": "ST-0119",
         "invoice_date": f"{this_month}-07", "hsn_code": "5208",
         "line_items": [{"description": "Cotton fabric retail", "hsn": "5208", "qty": 5, "rate": 6000, "amount": 30000, "tax_rate": 12}],
         "taxable_amount": 30000, "cgst": 1800, "sgst": 1800, "igst": 0,
         "total_tax": 3600, "total_amount": 33600, "created_at": now},
        {"user_id": uid, "type": "sales", "counterparty_name": "Retail Cash Sale",
         "counterparty_gstin": None, "invoice_number": "ST-0120",
         "invoice_date": f"{this_month}-08", "hsn_code": "5208",
         "line_items": [{"description": "Fabric", "hsn": "5208", "qty": 3, "rate": 5500, "amount": 16500, "tax_rate": 12}],
         "taxable_amount": 16500, "cgst": 990, "sgst": 990, "igst": 0,
         "total_tax": 1980, "total_amount": 18480, "created_at": now},
        {"user_id": uid, "type": "purchase", "counterparty_name": "Delhi Yarn Suppliers",
         "counterparty_gstin": "07DELHY6789C1Z3", "invoice_number": "DY-2201",
         "invoice_date": f"{this_month}-03", "hsn_code": "5205",
         "line_items": [{"description": "Yarn bundles (inter-state)", "hsn": "5205", "qty": 20, "rate": 800, "amount": 16000, "tax_rate": 12}],
         "taxable_amount": 16000, "cgst": 0, "sgst": 0, "igst": 1920,
         "total_tax": 1920, "total_amount": 17920, "created_at": now},
    ]
    await db.invoices.insert_many(sample_invoices)
    await db.upi_transactions.insert_many([
        {"user_id": uid, "payer_name": "Bharat Kapda Mart", "upi_id": "bharatkapda@okhdfcbank",
         "amount": 33600, "date": f"{this_month}-07", "ref_number": "UPI2024050712345",
         "matched_invoice_id": None, "created_at": now},
        {"user_id": uid, "payer_name": "Cash Customer", "upi_id": "customer@paytm",
         "amount": 18480, "date": f"{this_month}-08", "ref_number": "UPI2024050898765",
         "matched_invoice_id": None, "created_at": now},
    ])


async def seed_ca_with_clients():
    ca_email = "priya@hisaabbot.in"
    ca = await db.users.find_one({"email": ca_email})
    if ca:
        return
    res = await db.users.insert_one({
        "email": ca_email,
        "password_hash": hash_password("ca12345"),
        "name": "Priya Verma",
        "role": "ca",
        "business_name": "Verma & Associates",
        "phone": "+919812345678",
        "city": "Delhi",
        "language": "en",
        "created_at": datetime.now(timezone.utc),
    })
    ca_id = str(res.inserted_id)
    now = datetime.now(timezone.utc)
    this_month = now.strftime("%Y-%m")

    clients_data = [
        {"email": "verma_traders@hisaabbot.in",
         "name": "Suresh Verma", "business_name": "Verma Traders",
         "gstin": "07VERMA1234A1Z0", "city": "Delhi", "phone": "+919811111111",
         "invoices": [
             {"type": "sales", "counterparty_name": "Anand Enterprises", "counterparty_gstin": "07ANAND5678B2Z1",
              "invoice_number": "VT-101", "invoice_date": f"{this_month}-04", "hsn_code": "8517",
              "taxable_amount": 80000, "cgst": 7200, "sgst": 7200, "igst": 0, "total_tax": 14400, "total_amount": 94400},
             {"type": "purchase", "counterparty_name": "Delhi Electronics", "counterparty_gstin": "07DELEL2233C1Z8",
              "invoice_number": "DE-2201", "invoice_date": f"{this_month}-02", "hsn_code": "8517",
              "taxable_amount": 50000, "cgst": 4500, "sgst": 4500, "igst": 0, "total_tax": 9000, "total_amount": 59000},
         ], "gstr1_status": "pending", "gstr3b_status": "pending"},
        {"email": "kailash_kirana@hisaabbot.in",
         "name": "Kailash Chand", "business_name": "Kailash Kirana Store",
         "gstin": "08KAIL9988D1Z3", "city": "Jaipur", "phone": "+919822222222",
         "invoices": [
             {"type": "sales", "counterparty_name": "Retail Cash", "counterparty_gstin": None,
              "invoice_number": "KK-501", "invoice_date": f"{this_month}-06", "hsn_code": "0910",
              "taxable_amount": 12000, "cgst": 720, "sgst": 720, "igst": 0, "total_tax": 1440, "total_amount": 13440},
             {"type": "sales", "counterparty_name": "Retail Cash", "counterparty_gstin": None,
              "invoice_number": "KK-502", "invoice_date": f"{this_month}-09", "hsn_code": "0910",
              "taxable_amount": 8500, "cgst": 510, "sgst": 510, "igst": 0, "total_tax": 1020, "total_amount": 9520},
             {"type": "purchase", "counterparty_name": "Wholesale Spices Co", "counterparty_gstin": "08WHOLE7788E1Z4",
              "invoice_number": "WS-990", "invoice_date": f"{this_month}-01", "hsn_code": "0910",
              "taxable_amount": 25000, "cgst": 1500, "sgst": 1500, "igst": 0, "total_tax": 3000, "total_amount": 28000},
         ], "gstr1_status": "draft", "gstr3b_status": "pending"},
        {"email": "bharat_kapda@hisaabbot.in",
         "name": "Anil Bharat", "business_name": "Bharat Kapda Mart",
         "gstin": "08BHRTK4567B1Z9", "city": "Jaipur", "phone": "+919833333333",
         "invoices": [
             {"type": "sales", "counterparty_name": "Fashion Hub", "counterparty_gstin": "08FASHN1122F3Z6",
              "invoice_number": "BK-701", "invoice_date": f"{this_month}-03", "hsn_code": "6109",
              "taxable_amount": 150000, "cgst": 9000, "sgst": 9000, "igst": 0, "total_tax": 18000, "total_amount": 168000},
             {"type": "purchase", "counterparty_name": "Sharma Textiles", "counterparty_gstin": "08AABCU9603R1ZM",
              "invoice_number": "ST-0119", "invoice_date": f"{this_month}-07", "hsn_code": "5208",
              "taxable_amount": 30000, "cgst": 1800, "sgst": 1800, "igst": 0, "total_tax": 3600, "total_amount": 33600},
         ], "gstr1_status": "pending", "gstr3b_status": "pending"},
        {"name": "Ramesh Sharma (existing)", "business_name": "Sharma Textiles",
         "gstin": "08AABCU9603R1ZM", "city": "Jaipur", "phone": "+919876543210",
         "invoices": [], "link_existing": DEMO_EMAIL,
         "gstr1_status": "filed", "gstr3b_status": "pending", "ack_number": "AB12345678"},
    ]

    for cdata in clients_data:
        existing_email = cdata.get("link_existing")
        vendor = None
        if existing_email:
            vendor = await db.users.find_one({"email": existing_email})
        if not vendor:
            vdoc = {
                "email": cdata["email"],
                "password_hash": hash_password(uuid.uuid4().hex),
                "name": cdata["name"],
                "role": "vendor",
                "business_name": cdata["business_name"],
                "gstin": cdata["gstin"],
                "city": cdata["city"],
                "phone": cdata["phone"],
                "language": "hi",
                "client_status": "active",
                "created_at": now,
            }
            r = await db.users.insert_one(vdoc)
            vendor_id = str(r.inserted_id)
            for inv in cdata.get("invoices", []):
                await db.invoices.insert_one({**inv, "user_id": vendor_id, "line_items": [], "created_at": now})
        else:
            vendor_id = str(vendor["_id"])
        try:
            await db.client_links.insert_one({
                "ca_id": ca_id, "vendor_id": vendor_id, "created_at": now,
            })
        except Exception:
            pass
        filing_doc = {
            "ca_id": ca_id, "vendor_id": vendor_id, "period": this_month,
            "gstr1_status": cdata.get("gstr1_status", "pending"),
            "gstr3b_status": cdata.get("gstr3b_status", "pending"),
        }
        if cdata.get("ack_number"):
            filing_doc["gstr1_ack"] = cdata["ack_number"]
        await db.filings.update_one(
            {"ca_id": ca_id, "vendor_id": vendor_id, "period": this_month},
            {"$set": filing_doc}, upsert=True,
        )


async def run_all():
    await seed_admin()
    await seed_demo_vendor()
    await seed_ca_with_clients()

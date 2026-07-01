"""HisaabBot backend regression tests."""
import os
import time
import base64
import io
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://043b526b-3b05-4aa7-a1d6-eee4303da566.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

DEMO_EMAIL = "ramesh@hisaabbot.in"
DEMO_PASSWORD = "demo123"


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def token(session):
    r = session.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert r.status_code == 200, r.text
    tok = r.json().get("access_token")
    assert tok
    return tok


@pytest.fixture(scope="session")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------- Health ----------
def test_root():
    r = requests.get(f"{API}/")
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_health():
    r = requests.get(f"{API}/health")
    assert r.status_code == 200
    assert r.json().get("status") == "healthy"


# ---------- Auth ----------
def test_login_demo(session):
    r = session.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["user"]["email"] == DEMO_EMAIL
    assert data["user"]["business_name"] == "Sharma Textiles"
    assert data["user"]["gstin"] == "08AABCU9603R1ZM"


def test_login_bad_password(session):
    r = session.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": "wrong"})
    assert r.status_code == 401


def test_register_and_me(session):
    email = f"test-{int(time.time()*1000)}@hisaabbot.in"
    r = session.post(f"{API}/auth/register", json={
        "email": email, "password": "pass1234", "name": "Test User",
        "business_name": "T Traders", "language": "en"
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data
    assert data["user"]["email"] == email
    tok = data["access_token"]
    me = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert me.status_code == 200
    assert me.json()["email"] == email


def test_me_no_token():
    r = requests.get(f"{API}/auth/me")
    assert r.status_code == 401


# ---------- GSTIN ----------
def test_gstin_valid():
    r = requests.post(f"{API}/gstin/verify", json={"gstin": "08AABCU9603R1ZM"})
    assert r.status_code == 200
    d = r.json()
    assert d["valid"] is True
    assert d["state"] == "Rajasthan"
    assert d["state_code"] == "08"
    assert d["pan"] == "AABCU9603R"


def test_gstin_invalid():
    r = requests.post(f"{API}/gstin/verify", json={"gstin": "INVALID"})
    assert r.status_code == 200
    d = r.json()
    assert d["valid"] is False
    assert "error" in d


# ---------- Invoices ----------
def test_invoice_crud(auth_headers):
    from datetime import datetime
    today = datetime.utcnow().strftime("%Y-%m-%d")
    payload = {
        "type": "purchase", "counterparty_name": "TEST Vendor",
        "counterparty_gstin": "08AABCU9603R1ZM", "invoice_number": "T-001",
        "invoice_date": today, "taxable_amount": 1000, "cgst": 90, "sgst": 90,
        "igst": 0, "total_tax": 180, "total_amount": 1180
    }
    r = requests.post(f"{API}/invoices", json=payload, headers=auth_headers)
    assert r.status_code == 200, r.text
    inv = r.json()
    inv_id = inv["_id"]
    assert inv["counterparty_name"] == "TEST Vendor"
    assert inv["total_amount"] == 1180

    # list
    r = requests.get(f"{API}/invoices", headers=auth_headers)
    assert r.status_code == 200
    ids = [x["_id"] for x in r.json()]
    assert inv_id in ids

    # filter
    r = requests.get(f"{API}/invoices?type=purchase", headers=auth_headers)
    assert r.status_code == 200
    assert all(x["type"] == "purchase" for x in r.json())

    # delete
    r = requests.delete(f"{API}/invoices/{inv_id}", headers=auth_headers)
    assert r.status_code == 200
    r = requests.get(f"{API}/invoices", headers=auth_headers)
    assert inv_id not in [x["_id"] for x in r.json()]


# ---------- Dashboard ----------
def test_dashboard_summary(auth_headers):
    r = requests.get(f"{API}/dashboard/summary", headers=auth_headers)
    assert r.status_code == 200
    d = r.json()
    assert "today" in d and "month" in d and "upi_month" in d and "deadlines" in d
    # seeded month totals: sales 33600+18480=52080; purchase 50400+17920=68320
    assert d["month"]["sales"]["total"] == 52080.0
    assert d["month"]["purchase"]["total"] == 68320.0
    types = {x["return_type"] for x in d["deadlines"]}
    assert {"GSTR-1", "GSTR-3B"}.issubset(types)


# ---------- GST summary ----------
def test_gst_summary(auth_headers):
    from datetime import datetime
    month = datetime.utcnow().strftime("%Y-%m")
    r = requests.get(f"{API}/gst/summary?month={month}", headers=auth_headers)
    assert r.status_code == 200
    d = r.json()
    assert "gstr1" in d and "gstr3b" in d
    g1 = d["gstr1"]
    g3 = d["gstr3b"]
    # sales invoices seed: 33600 + 18480 = 52080
    assert g1["total_amount"] == 52080.0
    assert len(g1["invoices"]) >= 2
    # output tax = 3600 + 1980 = 5580; itc = 5400 + 1920 = 7320; net_payable = 0
    assert g3["output_tax_total"] == 5580.0
    assert g3["itc_total"] == 7320.0
    assert g3["net_payable"] == 0.0


# ---------- UPI ----------
def test_upi_list_and_create(auth_headers):
    r = requests.get(f"{API}/upi/transactions", headers=auth_headers)
    assert r.status_code == 200
    initial = len(r.json())
    assert initial >= 2

    from datetime import datetime
    today = datetime.utcnow().strftime("%Y-%m-%d")
    r = requests.post(f"{API}/upi/transactions", json={
        "payer_name": "TEST Payer", "upi_id": "test@upi",
        "amount": 500, "date": today, "ref_number": "TEST-REF"
    }, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["amount"] == 500

    r2 = requests.get(f"{API}/upi/transactions", headers=auth_headers)
    assert len(r2.json()) == initial + 1


# ---------- Chat ----------
def test_chat_and_history(auth_headers):
    sess = f"pytest-{int(time.time())}"
    r = requests.post(f"{API}/chat/message", json={
        "session_id": sess, "message": "Namaste, aaj ki bikri batao"
    }, headers=auth_headers, timeout=60)
    assert r.status_code == 200, r.text
    reply = r.json()["reply"]
    assert isinstance(reply, str) and len(reply) > 0

    r = requests.get(f"{API}/chat/history?session_id={sess}", headers=auth_headers)
    assert r.status_code == 200
    hist = r.json()
    assert len(hist) >= 2
    roles = [m["role"] for m in hist]
    assert "user" in roles and "assistant" in roles


# ---------- Voice extract-text ----------
def test_voice_extract_text(auth_headers):
    r = requests.post(f"{API}/voice/extract-text",
                      json={"text": "Aaj Sharma Textiles se 50,000 ka maal aaya, 12% GST"},
                      headers=auth_headers, timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    # Accept slight variation in extraction
    assert "counterparty_name" in d
    name = (d.get("counterparty_name") or "").lower()
    assert "sharma" in name
    # taxable ~50000
    ta = float(d.get("taxable_amount") or 0)
    assert 45000 <= ta <= 55000
    # total_tax ~6000 (12% of 50k)
    tt = float(d.get("total_tax") or 0)
    assert 5000 <= tt <= 7000


# ---------- WhatsApp webhook ----------
def test_whatsapp_webhook():
    r = requests.post(f"{API}/whatsapp/webhook", json={"event": "test", "message": "hi"})
    assert r.status_code == 200
    assert r.json().get("ok") is True


# ---------- Invoice OCR (LLM) ----------
def _make_synthetic_invoice_png():
    """Create a simple invoice image using Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        pytest.skip("Pillow not installed")
    img = Image.new("RGB", (700, 500), "white")
    d = ImageDraw.Draw(img)
    lines = [
        "TAX INVOICE",
        "Vendor: Kailash Textiles",
        "GSTIN: 08AAACK1234A1Z5",
        "Invoice No: KT-9999",
        "Date: 2025-01-15",
        "Item: Cotton fabric",
        "Taxable Amount: 10000",
        "CGST 6%: 600",
        "SGST 6%: 600",
        "Total: 11200",
    ]
    y = 20
    for ln in lines:
        d.text((30, y), ln, fill="black")
        y += 40
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_invoice_ocr(auth_headers):
    img_bytes = _make_synthetic_invoice_png()
    files = {"file": ("invoice.png", img_bytes, "image/png")}
    headers = {"Authorization": auth_headers["Authorization"]}
    r = requests.post(f"{API}/invoices/ocr", files=files, headers=headers, timeout=120)
    assert r.status_code == 200, r.text
    d = r.json()
    # even on partial parse, image_url should be there
    assert "image_url" in d
    # if LLM worked: counterparty should contain Kailash
    if "counterparty_name" in d and d["counterparty_name"]:
        assert "kailash" in d["counterparty_name"].lower() or "textile" in d["counterparty_name"].lower()

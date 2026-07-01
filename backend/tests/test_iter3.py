"""Iteration 3 tests: regression + WhatsApp + GSP filing + CA export.

Focuses on the new endpoints introduced in iteration 3 plus critical regression
paths across the refactored routers/ + core/ structure.
"""
import os
from datetime import datetime, timezone

import pytest
import requests
from dotenv import load_dotenv

# Load frontend .env so REACT_APP_BACKEND_URL is available when running via pytest CLI
load_dotenv("/app/frontend/.env")
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

VENDOR_EMAIL = "ramesh@hisaabbot.in"
VENDOR_PASSWORD = "demo123"
CA_EMAIL = "priya@hisaabbot.in"
CA_PASSWORD = "ca12345"


def _login(email: str, password: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok, f"no token in login response: {r.json()}"
    return tok


@pytest.fixture(scope="session")
def vendor_token() -> str:
    return _login(VENDOR_EMAIL, VENDOR_PASSWORD)


@pytest.fixture(scope="session")
def ca_token() -> str:
    return _login(CA_EMAIL, CA_PASSWORD)


@pytest.fixture(scope="session")
def current_period() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year}-{now.month:02d}"


# ---------------- REGRESSION (iteration-1/2) ----------------

class TestRegression:
    def test_health(self):
        r = requests.get(f"{API}/health", timeout=10)
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_vendor_login_me(self, vendor_token):
        r = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {vendor_token}"}, timeout=10)
        assert r.status_code == 200
        j = r.json()
        assert j["email"] == VENDOR_EMAIL
        assert j.get("role") == "vendor"

    def test_ca_login_me(self, ca_token):
        r = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {ca_token}"}, timeout=10)
        assert r.status_code == 200
        assert r.json().get("role") == "ca"

    def test_invoices_list(self, vendor_token):
        r = requests.get(f"{API}/invoices", headers={"Authorization": f"Bearer {vendor_token}"}, timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_dashboard_summary(self, vendor_token):
        r = requests.get(f"{API}/dashboard/summary", headers={"Authorization": f"Bearer {vendor_token}"}, timeout=10)
        assert r.status_code == 200
        data = r.json()
        for k in ("today", "month", "upi_month", "deadlines"):
            assert k in data

    def test_gst_summary(self, vendor_token, current_period):
        r = requests.get(f"{API}/gst/summary?month={current_period}",
                         headers={"Authorization": f"Bearer {vendor_token}"}, timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "gstr1" in data and "gstr3b" in data

    def test_gst_deadlines(self, vendor_token):
        r = requests.get(f"{API}/gst/deadlines", headers={"Authorization": f"Bearer {vendor_token}"}, timeout=10)
        assert r.status_code == 200
        assert "deadlines" in r.json()

    def test_gstin_verify(self):
        r = requests.post(f"{API}/gstin/verify", json={"gstin": "08AABCU9603R1ZM"}, timeout=10)
        assert r.status_code == 200
        j = r.json()
        assert j["valid"] is True
        assert j.get("state") == "Rajasthan"

    def test_upi_transactions(self, vendor_token):
        r = requests.get(f"{API}/upi/transactions", headers={"Authorization": f"Bearer {vendor_token}"}, timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_ca_clients(self, ca_token):
        r = requests.get(f"{API}/ca/clients", headers={"Authorization": f"Bearer {ca_token}"}, timeout=15)
        assert r.status_code == 200
        j = r.json()
        assert "clients" in j and "stats" in j
        assert len(j["clients"]) >= 4

    def test_chat_message(self, vendor_token):
        r = requests.post(
            f"{API}/chat/message",
            json={"message": "Namaste, batao GSTR-1 kya hai?"},
            headers={"Authorization": f"Bearer {vendor_token}"},
            timeout=45,
        )
        assert r.status_code == 200, r.text
        j = r.json()
        # Accept common reply field names
        reply = j.get("reply") or j.get("message") or j.get("text")
        assert reply and isinstance(reply, str) and len(reply) > 0


# ---------------- NEW: WhatsApp ----------------

class TestWhatsApp:
    def test_status_simulated(self):
        r = requests.get(f"{API}/whatsapp/status", timeout=10)
        assert r.status_code == 200
        j = r.json()
        assert j["enabled"] is False
        assert j["mode"] == "simulated"
        assert "hint" in j

    def test_send_test_requires_auth(self):
        r = requests.post(f"{API}/whatsapp/send-test", json={"to": "+919876543210", "text": "hi"}, timeout=10)
        assert r.status_code == 401

    def test_send_test_dry_run(self, vendor_token):
        r = requests.post(
            f"{API}/whatsapp/send-test",
            json={"to": "+919876543210", "text": "Namaste"},
            headers={"Authorization": f"Bearer {vendor_token}"},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("ok") is True
        assert j.get("dry_run") is True
        resp = j.get("response", {})
        assert resp.get("status") == "simulated"
        assert str(resp.get("message_id", "")).startswith("SIM-")

    def test_send_template_dry_run(self, vendor_token):
        r = requests.post(
            f"{API}/whatsapp/send-template",
            json={"to": "+919876543210", "template_id": "hisaabbot_welcome", "params": ["Ramesh"]},
            headers={"Authorization": f"Bearer {vendor_token}"},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("dry_run") is True
        assert j.get("response", {}).get("template") == "hisaabbot_welcome"

    def test_webhook_inbound_routes(self):
        payload = {
            "type": "message",
            "payload": {
                "sender": {"phone": "+919999999999"},
                "type": "text",
                "payload": {"text": "namaste bhai"},
            },
        }
        r = requests.post(f"{API}/whatsapp/webhook", json=payload, timeout=45)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("ok") is True
        assert j.get("routed") is True


# ---------------- NEW: GSP Filing pipeline ----------------

class TestGspFiling:
    def test_file_without_gstin_returns_400(self):
        # Register a fresh vendor without a GSTIN
        import uuid
        email = f"nogstin-{uuid.uuid4().hex[:8]}@hisaabbot.in"
        reg = requests.post(f"{API}/auth/register", json={
            "email": email, "password": "test12345", "name": "NoGst Vendor",
            "role": "vendor", "business_name": "NoGST Traders",
        }, timeout=15)
        assert reg.status_code in (200, 201), reg.text
        tok = reg.json().get("token") or reg.json().get("access_token")
        assert tok
        r = requests.post(
            f"{API}/gst/file",
            json={"return_type": "gstr1", "period": "2026-01"},
            headers={"Authorization": f"Bearer {tok}"},
            timeout=15,
        )
        assert r.status_code == 400
        assert "GSTIN" in r.text or "gstin" in r.text

    def test_full_file_flow(self, vendor_token, current_period):
        # 1. Upload
        r = requests.post(
            f"{API}/gst/file",
            json={"return_type": "gstr1", "period": current_period},
            headers={"Authorization": f"Bearer {vendor_token}"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        upload = r.json()
        assert "filing_id" in upload
        assert str(upload.get("ack_number", "")).startswith("SIM-ACK-")
        assert upload.get("otp_required") is True
        assert upload.get("gsp_provider") == "simulated"
        filing_id = upload["filing_id"]

        # 2. Invalid OTP (non-digit)
        r = requests.post(
            f"{API}/gst/file/submit-otp",
            json={"filing_id": filing_id, "otp": "abc"},
            headers={"Authorization": f"Bearer {vendor_token}"},
            timeout=15,
        )
        assert r.status_code == 400, r.text

        # 3. 5-digit OTP also rejected
        r = requests.post(
            f"{API}/gst/file/submit-otp",
            json={"filing_id": filing_id, "otp": "12345"},
            headers={"Authorization": f"Bearer {vendor_token}"},
            timeout=15,
        )
        assert r.status_code == 400, r.text

        # 4. Valid 6-digit OTP
        r = requests.post(
            f"{API}/gst/file/submit-otp",
            json={"filing_id": filing_id, "otp": "123456"},
            headers={"Authorization": f"Bearer {vendor_token}"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        sub = r.json()
        assert sub.get("ok") is True
        assert sub.get("status") == "submitted"
        assert str(sub.get("arn", "")).startswith("SIM-ARN-")

        # 5. Filing appears in list with status='submitted'
        r = requests.get(f"{API}/gst/filings",
                         headers={"Authorization": f"Bearer {vendor_token}"}, timeout=15)
        assert r.status_code == 200, r.text
        filings = r.json()
        assert isinstance(filings, list)
        match = [f for f in filings if f.get("_id") == filing_id]
        assert match, f"filing {filing_id} not found in list"
        assert match[0].get("status") == "submitted"
        assert str(match[0].get("arn", "")).startswith("SIM-ARN-")


# ---------------- NEW: CA export ----------------

class TestCaExport:
    def test_export_csv(self, ca_token):
        r = requests.get(f"{API}/ca/export?format=csv",
                         headers={"Authorization": f"Bearer {ca_token}"}, timeout=15)
        assert r.status_code == 200, r.text
        ct = r.headers.get("content-type", "")
        assert "text/csv" in ct, ct
        body = r.text
        assert "HisaabBot CA Export" in body
        # Column headers present
        assert "Business" in body
        assert "GSTIN" in body
        assert "Sales total (INR)" in body
        # At least one seeded client
        assert ("Bharat" in body) or ("Verma" in body) or ("Sharma" in body)

    def test_export_json(self, ca_token):
        r = requests.get(f"{API}/ca/export?format=json",
                         headers={"Authorization": f"Bearer {ca_token}"}, timeout=15)
        assert r.status_code == 200, r.text
        j = r.json()
        for k in ("generated_at", "ca_email", "period", "stats", "clients"):
            assert k in j, f"missing key {k} in export json"
        assert j["ca_email"] == CA_EMAIL
        assert isinstance(j["clients"], list) and len(j["clients"]) >= 4

    def test_export_forbidden_for_vendor(self, vendor_token):
        r = requests.get(f"{API}/ca/export?format=csv",
                         headers={"Authorization": f"Bearer {vendor_token}"}, timeout=15)
        assert r.status_code == 403

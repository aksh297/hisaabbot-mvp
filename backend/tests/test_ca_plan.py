"""CA Plan (Iteration 2) backend tests: /api/ca/* endpoints, role-gating, invite/mark/remove."""
import os
import time
from datetime import datetime
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://043b526b-3b05-4aa7-a1d6-eee4303da566.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

CA_EMAIL = "priya@hisaabbot.in"
CA_PASSWORD = "ca12345"
VENDOR_EMAIL = "ramesh@hisaabbot.in"
VENDOR_PASSWORD = "demo123"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return r.json()


@pytest.fixture(scope="module")
def ca_auth():
    data = _login(CA_EMAIL, CA_PASSWORD)
    assert data["user"]["role"] == "ca", f"Role expected ca, got {data['user']['role']}"
    return {"Authorization": f"Bearer {data['access_token']}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def vendor_auth():
    data = _login(VENDOR_EMAIL, VENDOR_PASSWORD)
    return {"Authorization": f"Bearer {data['access_token']}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def current_month():
    return datetime.utcnow().strftime("%Y-%m")


# ---- Auth / role ----
def test_ca_login_role():
    data = _login(CA_EMAIL, CA_PASSWORD)
    assert data["user"]["email"] == CA_EMAIL
    assert data["user"]["role"] == "ca"
    assert data["user"]["name"] == "Priya Verma"


def test_signup_role_ca():
    email = f"test-ca-signup-{int(time.time()*1000)}@hisaabbot.in"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": "capass123", "name": "CA Test",
        "business_name": "Test Associates", "role": "ca", "language": "en",
    }, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["user"]["role"] == "ca"
    assert d["user"]["email"] == email


# ---- CA clients listing ----
def test_ca_list_clients(ca_auth, current_month):
    r = requests.get(f"{API}/ca/clients", headers=ca_auth, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "clients" in d and "stats" in d and "period" in d
    clients = d["clients"]
    # Should have at least the 4 seeded clients
    assert len(clients) >= 4, f"Expected >=4 clients, got {len(clients)}"
    names = {(c.get("business_name") or "").strip() for c in clients}
    for expected in ["Bharat Kapda Mart", "Verma Traders", "Sharma Textiles", "Kailash Kirana Store"]:
        assert expected in names, f"Missing seeded client: {expected}. Got {names}"
    # Sharma Textiles gstr1 filed
    sharma = next(c for c in clients if c.get("business_name") == "Sharma Textiles")
    assert sharma["gstr1_status"] == "filed", f"Sharma gstr1_status expected filed, got {sharma['gstr1_status']}"
    # Each client has required fields
    for c in clients:
        for k in ("sales_total", "net_payable", "gstr1_status", "gstr3b_status", "vendor_id"):
            assert k in c, f"Missing key {k} in client row"
    # Bharat Kapda Mart sales = 168000
    bharat = next(c for c in clients if c.get("business_name") == "Bharat Kapda Mart")
    assert abs(bharat["sales_total"] - 168000) < 1, f"Bharat sales expected 168000, got {bharat['sales_total']}"


def test_ca_endpoint_vendor_forbidden(vendor_auth):
    r = requests.get(f"{API}/ca/clients", headers=vendor_auth, timeout=30)
    assert r.status_code == 403, f"Expected 403 for vendor, got {r.status_code} {r.text}"


def test_ca_endpoint_unauthenticated():
    r = requests.get(f"{API}/ca/clients", timeout=30)
    assert r.status_code == 401


# ---- Invite ----
@pytest.fixture(scope="module")
def invited_vendor_id(ca_auth):
    ts = int(time.time() * 1000)
    email = f"test-ca-invite-{ts}@test.in"
    r = requests.post(f"{API}/ca/clients/invite", headers=ca_auth, json={
        "name": "Test Client", "email": email, "business_name": "X Traders",
        "gstin": "27ABCDE1234F1Z5",
    }, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("ok") is True
    assert d.get("email") == email
    assert d.get("vendor_id")
    return {"vendor_id": d["vendor_id"], "email": email}


def test_invite_shows_in_list(ca_auth, invited_vendor_id):
    r = requests.get(f"{API}/ca/clients", headers=ca_auth, timeout=30)
    assert r.status_code == 200
    ids = {c["vendor_id"] for c in r.json()["clients"]}
    assert invited_vendor_id["vendor_id"] in ids


def test_invite_duplicate_400(ca_auth, invited_vendor_id):
    r = requests.post(f"{API}/ca/clients/invite", headers=ca_auth, json={
        "name": "Test Client Dup", "email": invited_vendor_id["email"],
        "business_name": "X Traders",
    }, timeout=30)
    assert r.status_code == 400, f"Expected 400 duplicate, got {r.status_code} {r.text}"


# ---- Mark filed ----
def test_mark_filed_gstr1_bharat(ca_auth, current_month):
    # Fetch bharat vendor_id from list
    r = requests.get(f"{API}/ca/clients", headers=ca_auth, timeout=30)
    bharat = next(c for c in r.json()["clients"] if c.get("business_name") == "Bharat Kapda Mart")
    vid = bharat["vendor_id"]
    r = requests.post(f"{API}/ca/filings/mark", headers=ca_auth, json={
        "vendor_id": vid, "period": current_month, "return_type": "gstr1", "status": "filed",
        "ack_number": "TEST-ACK-001",
    }, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True
    # Verify status updated
    r2 = requests.get(f"{API}/ca/clients", headers=ca_auth, timeout=30)
    bharat2 = next(c for c in r2.json()["clients"] if c["vendor_id"] == vid)
    assert bharat2["gstr1_status"] == "filed"


def test_mark_filed_unlinked_403(ca_auth, current_month):
    # Use a random ObjectId-like string
    fake_vid = "507f1f77bcf86cd799439011"
    r = requests.post(f"{API}/ca/filings/mark", headers=ca_auth, json={
        "vendor_id": fake_vid, "period": current_month, "return_type": "gstr1", "status": "filed",
    }, timeout=30)
    assert r.status_code == 403, f"Expected 403 for unlinked vendor, got {r.status_code}"


# ---- Client summary ----
def test_client_summary_sharma(ca_auth):
    r = requests.get(f"{API}/ca/clients", headers=ca_auth, timeout=30)
    sharma = next(c for c in r.json()["clients"] if c.get("business_name") == "Sharma Textiles")
    vid = sharma["vendor_id"]
    r2 = requests.get(f"{API}/ca/clients/{vid}/summary", headers=ca_auth, timeout=30)
    assert r2.status_code == 200, r2.text
    d = r2.json()
    for k in ("vendor", "gstr1", "gstr3b", "invoices"):
        assert k in d, f"Missing key {k} in summary"
    # invoices list should not be empty (demo has 4 seeded invoices this month)
    assert isinstance(d["invoices"], list)
    assert len(d["invoices"]) >= 1, "Sharma Textiles summary invoices empty"


# ---- Delete client link ----
def test_remove_client(ca_auth, invited_vendor_id):
    vid = invited_vendor_id["vendor_id"]
    r = requests.delete(f"{API}/ca/clients/{vid}", headers=ca_auth, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True
    # Verify it's gone
    r2 = requests.get(f"{API}/ca/clients", headers=ca_auth, timeout=30)
    ids = {c["vendor_id"] for c in r2.json()["clients"]}
    assert vid not in ids


# ---- Vendor sanity (regression) ----
def test_vendor_dashboard_still_works(vendor_auth):
    r = requests.get(f"{API}/dashboard/summary", headers=vendor_auth, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "month" in d and "deadlines" in d


def test_stats_shape(ca_auth):
    r = requests.get(f"{API}/ca/clients", headers=ca_auth, timeout=30)
    stats = r.json()["stats"]
    for k in ("total_clients", "gstr1_filed", "gstr3b_filed", "pending",
              "combined_output_tax", "combined_itc", "combined_net_payable"):
        assert k in stats
    assert stats["total_clients"] >= 4

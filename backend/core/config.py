"""Environment configuration for HisaabBot backend."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Auth
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret")
JWT_ALGO = "HS256"

# Mongo
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

# LLM
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

# Seed accounts
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@hisaabbot.in")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
DEMO_EMAIL = os.environ.get("DEMO_EMAIL", "ramesh@hisaabbot.in")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "demo123")

# Uploads
UPLOAD_DIR = Path("/app/backend/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# --- Wire-ready integrations (optional; features gracefully degrade if unset) ---
# Gupshup WhatsApp Business API
GUPSHUP_API_KEY = os.environ.get("GUPSHUP_API_KEY", "")
GUPSHUP_APP_NAME = os.environ.get("GUPSHUP_APP_NAME", "hisaabbot")
GUPSHUP_SOURCE = os.environ.get("GUPSHUP_SOURCE", "")  # E.164 phone e.g. +919XXXXXXXXX

def gupshup_enabled() -> bool:
    return bool(GUPSHUP_API_KEY and GUPSHUP_SOURCE)

# Masters India GSP for GSTR-1 / GSTR-3B filing
MASTERS_INDIA_CLIENT_ID = os.environ.get("MASTERS_INDIA_CLIENT_ID", "")
MASTERS_INDIA_CLIENT_SECRET = os.environ.get("MASTERS_INDIA_CLIENT_SECRET", "")
MASTERS_INDIA_BASE_URL = os.environ.get("MASTERS_INDIA_BASE_URL", "https://api.mastersindia.co")
MASTERS_INDIA_SANDBOX = os.environ.get("MASTERS_INDIA_SANDBOX", "true").lower() == "true"

def gsp_enabled() -> bool:
    return bool(MASTERS_INDIA_CLIENT_ID and MASTERS_INDIA_CLIENT_SECRET)

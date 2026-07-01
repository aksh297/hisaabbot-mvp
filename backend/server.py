"""
HisaabBot Backend — WhatsApp-Native AI GST & Bookkeeping Assistant
FastAPI + MongoDB + OpenAI GPT-4o (via Emergent Universal Key) + Whisper
"""
from dotenv import load_dotenv
load_dotenv()

import os
import re
import base64
import json
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Annotated, Optional, List, Any
from pathlib import Path

import bcrypt
import jwt
from bson import ObjectId
from fastapi import FastAPI, HTTPException, Request, Response, Depends, UploadFile, File, Form, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, BeforeValidator, EmailStr, ConfigDict
from motor.motor_asyncio import AsyncIOMotorClient

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent, FileContentWithMimeType
from emergentintegrations.llm.openai import OpenAISpeechToText

# ------------- Config -------------
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret")
JWT_ALGO = "HS256"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@hisaabbot.in")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
DEMO_EMAIL = os.environ.get("DEMO_EMAIL", "ramesh@hisaabbot.in")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "demo123")

UPLOAD_DIR = Path("/app/backend/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ------------- Mongo -------------
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# ------------- Pydantic base -------------
PyObjectId = Annotated[str, BeforeValidator(lambda x: str(x))]


class BaseDoc(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
    id: Optional[PyObjectId] = Field(default=None, alias="_id")


# ------------- Models -------------
class UserPublic(BaseModel):
    id: str
    email: str
    name: str
    role: str
    phone: Optional[str] = None
    business_name: Optional[str] = None
    gstin: Optional[str] = None
    city: Optional[str] = None
    language: str = "hi"


class RegisterReq(BaseModel):
    email: str
    password: str
    name: str
    business_name: Optional[str] = None
    gstin: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    language: str = "hi"
    role: Optional[str] = "vendor"  # "vendor" | "ca"


class LoginReq(BaseModel):
    email: str
    password: str


class InvoiceLineItem(BaseModel):
    description: str = ""
    hsn: Optional[str] = None
    qty: float = 1
    rate: float = 0
    amount: float = 0
    tax_rate: float = 0


class InvoiceIn(BaseModel):
    type: str  # "purchase" | "sales"
    counterparty_name: str
    counterparty_gstin: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: str  # YYYY-MM-DD
    place_of_supply: Optional[str] = None
    hsn_code: Optional[str] = None
    line_items: List[InvoiceLineItem] = []
    taxable_amount: float
    cgst: float = 0
    sgst: float = 0
    igst: float = 0
    total_tax: float = 0
    total_amount: float
    notes: Optional[str] = None
    image_url: Optional[str] = None


class UpiTxnIn(BaseModel):
    payer_name: Optional[str] = None
    upi_id: Optional[str] = None
    amount: float
    date: str
    ref_number: Optional[str] = None
    matched_invoice_id: Optional[str] = None
    image_url: Optional[str] = None
    notes: Optional[str] = None


class ChatMessageReq(BaseModel):
    session_id: Optional[str] = None
    message: str
    image_base64: Optional[str] = None


# ------------- Auth utils -------------
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(uid: str, email: str) -> str:
    payload = {"sub": uid, "email": email, "type": "access",
               "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def create_refresh_token(uid: str) -> str:
    payload = {"sub": uid, "type": "refresh",
               "exp": datetime.now(timezone.utc) + timedelta(days=30)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def _user_public(u: dict) -> dict:
    return {
        "id": str(u["_id"]),
        "email": u.get("email"),
        "name": u.get("name", ""),
        "role": u.get("role", "vendor"),
        "phone": u.get("phone"),
        "business_name": u.get("business_name"),
        "gstin": u.get("gstin"),
        "city": u.get("city"),
        "language": u.get("language", "hi"),
    }


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        uid = payload["sub"]
        try:
            oid = ObjectId(uid)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token subject")
        user = await db.users.find_one({"_id": oid})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ------------- GSTIN utils -------------
GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
STATE_CODES = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
    "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
    "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
    "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh",
    "24": "Gujarat", "25": "Daman and Diu", "26": "Dadra and Nagar Haveli", "27": "Maharashtra",
    "28": "Andhra Pradesh (Old)", "29": "Karnataka", "30": "Goa", "31": "Lakshadweep",
    "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry", "35": "Andaman and Nicobar Islands",
    "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh",
}


def validate_gstin(gstin: str) -> dict:
    """Regex-based validation + state derivation. Mocks a lookup response."""
    if not gstin:
        return {"valid": False, "error": "GSTIN required"}
    g = gstin.strip().upper()
    if not GSTIN_REGEX.match(g):
        return {"valid": False, "gstin": g, "error": "Invalid GSTIN format"}
    state = STATE_CODES.get(g[:2], "Unknown")
    pan = g[2:12]
    # NOTE: Real GSTN portal requires GSP integration (paid, KYC). We return a
    # structured verification response derived from the GSTIN pattern itself.
    return {
        "valid": True,
        "gstin": g,
        "state_code": g[:2],
        "state": state,
        "pan": pan,
        "entity_type": "Regular",
        "status": "Active",
        "note": "Simulated verification. Public GSTN API integration deferred (needs GSP KYC).",
    }


# ------------- AI helpers -------------
OCR_SYSTEM_PROMPT = """You are an expert Indian GST invoice OCR. Extract all fields from the invoice image.
Return ONLY a JSON object (no code fences, no prose) with these keys:
{
  "counterparty_name": "vendor or customer name printed on invoice",
  "counterparty_gstin": "15-char GSTIN if present else null",
  "invoice_number": "invoice number if present else null",
  "invoice_date": "YYYY-MM-DD, else best guess from any date",
  "place_of_supply": "state name if present else null",
  "hsn_code": "primary HSN/SAC code if present else null",
  "line_items": [{"description": "...", "hsn": "...", "qty": 0, "rate": 0, "amount": 0, "tax_rate": 0}],
  "taxable_amount": number,
  "cgst": number,
  "sgst": number,
  "igst": number,
  "total_tax": number,
  "total_amount": number,
  "detected_type": "purchase or sales (guess: purchase if vendor bill, sales if you issued it)",
  "confidence": 0..1,
  "notes": "any hindi/english context"
}
Rules: All amounts in INR as numbers only. If a field is not present return null (or 0 for numeric). NEVER wrap output in markdown."""

VOICE_EXTRACT_PROMPT = """You are an expert at extracting structured invoice/transaction data from a Hindi/English/Hinglish spoken sentence by an Indian trader.
Example inputs (Hinglish is common):
- "Aaj Sharma Textiles se 50,000 ka maal aaya, 12% GST"
- "Ramesh ko 25000 ki bikri, 18 percent tax"
- "Purchase from ABC Traders 15000 rupees, IGST 18%"

Return ONLY JSON:
{
  "type": "purchase or sales",
  "counterparty_name": "...",
  "counterparty_gstin": null,
  "invoice_number": null,
  "invoice_date": "YYYY-MM-DD (today if not specified)",
  "taxable_amount": number,
  "tax_rate": number (percent, e.g., 12, 18, 5),
  "cgst": number,
  "sgst": number,
  "igst": number,
  "total_tax": number,
  "total_amount": number,
  "hsn_code": null,
  "notes": "verbatim transcript",
  "confidence": 0..1
}
If the transcript is ambiguous, still return best guess and low confidence. Assume intra-state (CGST+SGST) unless user says IGST or inter-state."""

CHAT_SYSTEM_PROMPT = """You are HisaabBot — a WhatsApp-native AI CA (Chartered Accountant) assistant for Indian small vendors.
- Language: Mirror the user's language. Default to Hinglish (Hindi in Roman script). Be warm and use "aap" form.
- Tone: Trusted local mitra, not corporate. Short messages (WhatsApp style).
- You help with: GST filing (GSTR-1, GSTR-3B), invoice capture (photo/voice), bookkeeping, UPI reconciliation, HSN codes, deadlines, ITC.
- Suggest actions: "invoice ki photo bhejo", "aaj ki bikri batao", "GST status dekho".
- If user sends an invoice image, extract vendor, amount, tax and ask them to confirm before saving.
- If user asks about filing dates: GSTR-1 due on 11th of next month, GSTR-3B due on 20th of next month.
- Never invent GSTIN or filing status. If unknown, say "yeh check karna padega".
- Keep replies under 4 lines unless summarising data."""

UPI_SYSTEM_PROMPT = """You are an expert at parsing UPI payment screenshots (Google Pay / PhonePe / Paytm / BHIM). Extract from the image:
Return ONLY JSON:
{
  "payer_name": "sender name if visible else null",
  "receiver_name": "receiver if visible else null",
  "upi_id": "sender@bank or ref UPI ID",
  "amount": number in INR,
  "date": "YYYY-MM-DD",
  "time": "HH:MM else null",
  "ref_number": "UPI reference/transaction ID else null",
  "status": "success/pending/failed",
  "app": "gpay/phonepe/paytm/other",
  "confidence": 0..1
}"""


def _strip_json(text: str) -> str:
    """Remove code fences/prose so we can json.loads."""
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    # find first { and last }
    if "{" in t and "}" in t:
        t = t[t.find("{"): t.rfind("}") + 1]
    return t


async def _llm_extract(system_prompt: str, user_text: str, image_b64: Optional[str] = None) -> dict:
    """Call GPT-4o with optional image, return parsed JSON."""
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")
    session_id = f"extract-{uuid.uuid4()}"
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_prompt,
    ).with_model("openai", "gpt-4o")
    file_contents = []
    if image_b64:
        file_contents.append(ImageContent(image_base64=image_b64))
    msg = UserMessage(text=user_text, file_contents=file_contents if file_contents else None)
    reply = await chat.send_message(msg)
    raw = reply if isinstance(reply, str) else str(reply)
    cleaned = _strip_json(raw)
    try:
        return json.loads(cleaned)
    except Exception as e:
        # try to recover — return raw so upstream can decide
        return {"_raw": raw, "_error": f"JSON parse failed: {e}"}


async def _llm_chat(session_id: str, system_prompt: str, user_text: str, image_b64: Optional[str] = None) -> str:
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_prompt,
    ).with_model("openai", "gpt-4o")
    file_contents = []
    if image_b64:
        file_contents.append(ImageContent(image_base64=image_b64))
    msg = UserMessage(text=user_text, file_contents=file_contents if file_contents else None)
    reply = await chat.send_message(msg)
    return reply if isinstance(reply, str) else str(reply)


async def _whisper_transcribe(file_path: str, language: str = "hi") -> str:
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")
    stt = OpenAISpeechToText(api_key=EMERGENT_LLM_KEY)
    with open(file_path, "rb") as f:
        resp = await stt.transcribe(file=f, model="whisper-1", response_format="json", language=language)
    return getattr(resp, "text", str(resp))


# ------------- GST engine -------------
def compute_gst_summary(invoices: List[dict], month: str) -> dict:
    """month = YYYY-MM. Returns GSTR-1 + GSTR-3B like summary."""
    sales = [i for i in invoices if i.get("type") == "sales" and (i.get("invoice_date") or "").startswith(month)]
    purchases = [i for i in invoices if i.get("type") == "purchase" and (i.get("invoice_date") or "").startswith(month)]

    def _sum(items, key):
        return round(sum(float(i.get(key, 0) or 0) for i in items), 2)

    gstr1 = {
        "period": month,
        "count": len(sales),
        "taxable_amount": _sum(sales, "taxable_amount"),
        "cgst": _sum(sales, "cgst"),
        "sgst": _sum(sales, "sgst"),
        "igst": _sum(sales, "igst"),
        "total_tax": _sum(sales, "total_tax"),
        "total_amount": _sum(sales, "total_amount"),
        "invoices": [
            {
                "id": str(i["_id"]),
                "counterparty_name": i.get("counterparty_name"),
                "counterparty_gstin": i.get("counterparty_gstin"),
                "invoice_number": i.get("invoice_number"),
                "invoice_date": i.get("invoice_date"),
                "taxable_amount": i.get("taxable_amount", 0),
                "cgst": i.get("cgst", 0),
                "sgst": i.get("sgst", 0),
                "igst": i.get("igst", 0),
                "total_amount": i.get("total_amount", 0),
                "hsn_code": i.get("hsn_code"),
            } for i in sales
        ],
    }

    output_tax = gstr1["total_tax"]
    itc_available = _sum(purchases, "total_tax")
    net_payable = round(max(0, output_tax - itc_available), 2)
    gstr3b = {
        "period": month,
        "outward_taxable": gstr1["taxable_amount"],
        "output_cgst": gstr1["cgst"],
        "output_sgst": gstr1["sgst"],
        "output_igst": gstr1["igst"],
        "output_tax_total": output_tax,
        "inward_taxable": _sum(purchases, "taxable_amount"),
        "itc_cgst": _sum(purchases, "cgst"),
        "itc_sgst": _sum(purchases, "sgst"),
        "itc_igst": _sum(purchases, "igst"),
        "itc_total": itc_available,
        "net_payable": net_payable,
        "purchase_count": len(purchases),
        "sales_count": len(sales),
    }

    return {"gstr1": gstr1, "gstr3b": gstr3b}


def next_gst_deadlines(today: Optional[datetime] = None) -> List[dict]:
    today = today or datetime.now(timezone.utc)
    y, m = today.year, today.month
    # current month due dates
    next_month = m + 1 if m < 12 else 1
    year_of_next = y if m < 12 else y + 1
    dates = []
    for return_type, day in [("GSTR-1", 11), ("GSTR-3B", 20)]:
        due = datetime(year_of_next, next_month, day, 23, 59, tzinfo=timezone.utc)
        if due < today:
            # push another month
            due = datetime(year_of_next if next_month < 12 else year_of_next + 1,
                           next_month + 1 if next_month < 12 else 1, day, tzinfo=timezone.utc)
        days = (due.date() - today.date()).days
        period = f"{y}-{m:02d}"
        dates.append({
            "return_type": return_type,
            "period": period,
            "due_date": due.strftime("%Y-%m-%d"),
            "days_left": days,
        })
    return dates


# ------------- FastAPI setup -------------
app = FastAPI(title="HisaabBot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # allow_origins=* requires credentials=false
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded images so we can preview them via public URL
app.mount("/api/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

api = APIRouter(prefix="/api")


@api.get("/")
async def root():
    return {"ok": True, "service": "HisaabBot API", "version": "1.0.0"}


@api.get("/health")
async def health():
    return {"status": "healthy", "time": datetime.now(timezone.utc).isoformat()}


# ---------------- Auth ----------------
@api.post("/auth/register")
async def register(req: RegisterReq, response: Response):
    email = req.email.strip().lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    if req.gstin:
        v = validate_gstin(req.gstin)
        if not v["valid"]:
            raise HTTPException(status_code=400, detail=v.get("error", "Invalid GSTIN"))
    doc = {
        "email": email,
        "password_hash": hash_password(req.password),
        "name": req.name,
        "phone": req.phone,
        "business_name": req.business_name,
        "gstin": req.gstin.upper() if req.gstin else None,
        "city": req.city,
        "language": req.language,
        "role": req.role if req.role in ("vendor", "ca") else "vendor",
        "created_at": datetime.now(timezone.utc),
    }
    res = await db.users.insert_one(doc)
    uid = str(res.inserted_id)
    access = create_access_token(uid, email)
    refresh = create_refresh_token(uid)
    response.set_cookie("access_token", access, httponly=True, samesite="lax", max_age=7*86400, path="/")
    response.set_cookie("refresh_token", refresh, httponly=True, samesite="lax", max_age=30*86400, path="/")
    doc["_id"] = res.inserted_id
    return {"user": _user_public(doc), "access_token": access}


@api.post("/auth/login")
async def login(req: LoginReq, response: Response):
    email = req.email.strip().lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    uid = str(user["_id"])
    access = create_access_token(uid, email)
    refresh = create_refresh_token(uid)
    response.set_cookie("access_token", access, httponly=True, samesite="lax", max_age=7*86400, path="/")
    response.set_cookie("refresh_token", refresh, httponly=True, samesite="lax", max_age=30*86400, path="/")
    return {"user": _user_public(user), "access_token": access}


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(current=Depends(get_current_user)):
    return _user_public(current)


# ---------------- GSTIN ----------------
@api.post("/gstin/verify")
async def gstin_verify(payload: dict):
    return validate_gstin(payload.get("gstin", ""))


# ---------------- Invoices ----------------
def _save_upload(file: UploadFile, prefix: str) -> tuple[str, str]:
    ext = Path(file.filename or "").suffix or ".bin"
    fname = f"{prefix}-{uuid.uuid4().hex}{ext}"
    fpath = UPLOAD_DIR / fname
    return fname, str(fpath)


@api.post("/invoices/ocr")
async def invoice_ocr(file: UploadFile = File(...), current=Depends(get_current_user)):
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    fname, fpath = _save_upload(file, "invoice")
    with open(fpath, "wb") as f:
        f.write(data)
    b64 = base64.b64encode(data).decode("utf-8")
    parsed = await _llm_extract(
        OCR_SYSTEM_PROMPT,
        "Extract invoice fields from this image. Return only JSON.",
        image_b64=b64,
    )
    parsed["image_url"] = f"/api/uploads/{fname}"
    return parsed


@api.post("/invoices")
async def create_invoice(inv: InvoiceIn, current=Depends(get_current_user)):
    if inv.type not in ("purchase", "sales"):
        raise HTTPException(status_code=400, detail="type must be purchase or sales")
    doc = inv.model_dump()
    doc["user_id"] = str(current["_id"])
    doc["created_at"] = datetime.now(timezone.utc)
    # normalize
    doc["counterparty_gstin"] = (doc.get("counterparty_gstin") or "").upper() or None
    res = await db.invoices.insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    return doc


@api.get("/invoices")
async def list_invoices(type: Optional[str] = None, month: Optional[str] = None, current=Depends(get_current_user)):
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


@api.delete("/invoices/{inv_id}")
async def delete_invoice(inv_id: str, current=Depends(get_current_user)):
    res = await db.invoices.delete_one({"_id": ObjectId(inv_id), "user_id": str(current["_id"])})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"ok": True}


# ---------------- Voice ----------------
@api.post("/voice/transcribe")
async def voice_transcribe(file: UploadFile = File(...), language: str = Form("hi"),
                            current=Depends(get_current_user)):
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Audio too large (max 25MB)")
    fname, fpath = _save_upload(file, "voice")
    with open(fpath, "wb") as f:
        f.write(data)
    try:
        text = await _whisper_transcribe(fpath, language=language or "hi")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
    return {"text": text, "audio_url": f"/api/uploads/{fname}"}


@api.post("/voice/extract")
async def voice_extract(file: UploadFile = File(...), language: str = Form("hi"),
                         current=Depends(get_current_user)):
    """Transcribe audio then extract structured invoice/transaction."""
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Audio too large (max 25MB)")
    fname, fpath = _save_upload(file, "voice")
    with open(fpath, "wb") as f:
        f.write(data)
    try:
        text = await _whisper_transcribe(fpath, language=language or "hi")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
    parsed = await _llm_extract(VOICE_EXTRACT_PROMPT, f"Transcript: {text}\n\nExtract JSON.")
    parsed["transcript"] = text
    parsed["audio_url"] = f"/api/uploads/{fname}"
    return parsed


@api.post("/voice/extract-text")
async def voice_extract_text(payload: dict, current=Depends(get_current_user)):
    """Fallback: user types the sentence directly (or edits transcript) → extract."""
    text = (payload or {}).get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    parsed = await _llm_extract(VOICE_EXTRACT_PROMPT, f"Transcript: {text}\n\nExtract JSON.")
    parsed["transcript"] = text
    return parsed


# ---------------- UPI ----------------
@api.post("/upi/parse")
async def upi_parse(file: UploadFile = File(...), current=Depends(get_current_user)):
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large")
    fname, fpath = _save_upload(file, "upi")
    with open(fpath, "wb") as f:
        f.write(data)
    b64 = base64.b64encode(data).decode("utf-8")
    parsed = await _llm_extract(UPI_SYSTEM_PROMPT, "Extract UPI payment details from this screenshot.", image_b64=b64)
    parsed["image_url"] = f"/api/uploads/{fname}"
    # Attempt to match with unmatched sales invoices for this user (same amount, ±3 days)
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


@api.post("/upi/transactions")
async def create_upi_txn(txn: UpiTxnIn, current=Depends(get_current_user)):
    doc = txn.model_dump()
    doc["user_id"] = str(current["_id"])
    doc["created_at"] = datetime.now(timezone.utc)
    res = await db.upi_transactions.insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    return doc


@api.get("/upi/transactions")
async def list_upi_txns(current=Depends(get_current_user)):
    q = {"user_id": str(current["_id"])}
    cur = db.upi_transactions.find(q).sort("date", -1)
    out = []
    async for d in cur:
        d["_id"] = str(d["_id"])
        out.append(d)
    return out


# ---------------- GST ----------------
@api.get("/gst/summary")
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


@api.get("/gst/deadlines")
async def gst_deadlines(current=Depends(get_current_user)):
    return {"deadlines": next_gst_deadlines()}


# ---------------- Dashboard ----------------
@api.get("/dashboard/summary")
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
        "month": {"sales": month_sales, "purchase": month_purchase, "profit": round(month_sales["total"] - month_purchase["total"], 2)},
        "upi_month": {"total": round(upi_total, 2), "count": upi_count},
        "deadlines": deadlines,
    }


# ---------------- Chat playground ----------------
@api.post("/chat/message")
async def chat_message(req: ChatMessageReq, current=Depends(get_current_user)):
    session_id = req.session_id or f"chat-{current['_id']}"
    # Store user message
    await db.chat_messages.insert_one({
        "user_id": str(current["_id"]),
        "session_id": session_id,
        "role": "user",
        "text": req.message,
        "has_image": bool(req.image_base64),
        "created_at": datetime.now(timezone.utc),
    })

    # If image present, do OCR first and include structured extract in the prompt
    system_prompt = CHAT_SYSTEM_PROMPT
    if current.get("business_name"):
        system_prompt += f"\n\nUser's business: {current['business_name']}. GSTIN: {current.get('gstin') or 'not set'}. Language pref: {current.get('language','hi')}."

    if req.image_base64:
        # Get structured invoice preview
        ocr = await _llm_extract(OCR_SYSTEM_PROMPT, "Extract invoice fields from this image.", image_b64=req.image_base64)
        preview = json.dumps({k: v for k, v in ocr.items() if k not in ("_raw", "_error", "line_items")}, ensure_ascii=False)
        user_text = f"{req.message}\n\n[System note: user uploaded an invoice. OCR extracted: {preview}. Ask user to confirm before saving.]"
        reply = await _llm_chat(session_id, system_prompt, user_text, image_b64=req.image_base64)
    else:
        reply = await _llm_chat(session_id, system_prompt, req.message)

    await db.chat_messages.insert_one({
        "user_id": str(current["_id"]),
        "session_id": session_id,
        "role": "assistant",
        "text": reply,
        "created_at": datetime.now(timezone.utc),
    })

    return {"session_id": session_id, "reply": reply}


@api.get("/chat/history")
async def chat_history(session_id: Optional[str] = None, current=Depends(get_current_user)):
    q: dict = {"user_id": str(current["_id"])}
    if session_id:
        q["session_id"] = session_id
    cur = db.chat_messages.find(q).sort("created_at", 1)
    out = []
    async for d in cur:
        d["_id"] = str(d["_id"])
        d["created_at"] = d["created_at"].isoformat() if isinstance(d.get("created_at"), datetime) else d.get("created_at")
        out.append(d)
    return out


# ---------------- WhatsApp Webhook (Gupshup) ----------------
@api.post("/whatsapp/webhook")
async def whatsapp_webhook(payload: dict):
    """Gupshup-format inbound webhook. Real message routing is deferred; we log for now."""
    await db.whatsapp_events.insert_one({
        "raw": payload,
        "received_at": datetime.now(timezone.utc),
    })
    return {"ok": True}


@api.get("/whatsapp/webhook")
async def whatsapp_webhook_verify(request: Request):
    """Verification GET for BSP setup."""
    return {"status": "verified"}


# ---------------- CA Plan: Bulk client dashboard ----------------
class InviteClientReq(BaseModel):
    name: str
    business_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    gstin: Optional[str] = None
    city: Optional[str] = None


def _ensure_ca(user: dict):
    if user.get("role") != "ca":
        raise HTTPException(status_code=403, detail="Only CA accounts can access this")


async def _client_status_row(ca_id: str, vendor: dict, month: str) -> dict:
    """Compute a status summary for one client vendor for the given month."""
    vid = str(vendor["_id"])
    # aggregate invoices for month
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
        "status": vendor.get("client_status", "active"),  # active / invited
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


@api.get("/ca/clients")
async def ca_list_clients(month: Optional[str] = None, current=Depends(get_current_user)):
    _ensure_ca(current)
    if not month:
        now = datetime.now(timezone.utc)
        month = f"{now.year}-{now.month:02d}"
    ca_id = str(current["_id"])
    links = db.client_links.find({"ca_id": ca_id})
    rows: List[dict] = []
    vendor_ids: List[str] = []
    async for link in links:
        vendor_ids.append(link["vendor_id"])
    # fetch vendors
    if not vendor_ids:
        return {"period": month, "clients": [], "stats": _ca_stats([])}
    cursor = db.users.find({"_id": {"$in": [ObjectId(v) for v in vendor_ids]}})
    vendors = []
    async for v in cursor:
        vendors.append(v)
    for v in vendors:
        rows.append(await _client_status_row(ca_id, v, month))
    rows.sort(key=lambda r: (0 if r["gstr1_status"] == "pending" else 1, -(r["net_payable"] or 0)))
    return {"period": month, "clients": rows, "stats": _ca_stats(rows)}


def _ca_stats(rows: List[dict]) -> dict:
    total = len(rows)
    filed_1 = sum(1 for r in rows if r["gstr1_status"] == "filed")
    filed_3b = sum(1 for r in rows if r["gstr3b_status"] == "filed")
    pending = total - min(filed_1, filed_3b)
    total_output = round(sum(r.get("output_tax", 0) or 0 for r in rows), 2)
    total_itc = round(sum(r.get("itc_total", 0) or 0 for r in rows), 2)
    total_net = round(sum(r.get("net_payable", 0) or 0 for r in rows), 2)
    total_sales = round(sum(r.get("sales_total", 0) or 0 for r in rows), 2)
    return {
        "total_clients": total,
        "gstr1_filed": filed_1,
        "gstr3b_filed": filed_3b,
        "pending": pending,
        "combined_output_tax": total_output,
        "combined_itc": total_itc,
        "combined_net_payable": total_net,
        "combined_sales": total_sales,
    }


@api.post("/ca/clients/invite")
async def ca_invite_client(req: InviteClientReq, current=Depends(get_current_user)):
    _ensure_ca(current)
    if not req.email and not req.phone:
        raise HTTPException(status_code=400, detail="email or phone required")
    if req.gstin:
        v = validate_gstin(req.gstin)
        if not v["valid"]:
            raise HTTPException(status_code=400, detail=v.get("error", "Invalid GSTIN"))
    # Look up or create the vendor user
    q: dict = {}
    if req.email:
        q["email"] = req.email.strip().lower()
    vendor = await db.users.find_one(q) if q else None
    if not vendor:
        vendor_doc = {
            "email": (req.email or f"invited-{uuid.uuid4().hex[:8]}@hisaabbot.in").lower(),
            "password_hash": hash_password(uuid.uuid4().hex),  # random — invited users must reset later
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
    # Link
    ca_id = str(current["_id"])
    vid = str(vendor["_id"])
    existing = await db.client_links.find_one({"ca_id": ca_id, "vendor_id": vid})
    if existing:
        raise HTTPException(status_code=400, detail="Already your client")
    await db.client_links.insert_one({
        "ca_id": ca_id,
        "vendor_id": vid,
        "created_at": datetime.now(timezone.utc),
    })
    return {"ok": True, "vendor_id": vid, "email": vendor.get("email")}


@api.delete("/ca/clients/{vendor_id}")
async def ca_remove_client(vendor_id: str, current=Depends(get_current_user)):
    _ensure_ca(current)
    ca_id = str(current["_id"])
    res = await db.client_links.delete_one({"ca_id": ca_id, "vendor_id": vendor_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client link not found")
    return {"ok": True}


class MarkFiledReq(BaseModel):
    vendor_id: str
    period: str
    return_type: str  # "gstr1" | "gstr3b"
    status: str = "filed"  # or "pending"
    ack_number: Optional[str] = None


@api.post("/ca/filings/mark")
async def ca_mark_filed(req: MarkFiledReq, current=Depends(get_current_user)):
    _ensure_ca(current)
    _ensure_ca(current)
    ca_id = str(current["_id"])
    # Verify link
    link = await db.client_links.find_one({"ca_id": ca_id, "vendor_id": req.vendor_id})
    if not link:
        raise HTTPException(status_code=403, detail="Not your client")
    if req.return_type not in ("gstr1", "gstr3b"):
        raise HTTPException(status_code=400, detail="return_type must be gstr1 or gstr3b")
    field = f"{req.return_type}_status"
    doc = {
        "ca_id": ca_id,
        "vendor_id": req.vendor_id,
        "period": req.period,
    }
    update = {"$set": {field: req.status, f"{req.return_type}_ack": req.ack_number,
                        f"{req.return_type}_at": datetime.now(timezone.utc)}}
    await db.filings.update_one(doc, update, upsert=True)
    return {"ok": True}


@api.get("/ca/clients/{vendor_id}/summary")
async def ca_client_summary(vendor_id: str, month: Optional[str] = None, current=Depends(get_current_user)):
    _ensure_ca(current)
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
    # invoices for vendor
    cur = db.invoices.find({"user_id": vendor_id, "invoice_date": {"$regex": f"^{re.escape(month)}"}})
    invoices = []
    async for d in cur:
        d["_id"] = str(d["_id"])
        invoices.append(d)
    summary = compute_gst_summary(invoices, month)
    row = await _client_status_row(ca_id, vendor, month)
    return {"vendor": row, "gstr1": summary["gstr1"], "gstr3b": summary["gstr3b"], "invoices": invoices}


# ---------------- Startup: indexes + seed ----------------
@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.invoices.create_index([("user_id", 1), ("invoice_date", -1)])
    await db.invoices.create_index([("user_id", 1), ("type", 1)])
    await db.upi_transactions.create_index([("user_id", 1), ("date", -1)])
    await db.chat_messages.create_index([("user_id", 1), ("session_id", 1), ("created_at", 1)])

    # Seed admin
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

    # Seed demo vendor + sample invoices
    demo = await db.users.find_one({"email": DEMO_EMAIL})
    if not demo:
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
            {
                "user_id": uid, "type": "purchase", "counterparty_name": "Kailash Textiles",
                "counterparty_gstin": "08AAACK1234A1Z5", "invoice_number": "KT-0421",
                "invoice_date": f"{this_month}-05", "hsn_code": "5208",
                "line_items": [{"description": "Cotton fabric bales", "hsn": "5208", "qty": 10, "rate": 4500, "amount": 45000, "tax_rate": 12}],
                "taxable_amount": 45000, "cgst": 2700, "sgst": 2700, "igst": 0,
                "total_tax": 5400, "total_amount": 50400,
                "created_at": now,
            },
            {
                "user_id": uid, "type": "sales", "counterparty_name": "Bharat Kapda Mart",
                "counterparty_gstin": "08BHRTK4567B1Z9", "invoice_number": "ST-0119",
                "invoice_date": f"{this_month}-07", "hsn_code": "5208",
                "line_items": [{"description": "Cotton fabric retail", "hsn": "5208", "qty": 5, "rate": 6000, "amount": 30000, "tax_rate": 12}],
                "taxable_amount": 30000, "cgst": 1800, "sgst": 1800, "igst": 0,
                "total_tax": 3600, "total_amount": 33600,
                "created_at": now,
            },
            {
                "user_id": uid, "type": "sales", "counterparty_name": "Retail Cash Sale",
                "counterparty_gstin": None, "invoice_number": "ST-0120",
                "invoice_date": f"{this_month}-08", "hsn_code": "5208",
                "line_items": [{"description": "Fabric", "hsn": "5208", "qty": 3, "rate": 5500, "amount": 16500, "tax_rate": 12}],
                "taxable_amount": 16500, "cgst": 990, "sgst": 990, "igst": 0,
                "total_tax": 1980, "total_amount": 18480,
                "created_at": now,
            },
            {
                "user_id": uid, "type": "purchase", "counterparty_name": "Delhi Yarn Suppliers",
                "counterparty_gstin": "07DELHY6789C1Z3", "invoice_number": "DY-2201",
                "invoice_date": f"{this_month}-03", "hsn_code": "5205",
                "line_items": [{"description": "Yarn bundles (inter-state)", "hsn": "5205", "qty": 20, "rate": 800, "amount": 16000, "tax_rate": 12}],
                "taxable_amount": 16000, "cgst": 0, "sgst": 0, "igst": 1920,
                "total_tax": 1920, "total_amount": 17920,
                "created_at": now,
            },
        ]
        await db.invoices.insert_many(sample_invoices)
        await db.upi_transactions.insert_many([
            {
                "user_id": uid, "payer_name": "Bharat Kapda Mart", "upi_id": "bharatkapda@okhdfcbank",
                "amount": 33600, "date": f"{this_month}-07", "ref_number": "UPI2024050712345",
                "matched_invoice_id": None, "created_at": now,
            },
            {
                "user_id": uid, "payer_name": "Cash Customer", "upi_id": "customer@paytm",
                "amount": 18480, "date": f"{this_month}-08", "ref_number": "UPI2024050898765",
                "matched_invoice_id": None, "created_at": now,
            },
        ])

    print(f"[startup] HisaabBot ready. Admin={ADMIN_EMAIL}, Demo={DEMO_EMAIL}")

    # Seed demo CA + linked clients
    await db.client_links.create_index([("ca_id", 1), ("vendor_id", 1)], unique=True)
    await db.filings.create_index([("ca_id", 1), ("vendor_id", 1), ("period", 1)], unique=True)

    ca_email = "priya@hisaabbot.in"
    ca = await db.users.find_one({"email": ca_email})
    if not ca:
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

        # 4 sample client vendors
        clients_data = [
            {
                "email": "verma_traders@hisaabbot.in",
                "name": "Suresh Verma", "business_name": "Verma Traders",
                "gstin": "07VERMA1234A1Z0", "city": "Delhi", "phone": "+919811111111",
                "invoices": [
                    {"type": "sales", "counterparty_name": "Anand Enterprises", "counterparty_gstin": "07ANAND5678B2Z1",
                     "invoice_number": "VT-101", "invoice_date": f"{this_month}-04", "hsn_code": "8517",
                     "taxable_amount": 80000, "cgst": 7200, "sgst": 7200, "igst": 0, "total_tax": 14400, "total_amount": 94400},
                    {"type": "purchase", "counterparty_name": "Delhi Electronics", "counterparty_gstin": "07DELEL2233C1Z8",
                     "invoice_number": "DE-2201", "invoice_date": f"{this_month}-02", "hsn_code": "8517",
                     "taxable_amount": 50000, "cgst": 4500, "sgst": 4500, "igst": 0, "total_tax": 9000, "total_amount": 59000},
                ],
                "gstr1_status": "pending", "gstr3b_status": "pending",
            },
            {
                "email": "kailash_kirana@hisaabbot.in",
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
                ],
                "gstr1_status": "draft", "gstr3b_status": "pending",
            },
            {
                "email": "bharat_kapda@hisaabbot.in",
                "name": "Anil Bharat", "business_name": "Bharat Kapda Mart",
                "gstin": "08BHRTK4567B1Z9", "city": "Jaipur", "phone": "+919833333333",
                "invoices": [
                    {"type": "sales", "counterparty_name": "Fashion Hub", "counterparty_gstin": "08FASHN1122F3Z6",
                     "invoice_number": "BK-701", "invoice_date": f"{this_month}-03", "hsn_code": "6109",
                     "taxable_amount": 150000, "cgst": 9000, "sgst": 9000, "igst": 0, "total_tax": 18000, "total_amount": 168000},
                    {"type": "purchase", "counterparty_name": "Sharma Textiles", "counterparty_gstin": "08AABCU9603R1ZM",
                     "invoice_number": "ST-0119", "invoice_date": f"{this_month}-07", "hsn_code": "5208",
                     "taxable_amount": 30000, "cgst": 1800, "sgst": 1800, "igst": 0, "total_tax": 3600, "total_amount": 33600},
                ],
                "gstr1_status": "pending", "gstr3b_status": "pending",
                "urgent": True,
            },
            {
                "email": "sharma_textiles_link@hisaabbot.in",  # separate link doc; actually we'll link the existing demo user too
                "name": "Ramesh Sharma (existing)", "business_name": "Sharma Textiles",
                "gstin": "08AABCU9603R1ZM", "city": "Jaipur", "phone": "+919876543210",
                "invoices": [],  # already has sample invoices from demo seed
                "link_existing": DEMO_EMAIL,
                "gstr1_status": "filed", "gstr3b_status": "pending", "ack_number": "AB12345678",
            },
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
                # insert invoices for this vendor
                for inv in cdata.get("invoices", []):
                    await db.invoices.insert_one({
                        **inv, "user_id": vendor_id, "line_items": [], "created_at": now,
                    })
            else:
                vendor_id = str(vendor["_id"])
            # link ca ↔ vendor
            try:
                await db.client_links.insert_one({
                    "ca_id": ca_id, "vendor_id": vendor_id, "created_at": now,
                })
            except Exception:
                pass  # unique index guard
            # filings status
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
        print(f"[startup] Seeded CA {ca_email} with {len(clients_data)} demo clients")


app.include_router(api)

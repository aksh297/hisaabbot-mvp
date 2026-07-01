"""GPT-4o + Whisper wrappers via emergentintegrations."""
import json
import re
import uuid
from typing import Optional

from fastapi import HTTPException
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
from emergentintegrations.llm.openai import OpenAISpeechToText

from .config import EMERGENT_LLM_KEY


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
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    if "{" in t and "}" in t:
        t = t[t.find("{"): t.rfind("}") + 1]
    return t


async def llm_extract(system_prompt: str, user_text: str, image_b64: Optional[str] = None) -> dict:
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
        return {"_raw": raw, "_error": f"JSON parse failed: {e}"}


async def llm_chat(session_id: str, system_prompt: str, user_text: str, image_b64: Optional[str] = None) -> str:
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


async def whisper_transcribe(file_path: str, language: str = "hi") -> str:
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")
    stt = OpenAISpeechToText(api_key=EMERGENT_LLM_KEY)
    with open(file_path, "rb") as f:
        resp = await stt.transcribe(file=f, model="whisper-1", response_format="json", language=language)
    return getattr(resp, "text", str(resp))

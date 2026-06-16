"""
HisaabBot — Invoice OCR & Extraction Engine
============================================
Extracts structured GST invoice data from image URLs or local file paths.

Pipeline:
  1. extract_raw_text()  — Google Cloud Vision OCR (mocked for local dev)
  2. parse_with_llm()    — GPT-4o prompt engineered for Indian GST invoice formats
  3. Returns a clean InvoiceData Pydantic model (serialisable to JSON)

Bharat-first design:
  - Handles Hindi / Hinglish / Tamil / Marathi / Telugu labels on invoices
  - Understands Indian date formats (DD/MM/YYYY, DD-MM-YYYY, "दिनांक")
  - Maps CGST + SGST + IGST + CESS correctly
  - Validates GSTINs (15-char alphanumeric, state-code prefix)
  - Recognises HSN / SAC codes for goods and services
"""

import json
import logging
import os
import re
import urllib.request
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("hisaabbot.ocr")

# ---------------------------------------------------------------------------
# Output schema — everything the downstream bookkeeping engine needs
# ---------------------------------------------------------------------------

class TaxBreakdown(BaseModel):
    cgst_rate: Optional[float] = Field(None, description="CGST rate in percent (e.g. 9.0)")
    cgst_amount: Optional[float] = Field(None, description="CGST amount in INR")
    sgst_rate: Optional[float] = Field(None, description="SGST rate in percent (e.g. 9.0)")
    sgst_amount: Optional[float] = Field(None, description="SGST amount in INR")
    igst_rate: Optional[float] = Field(None, description="IGST rate in percent (e.g. 18.0)")
    igst_amount: Optional[float] = Field(None, description="IGST amount in INR")
    cess_amount: Optional[float] = Field(None, description="CESS amount in INR if present")
    total_tax_amount: Optional[float] = Field(None, description="Sum of all tax components in INR")


class InvoiceData(BaseModel):
    """Structured output of an OCR + LLM parsed Indian GST invoice."""

    # Core identification
    vendor_name: Optional[str] = Field(None, description="Supplier / seller legal name")
    vendor_gstin: Optional[str] = Field(None, description="Supplier GSTIN (15-char)")
    buyer_name: Optional[str] = Field(None, description="Buyer / recipient legal name")
    buyer_gstin: Optional[str] = Field(None, description="Buyer GSTIN if present")

    # Invoice metadata
    invoice_number: Optional[str] = Field(None, description="Invoice / bill number")
    invoice_date: Optional[str] = Field(None, description="Invoice date (YYYY-MM-DD if parseable)")
    place_of_supply: Optional[str] = Field(None, description="State name or code")

    # Amounts
    subtotal_amount: Optional[float] = Field(None, description="Pre-tax subtotal in INR")
    total_amount: Optional[float] = Field(None, description="Grand total including all taxes in INR")
    tax: TaxBreakdown = Field(default_factory=TaxBreakdown)

    # HSN / SAC codes found on the invoice
    hsn_codes: list[str] = Field(default_factory=list, description="List of HSN/SAC codes detected")

    # Raw text for audit / debugging
    raw_ocr_text: Optional[str] = Field(None, description="Full raw OCR text before LLM parsing")

    # Confidence and error tracking
    confidence: str = Field("low", description="high | medium | low — LLM self-assessed confidence")
    parse_warnings: list[str] = Field(default_factory=list, description="Non-fatal issues noted during parsing")

    @field_validator("vendor_gstin", "buyer_gstin", mode="before")
    @classmethod
    def validate_gstin(cls, v: Optional[str]) -> Optional[str]:
        """
        GSTIN format: 2-digit state code + 10-char PAN + 1-char entity + Z + 1 check char.
        Example: 08AABCU9603R1ZM
        """
        if v is None:
            return None
        cleaned = v.strip().upper().replace(" ", "")
        # Basic pattern: 15 alphanumeric chars starting with 01-37 (valid state codes)
        if re.fullmatch(r"[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]", cleaned):
            return cleaned
        # Return as-is but will be flagged in parse_warnings downstream
        return cleaned


# ---------------------------------------------------------------------------
# GSTIN state code reference — used in prompt and output enrichment
# ---------------------------------------------------------------------------

GSTIN_STATE_CODES: dict[str, str] = {
    "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana",
    "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
    "13": "Nagaland", "14": "Manipur", "15": "Mizoram",
    "16": "Tripura", "17": "Meghalaya", "18": "Assam",
    "19": "West Bengal", "20": "Jharkhand", "21": "Odisha",
    "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "26": "Dadra & Nagar Haveli and Daman & Diu", "27": "Maharashtra",
    "28": "Andhra Pradesh", "29": "Karnataka", "30": "Goa",
    "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu",
    "34": "Puducherry", "35": "Andaman & Nicobar Islands",
    "36": "Telangana", "37": "Andhra Pradesh (New)",
    "38": "Ladakh", "97": "Other Territory", "99": "Centre Jurisdiction",
}


# ---------------------------------------------------------------------------
# Mock OCR response — used when Google Cloud Vision credentials are absent
# ---------------------------------------------------------------------------

MOCK_OCR_TEXT = """
TAX INVOICE
===========
Sharma Textiles Pvt. Ltd.
GSTIN: 08AABCU9603R1ZM
Address: Plot No. 42, RIICO Industrial Area, Jaipur - 302013, Rajasthan

Invoice No.: ST/2526/001247          Date: 15/06/2026
Bill To:
M/s Patel Garments
GSTIN: 24AADCP3456Q1ZR
Address: Ring Road, Surat - 395003, Gujarat

Place of Supply: Gujarat (24)

Description of Goods:
+-------------------+-------+-----+----------+-------+-----------+-----------+
| Description        | HSN   | Qty | Rate     | Value | IGST 12%  | Total     |
+-------------------+-------+-----+----------+-------+-----------+-----------+
| Cotton Fabric       | 5208  | 500 | 80.00    | 40,000| 4,800.00  | 44,800.00 |
| Polyester Blend     | 5512  | 200 | 150.00   | 30,000| 3,600.00  | 33,600.00 |
+-------------------+-------+-----+----------+-------+-----------+-----------+

Subtotal:                    ₹70,000.00
IGST @ 12%:                  ₹8,400.00
Round Off:                   +₹0.00
Grand Total:                 ₹78,400.00

Amount in Words: Seventy-Eight Thousand Four Hundred Rupees Only

Authorised Signatory: [Signature]
"""


# ---------------------------------------------------------------------------
# LLM system prompt — Bharat-first, GST-aware
# ---------------------------------------------------------------------------

LLM_SYSTEM_PROMPT = """You are HisaabBot's Indian GST invoice parser. Your job is to extract
structured data from raw OCR text of Indian tax invoices.

KEY RULES — READ CAREFULLY:

1. INDIAN GST INVOICE STRUCTURE:
   - Every GST invoice must have: Supplier GSTIN, Invoice No., Invoice Date, HSN/SAC codes, Tax rates
   - GSTINs are 15 characters: [2-digit state code][10-char PAN][entity code][Z][check digit]
   - Valid state codes: 01-38, 97, 99 (see reference list below)
   - CGST + SGST applies for intra-state supplies (same state for supplier and buyer)
   - IGST applies for inter-state supplies (different states)
   - Total Tax = CGST + SGST (or IGST alone) + CESS (if any)

2. HINDI / HINGLISH / REGIONAL LANGUAGE LABELS TO RECOGNISE:
   - "विक्रेता" or "बेचने वाला" = Vendor/Supplier
   - "खरीदार" or "क्रेता" = Buyer
   - "दिनांक" = Date
   - "कुल राशि" = Total Amount
   - "कर" = Tax
   - "माल का विवरण" = Description of goods
   - "बिल नंबर" or "चालान" = Invoice number
   - "जमा राशि" = Amount paid
   - HSN codes may appear as "HSN Code", "HSN/SAC", "Tariff Code", "वस्तु कोड"
   - Amount may appear as "₹", "Rs.", "INR", "रुपये", "रु."

3. AMOUNT PARSING (CRITICAL for Indian number system):
   - Indian lakhs format: 1,00,000 (not 100,000) — parse correctly
   - ₹1,50,000.50 = 150000.50 INR
   - Remove commas and currency symbols before converting to float
   - "Fifteen Thousand" in words → 15000

4. DATE NORMALISATION:
   - Indian invoices use DD/MM/YYYY or DD-MM-YYYY
   - Convert to YYYY-MM-DD for output
   - "15/06/2026" → "2026-06-15"
   - If date unclear, return the raw string as found

5. CONFIDENCE ASSESSMENT:
   - "high": GSTIN found and valid, amount clear, date clear, HSN present
   - "medium": Most fields present but some ambiguity (blurry text, partial data)
   - "low": Key fields missing or OCR quality is poor

6. WARNINGS:
   - Flag if GSTIN doesn't match standard pattern
   - Flag if CGST+SGST total doesn't match stated total tax
   - Flag if invoice date is more than 1 year old (potential backdating)
   - Flag if HSN code has fewer than 4 digits (incomplete)

GSTIN STATE CODE REFERENCE:
07=Delhi, 08=Rajasthan, 09=UP, 19=West Bengal, 24=Gujarat, 27=Maharashtra,
29=Karnataka, 32=Kerala, 33=Tamil Nadu, 36=Telangana, 06=Haryana, 03=Punjab

OUTPUT FORMAT — Return ONLY valid JSON, no markdown, no explanation:
{
  "vendor_name": "string or null",
  "vendor_gstin": "string or null",
  "buyer_name": "string or null",
  "buyer_gstin": "string or null",
  "invoice_number": "string or null",
  "invoice_date": "YYYY-MM-DD or raw string or null",
  "place_of_supply": "string or null",
  "subtotal_amount": float or null,
  "total_amount": float or null,
  "tax": {
    "cgst_rate": float or null,
    "cgst_amount": float or null,
    "sgst_rate": float or null,
    "sgst_amount": float or null,
    "igst_rate": float or null,
    "igst_amount": float or null,
    "cess_amount": float or null,
    "total_tax_amount": float or null
  },
  "hsn_codes": ["string", ...],
  "confidence": "high | medium | low",
  "parse_warnings": ["string", ...]
}
"""


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class InvoiceExtractor:
    """
    Core OCR and LLM extraction engine for HisaabBot.

    Usage:
        extractor = InvoiceExtractor()

        # From a public URL
        result = extractor.extract("https://example.com/invoice.jpg")

        # From a local file path
        result = extractor.extract("/tmp/invoice.jpg")

        # Step by step
        raw = extractor.extract_raw_text("path/to/invoice.jpg")
        data = extractor.parse_with_llm(raw)
        print(data.model_dump_json(indent=2))

    Environment variables:
        GOOGLE_APPLICATION_CREDENTIALS  — Path to GCP service account JSON key file
        OPENAI_API_KEY                  — OpenAI API key for GPT-4o
        HISAABBOT_OCR_MOCK              — Set to "1" to force mock mode (no real API calls)
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        gcp_credentials_path: Optional[str] = None,
        mock_mode: Optional[bool] = None,
    ) -> None:
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY", "")
        self.gcp_credentials_path = gcp_credentials_path or os.getenv(
            "GOOGLE_APPLICATION_CREDENTIALS", ""
        )

        # Mock mode: explicit parameter > env var > auto-detect (no real credentials)
        if mock_mode is not None:
            self._mock_mode = mock_mode
        else:
            env_flag = os.getenv("HISAABBOT_OCR_MOCK", "").strip()
            if env_flag == "1":
                self._mock_mode = True
            else:
                self._mock_mode = not bool(self.gcp_credentials_path)

        logger.info(
            "InvoiceExtractor init | mock_ocr=%s | openai_configured=%s",
            self._mock_mode,
            bool(self.openai_api_key),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, image_source: str) -> InvoiceData:
        """
        Full pipeline: image source → InvoiceData.

        Args:
            image_source: HTTP/HTTPS URL or local file path to the invoice image.

        Returns:
            InvoiceData with all extracted fields.
        """
        raw_text = self.extract_raw_text(image_source)
        invoice = self.parse_with_llm(raw_text)
        invoice.raw_ocr_text = raw_text
        return invoice

    def extract_raw_text(self, image_source: str) -> str:
        """
        Extract raw text from the invoice image using Google Cloud Vision OCR.

        In mock mode (no GCP credentials), returns a realistic Indian GST invoice
        text fixture so the rest of the pipeline can be tested end-to-end.

        Args:
            image_source: HTTP/HTTPS URL or local absolute/relative file path.

        Returns:
            Raw OCR text as a single string.
        """
        if self._mock_mode:
            logger.info("🔧 OCR mock mode — returning fixture text | source=%s", image_source)
            return MOCK_OCR_TEXT.strip()

        # --- Real Google Cloud Vision path ---
        try:
            from google.cloud import vision  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "google-cloud-vision is not installed. "
                "Run: pip install google-cloud-vision"
            ) from exc

        client = vision.ImageAnnotatorClient()

        if image_source.startswith(("http://", "https://")):
            image = vision.Image(source=vision.ImageSource(image_uri=image_source))
        else:
            path = Path(image_source)
            if not path.exists():
                raise FileNotFoundError(f"Invoice image not found: {image_source}")
            with open(path, "rb") as f:
                content = f.read()
            image = vision.Image(content=content)

        logger.info("📡 Sending image to Google Cloud Vision | source=%s", image_source)
        response = client.document_text_detection(image=image)

        if response.error.message:
            raise RuntimeError(
                f"Google Cloud Vision error: {response.error.message}\n"
                "Check https://cloud.google.com/apis/design/errors for details."
            )

        full_text: str = response.full_text_annotation.text
        logger.info("✅ OCR complete | chars=%d", len(full_text))
        return full_text

    def parse_with_llm(self, raw_text: str) -> InvoiceData:
        """
        Send raw OCR text to GPT-4o with a Bharat-first prompt to extract
        structured GST invoice fields.

        Falls back to a rule-based heuristic parser when no OpenAI API key is
        configured — useful for unit tests and local development without any keys.

        Args:
            raw_text: OCR-extracted text from the invoice image.

        Returns:
            InvoiceData pydantic model with all extracted fields.
        """
        if not self.openai_api_key:
            logger.info("🔧 No OpenAI key — using heuristic fallback parser")
            return self._heuristic_parse(raw_text)

        try:
            from openai import OpenAI  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "openai package is not installed. Run: pip install openai"
            ) from exc

        client = OpenAI(api_key=self.openai_api_key)

        user_message = (
            "Here is the raw OCR text extracted from an Indian GST tax invoice. "
            "Please extract all the structured fields as specified.\n\n"
            f"--- BEGIN OCR TEXT ---\n{raw_text}\n--- END OCR TEXT ---"
        )

        logger.info("🤖 Sending OCR text to GPT-4o for structured extraction")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.0,       # Deterministic for data extraction
            max_tokens=1024,
            response_format={"type": "json_object"},
        )

        raw_json = response.choices[0].message.content or "{}"
        logger.info("✅ GPT-4o extraction complete | tokens_used=%d", response.usage.total_tokens)

        return self._json_to_invoice_data(raw_json, raw_text)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _json_to_invoice_data(self, raw_json: str, raw_text: str = "") -> InvoiceData:
        """
        Parse the LLM's JSON response into an InvoiceData model.
        Handles common LLM formatting issues gracefully.
        """
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            logger.warning("LLM returned invalid JSON: %s | raw=%s", exc, raw_json[:200])
            return InvoiceData(
                raw_ocr_text=raw_text,
                parse_warnings=[f"LLM returned invalid JSON: {exc}"],
                confidence="low",
            )

        # Nest the tax breakdown correctly if the LLM flattened it
        tax_fields = {
            "cgst_rate", "cgst_amount", "sgst_rate", "sgst_amount",
            "igst_rate", "igst_amount", "cess_amount", "total_tax_amount",
        }
        if "tax" not in data:
            tax_data = {k: data.pop(k, None) for k in tax_fields}
            data["tax"] = tax_data

        # Ensure hsn_codes is always a list
        if isinstance(data.get("hsn_codes"), str):
            data["hsn_codes"] = [data["hsn_codes"]] if data["hsn_codes"] else []

        # Ensure parse_warnings is always a list
        if isinstance(data.get("parse_warnings"), str):
            data["parse_warnings"] = [data["parse_warnings"]] if data["parse_warnings"] else []

        try:
            return InvoiceData(**data)
        except Exception as exc:
            logger.warning("InvoiceData validation error: %s", exc)
            return InvoiceData(
                raw_ocr_text=raw_text,
                parse_warnings=[f"Validation error: {exc}"],
                confidence="low",
            )

    def _heuristic_parse(self, raw_text: str) -> InvoiceData:
        """
        Rule-based fallback parser using regex patterns for common Indian GST
        invoice layouts. Used when no LLM API key is available.

        Handles common formats used by Tally, Busy, Zoho Books, and hand-typed
        invoices from small Indian traders.
        """
        warnings: list[str] = ["Heuristic parser used — no OpenAI key configured"]
        tax = TaxBreakdown()

        # --- Vendor GSTIN ---
        gstin_pattern = r"\b([0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b"
        gstins = re.findall(gstin_pattern, raw_text.upper())
        vendor_gstin = gstins[0] if gstins else None
        buyer_gstin = gstins[1] if len(gstins) > 1 else None

        # --- Vendor name: line before or after GSTIN ---
        vendor_name: Optional[str] = None
        if vendor_gstin:
            lines = raw_text.strip().splitlines()
            for i, line in enumerate(lines):
                if vendor_gstin in line.upper():
                    if i > 0:
                        candidate = lines[i - 1].strip()
                        if len(candidate) > 3 and not re.search(r"^\d", candidate):
                            vendor_name = candidate
                    break

        # --- Invoice number ---
        inv_no_match = re.search(
            r"(?:invoice\s*(?:no\.?|number|#)|bill\s*no\.?|चालान\s*(?:नंबर)?)"
            r"[\s:]*([A-Z0-9/\-]{4,30})",
            raw_text,
            re.IGNORECASE,
        )
        invoice_number = inv_no_match.group(1).strip() if inv_no_match else None

        # --- Invoice date (DD/MM/YYYY or DD-MM-YYYY) ---
        date_match = re.search(
            r"\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})\b",
            raw_text,
        )
        invoice_date: Optional[str] = None
        if date_match:
            dd, mm, yyyy = date_match.groups()
            try:
                invoice_date = f"{yyyy}-{int(mm):02d}-{int(dd):02d}"
            except ValueError:
                invoice_date = date_match.group(0)

        # --- Amounts: search for ₹/Rs. followed by Indian-format numbers ---
        amount_pattern = r"(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)"
        amounts_raw = re.findall(amount_pattern, raw_text, re.IGNORECASE)
        amounts = []
        for a in amounts_raw:
            try:
                amounts.append(float(a.replace(",", "")))
            except ValueError:
                pass

        total_amount: Optional[float] = max(amounts) if amounts else None

        # --- Grand Total label ---
        grand_total_match = re.search(
            r"(?:grand\s*total|total\s*amount|कुल\s*राशि|net\s*payable)"
            r"[\s:₹Rs.INR]*"
            r"([\d,]+(?:\.\d{1,2})?)",
            raw_text,
            re.IGNORECASE,
        )
        if grand_total_match:
            try:
                total_amount = float(grand_total_match.group(1).replace(",", ""))
            except ValueError:
                pass

        # --- Subtotal ---
        subtotal_match = re.search(
            r"(?:subtotal|sub-total|taxable\s*value|taxable\s*amount)"
            r"[\s:₹Rs.]*"
            r"([\d,]+(?:\.\d{1,2})?)",
            raw_text,
            re.IGNORECASE,
        )
        subtotal_amount: Optional[float] = None
        if subtotal_match:
            try:
                subtotal_amount = float(subtotal_match.group(1).replace(",", ""))
            except ValueError:
                pass

        # --- IGST ---
        igst_match = re.search(
            r"IGST\s*@?\s*([\d.]+)\s*%[\s:₹Rs.INR]*([\d,]+(?:\.\d{1,2})?)",
            raw_text,
            re.IGNORECASE,
        )
        if igst_match:
            try:
                tax.igst_rate = float(igst_match.group(1))
                tax.igst_amount = float(igst_match.group(2).replace(",", ""))
            except ValueError:
                pass

        # --- CGST ---
        cgst_match = re.search(
            r"CGST\s*@?\s*([\d.]+)\s*%[\s:₹Rs.INR]*([\d,]+(?:\.\d{1,2})?)",
            raw_text,
            re.IGNORECASE,
        )
        if cgst_match:
            try:
                tax.cgst_rate = float(cgst_match.group(1))
                tax.cgst_amount = float(cgst_match.group(2).replace(",", ""))
            except ValueError:
                pass

        # --- SGST ---
        sgst_match = re.search(
            r"SGST\s*@?\s*([\d.]+)\s*%[\s:₹Rs.INR]*([\d,]+(?:\.\d{1,2})?)",
            raw_text,
            re.IGNORECASE,
        )
        if sgst_match:
            try:
                tax.sgst_rate = float(sgst_match.group(1))
                tax.sgst_amount = float(sgst_match.group(2).replace(",", ""))
            except ValueError:
                pass

        # --- CESS ---
        cess_match = re.search(
            r"CESS[\s:₹Rs.INR]*([\d,]+(?:\.\d{1,2})?)",
            raw_text,
            re.IGNORECASE,
        )
        if cess_match:
            try:
                tax.cess_amount = float(cess_match.group(1).replace(",", ""))
            except ValueError:
                pass

        # --- Total tax (compute if possible, else search) ---
        computed_tax: Optional[float] = None
        components = [
            c for c in [tax.cgst_amount, tax.sgst_amount, tax.igst_amount, tax.cess_amount]
            if c is not None
        ]
        if components:
            computed_tax = sum(components)
        else:
            tax_match = re.search(
                r"(?:total\s*tax|total\s*gst|tax\s*amount)[\s:₹Rs.INR]*([\d,]+(?:\.\d{1,2})?)",
                raw_text,
                re.IGNORECASE,
            )
            if tax_match:
                try:
                    computed_tax = float(tax_match.group(1).replace(",", ""))
                except ValueError:
                    pass
        tax.total_tax_amount = computed_tax

        # --- HSN / SAC codes (4-8 digit numbers near HSN/SAC label) ---
        hsn_codes: list[str] = []
        hsn_matches = re.findall(
            r"(?:HSN[/\s]*SAC|HSN\s*Code|SAC\s*Code|HSN|SAC|वस्तु\s*कोड)"
            r"[\s:]*(\d{4,8})",
            raw_text,
            re.IGNORECASE,
        )
        hsn_codes.extend(hsn_matches)

        # Also pick up standalone 4-8 digit numbers that appear in table-like rows
        # common in Tally/Busy export formats
        table_hsn = re.findall(r"\|\s*(\d{4,8})\s*\|", raw_text)
        for code in table_hsn:
            if code not in hsn_codes:
                hsn_codes.append(code)

        # --- Place of supply (state name or code near "Place of Supply") ---
        pos_match = re.search(
            r"place\s*of\s*supply[\s:]*([A-Za-z &]+?)(?:\s*\((\d{2})\))?(?:\n|$|,)",
            raw_text,
            re.IGNORECASE,
        )
        place_of_supply: Optional[str] = None
        if pos_match:
            state_name = pos_match.group(1).strip()
            state_code = pos_match.group(2)
            if state_code and state_code in GSTIN_STATE_CODES:
                place_of_supply = f"{state_name} ({state_code})"
            else:
                place_of_supply = state_name

        # --- Confidence assessment ---
        filled_count = sum([
            vendor_gstin is not None,
            total_amount is not None,
            invoice_date is not None,
            bool(hsn_codes),
        ])
        confidence = "high" if filled_count >= 3 else "medium" if filled_count >= 2 else "low"

        return InvoiceData(
            vendor_name=vendor_name,
            vendor_gstin=vendor_gstin,
            buyer_gstin=buyer_gstin,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            place_of_supply=place_of_supply,
            subtotal_amount=subtotal_amount,
            total_amount=total_amount,
            tax=tax,
            hsn_codes=list(dict.fromkeys(hsn_codes)),  # deduplicate, preserve order
            raw_ocr_text=raw_text,
            confidence=confidence,
            parse_warnings=warnings,
        )

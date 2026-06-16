"""
Tests for HisaabBot Invoice OCR Engine
=======================================
All tests run in mock mode (no real API keys required).
"""

import json
import pytest
import sys
from pathlib import Path

# Ensure the module is importable from test context
sys.path.insert(0, str(Path(__file__).parent))

from invoice_extractor import (
    InvoiceExtractor,
    InvoiceData,
    TaxBreakdown,
    MOCK_OCR_TEXT,
    LLM_SYSTEM_PROMPT,
    GSTIN_STATE_CODES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def extractor():
    """InvoiceExtractor in full mock mode — no GCP, no OpenAI."""
    return InvoiceExtractor(mock_mode=True)


@pytest.fixture
def extractor_with_fake_key():
    """Mock OCR, but with a fake OpenAI key to test the JSON-to-model path."""
    e = InvoiceExtractor(mock_mode=True, openai_api_key="sk-fake-key")
    return e


IGST_INVOICE_TEXT = """
TAX INVOICE
Sharma Textiles Pvt. Ltd.
GSTIN: 08AABCU9603R1ZM
Address: Jaipur, Rajasthan

Invoice No.: ST/2526/001247    Date: 15/06/2026
Bill To: Patel Garments
GSTIN: 24AADCP3456Q1ZR
Place of Supply: Gujarat (24)

Cotton Fabric  HSN 5208   ₹40,000
Polyester      HSN 5512   ₹30,000

Subtotal:       ₹70,000.00
IGST @ 12%:     ₹8,400.00
Grand Total:    ₹78,400.00
"""

CGST_SGST_INVOICE_TEXT = """
TAX INVOICE
Raj Electronics
GSTIN: 07AADCR1234P1ZX
New Delhi

Invoice No: REL/2526/0089     Date: 01/06/2026
Customer: Priya Retailers
GSTIN: 07ZZZZR9999Q1ZA
Place of Supply: Delhi (07)

LED TV 43 inch  HSN 85287200   ₹25,000
Smart Speaker   HSN 85182900   ₹3,000

Subtotal:       ₹28,000.00
CGST @ 9%:      ₹2,520.00
SGST @ 9%:      ₹2,520.00
Grand Total:    ₹33,040.00
"""

HINDI_INVOICE_TEXT = """
कर चालान / TAX INVOICE
विक्रेता: Kapoor Kirana Store
GSTIN: 09AABCK7890M1ZT
दिनांक: 20/05/2026
बिल नंबर: KKS/001/2526

खरीदार: Local Shop
GSTIN: 09AABCL1111N1ZS

माल का विवरण:
चाय पत्ती HSN 0902     ₹5,000
आटा       HSN 1101     ₹3,200

Subtotal:     ₹8,200.00
CGST @ 2.5%:  ₹205.00
SGST @ 2.5%:  ₹205.00
कुल राशि:    ₹8,610.00
"""

MINIMAL_INVOICE_TEXT = """
BILL
ABC Traders
123 Main Street
Some description here
No amounts, no dates, no GSTIN
"""

LAKH_AMOUNTS_TEXT = """
TAX INVOICE
Big Wholesale Ltd.
GSTIN: 27AABCB1234X1Z5
Mumbai, Maharashtra

Invoice No: BW/2026/9999   Date: 10/06/2026
Place of Supply: Karnataka (29)

Industrial Machinery HSN 84798999  ₹2,50,000

Subtotal:       ₹2,50,000.00
IGST @ 18%:     ₹45,000.00
Grand Total:    ₹2,95,000.00
"""


# ---------------------------------------------------------------------------
# Basic init tests
# ---------------------------------------------------------------------------

class TestInvoiceExtractorInit:
    def test_mock_mode_auto_without_credentials(self):
        e = InvoiceExtractor()
        assert e._mock_mode is True

    def test_mock_mode_explicit_true(self):
        e = InvoiceExtractor(mock_mode=True)
        assert e._mock_mode is True

    def test_mock_mode_explicit_false_with_creds(self, tmp_path):
        fake_creds = tmp_path / "creds.json"
        fake_creds.write_text("{}")
        e = InvoiceExtractor(gcp_credentials_path=str(fake_creds), mock_mode=False)
        assert e._mock_mode is False

    def test_openai_key_stored(self):
        e = InvoiceExtractor(openai_api_key="sk-test-key")
        assert e.openai_api_key == "sk-test-key"

    def test_no_openai_key_defaults_empty(self):
        e = InvoiceExtractor(mock_mode=True)
        assert e.openai_api_key == ""


# ---------------------------------------------------------------------------
# extract_raw_text tests
# ---------------------------------------------------------------------------

class TestExtractRawText:
    def test_mock_returns_fixture_text(self, extractor):
        result = extractor.extract_raw_text("https://example.com/invoice.jpg")
        assert "Sharma Textiles" in result
        assert "08AABCU9603R1ZM" in result
        assert "IGST" in result

    def test_mock_returns_same_for_local_path(self, extractor):
        result = extractor.extract_raw_text("/tmp/some_invoice.jpg")
        assert len(result) > 100

    def test_mock_text_contains_hsn_codes(self, extractor):
        result = extractor.extract_raw_text("https://example.com/invoice.jpg")
        assert "5208" in result
        assert "5512" in result

    def test_mock_text_contains_gstin(self, extractor):
        result = extractor.extract_raw_text("any_source")
        import re
        gstins = re.findall(r"[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]", result)
        assert len(gstins) >= 1


# ---------------------------------------------------------------------------
# Heuristic parser tests (no LLM, no API keys)
# ---------------------------------------------------------------------------

class TestHeuristicParser:
    def test_igst_invoice_vendor_gstin(self, extractor):
        result = extractor._heuristic_parse(IGST_INVOICE_TEXT)
        assert result.vendor_gstin == "08AABCU9603R1ZM"

    def test_igst_invoice_buyer_gstin(self, extractor):
        result = extractor._heuristic_parse(IGST_INVOICE_TEXT)
        assert result.buyer_gstin == "24AADCP3456Q1ZR"

    def test_igst_invoice_total_amount(self, extractor):
        result = extractor._heuristic_parse(IGST_INVOICE_TEXT)
        assert result.total_amount == pytest.approx(78400.0)

    def test_igst_rate_and_amount(self, extractor):
        result = extractor._heuristic_parse(IGST_INVOICE_TEXT)
        assert result.tax.igst_rate == pytest.approx(12.0)
        assert result.tax.igst_amount == pytest.approx(8400.0)

    def test_igst_no_cgst_sgst(self, extractor):
        result = extractor._heuristic_parse(IGST_INVOICE_TEXT)
        assert result.tax.cgst_amount is None
        assert result.tax.sgst_amount is None

    def test_igst_total_tax_computed(self, extractor):
        result = extractor._heuristic_parse(IGST_INVOICE_TEXT)
        assert result.tax.total_tax_amount == pytest.approx(8400.0)

    def test_hsn_codes_extracted(self, extractor):
        result = extractor._heuristic_parse(IGST_INVOICE_TEXT)
        assert "5208" in result.hsn_codes
        assert "5512" in result.hsn_codes

    def test_invoice_number_extracted(self, extractor):
        result = extractor._heuristic_parse(IGST_INVOICE_TEXT)
        assert result.invoice_number is not None
        assert "001247" in result.invoice_number

    def test_invoice_date_normalised(self, extractor):
        result = extractor._heuristic_parse(IGST_INVOICE_TEXT)
        assert result.invoice_date == "2026-06-15"

    def test_subtotal_extracted(self, extractor):
        result = extractor._heuristic_parse(IGST_INVOICE_TEXT)
        assert result.subtotal_amount == pytest.approx(70000.0)

    def test_place_of_supply(self, extractor):
        result = extractor._heuristic_parse(IGST_INVOICE_TEXT)
        assert result.place_of_supply is not None
        assert "Gujarat" in result.place_of_supply

    def test_cgst_sgst_invoice(self, extractor):
        result = extractor._heuristic_parse(CGST_SGST_INVOICE_TEXT)
        assert result.tax.cgst_rate == pytest.approx(9.0)
        assert result.tax.cgst_amount == pytest.approx(2520.0)
        assert result.tax.sgst_rate == pytest.approx(9.0)
        assert result.tax.sgst_amount == pytest.approx(2520.0)
        assert result.tax.igst_amount is None

    def test_cgst_sgst_total_tax_summed(self, extractor):
        result = extractor._heuristic_parse(CGST_SGST_INVOICE_TEXT)
        assert result.tax.total_tax_amount == pytest.approx(5040.0)

    def test_hindi_invoice_gstin(self, extractor):
        result = extractor._heuristic_parse(HINDI_INVOICE_TEXT)
        assert result.vendor_gstin == "09AABCK7890M1ZT"

    def test_hindi_invoice_date(self, extractor):
        result = extractor._heuristic_parse(HINDI_INVOICE_TEXT)
        assert result.invoice_date == "2026-05-20"

    def test_hindi_invoice_total_amount(self, extractor):
        result = extractor._heuristic_parse(HINDI_INVOICE_TEXT)
        assert result.total_amount == pytest.approx(8610.0)

    def test_minimal_invoice_low_confidence(self, extractor):
        result = extractor._heuristic_parse(MINIMAL_INVOICE_TEXT)
        assert result.confidence == "low"

    def test_full_invoice_high_confidence(self, extractor):
        result = extractor._heuristic_parse(IGST_INVOICE_TEXT)
        assert result.confidence in ("high", "medium")

    def test_lakh_amount_parsed_correctly(self, extractor):
        result = extractor._heuristic_parse(LAKH_AMOUNTS_TEXT)
        assert result.total_amount == pytest.approx(295000.0)

    def test_hsn_deduplication(self, extractor):
        text_with_dupes = IGST_INVOICE_TEXT + "\nHSN 5208  ₹1,000"
        result = extractor._heuristic_parse(text_with_dupes)
        assert result.hsn_codes.count("5208") == 1

    def test_heuristic_always_has_warning(self, extractor):
        result = extractor._heuristic_parse(IGST_INVOICE_TEXT)
        assert len(result.parse_warnings) >= 1
        assert any("heuristic" in w.lower() or "openai" in w.lower()
                   for w in result.parse_warnings)

    def test_raw_ocr_text_preserved(self, extractor):
        result = extractor._heuristic_parse(IGST_INVOICE_TEXT)
        assert result.raw_ocr_text == IGST_INVOICE_TEXT


# ---------------------------------------------------------------------------
# JSON → InvoiceData parsing tests
# ---------------------------------------------------------------------------

class TestJsonToInvoiceData:
    def test_valid_json_parsed(self, extractor):
        raw = json.dumps({
            "vendor_name": "Test Co.",
            "vendor_gstin": "07AADCT1234P1ZX",
            "total_amount": 11800.0,
            "tax": {"igst_rate": 18.0, "igst_amount": 1800.0, "total_tax_amount": 1800.0},
            "hsn_codes": ["8471"],
            "confidence": "high",
            "parse_warnings": [],
        })
        result = extractor._json_to_invoice_data(raw)
        assert result.vendor_name == "Test Co."
        assert result.total_amount == 11800.0
        assert result.tax.igst_amount == 1800.0

    def test_invalid_json_returns_low_confidence(self, extractor):
        result = extractor._json_to_invoice_data("not valid json{{")
        assert result.confidence == "low"
        assert len(result.parse_warnings) >= 1

    def test_flat_tax_fields_nested(self, extractor):
        """LLM may return tax fields at root level instead of nested under 'tax'."""
        raw = json.dumps({
            "vendor_name": "ABC Ltd",
            "total_amount": 5900.0,
            "igst_rate": 18.0,
            "igst_amount": 900.0,
            "total_tax_amount": 900.0,
            "confidence": "medium",
            "parse_warnings": [],
        })
        result = extractor._json_to_invoice_data(raw)
        assert result.tax.igst_amount == 900.0

    def test_hsn_codes_as_string_converted_to_list(self, extractor):
        raw = json.dumps({
            "vendor_name": "XYZ",
            "hsn_codes": "8471",
            "confidence": "medium",
            "parse_warnings": [],
        })
        result = extractor._json_to_invoice_data(raw)
        assert isinstance(result.hsn_codes, list)
        assert "8471" in result.hsn_codes

    def test_parse_warnings_as_string_converted(self, extractor):
        raw = json.dumps({
            "vendor_name": "XYZ",
            "confidence": "low",
            "parse_warnings": "GSTIN not found",
        })
        result = extractor._json_to_invoice_data(raw)
        assert isinstance(result.parse_warnings, list)

    def test_empty_hsn_string_gives_empty_list(self, extractor):
        raw = json.dumps({
            "confidence": "low",
            "hsn_codes": "",
            "parse_warnings": [],
        })
        result = extractor._json_to_invoice_data(raw)
        assert result.hsn_codes == []


# ---------------------------------------------------------------------------
# GSTIN validator tests
# ---------------------------------------------------------------------------

class TestGSTINValidator:
    def test_valid_gstin_accepted(self):
        data = InvoiceData(vendor_gstin="08AABCU9603R1ZM")
        assert data.vendor_gstin == "08AABCU9603R1ZM"

    def test_valid_gstin_lowercase_normalised(self):
        data = InvoiceData(vendor_gstin="08aabcu9603r1zm")
        assert data.vendor_gstin == "08AABCU9603R1ZM"

    def test_invalid_gstin_still_stored(self):
        data = InvoiceData(vendor_gstin="INVALID123")
        assert data.vendor_gstin == "INVALID123"

    def test_none_gstin_accepted(self):
        data = InvoiceData(vendor_gstin=None)
        assert data.vendor_gstin is None

    def test_gstin_spaces_stripped(self):
        data = InvoiceData(vendor_gstin="  08AABCU9603R1ZM  ")
        assert data.vendor_gstin == "08AABCU9603R1ZM"


# ---------------------------------------------------------------------------
# Full pipeline tests (extract_raw_text + heuristic)
# ---------------------------------------------------------------------------

class TestFullPipeline:
    def test_extract_returns_invoice_data(self, extractor):
        result = extractor.extract("https://example.com/invoice.jpg")
        assert isinstance(result, InvoiceData)

    def test_extract_populates_raw_ocr_text(self, extractor):
        result = extractor.extract("https://example.com/invoice.jpg")
        assert result.raw_ocr_text is not None
        assert len(result.raw_ocr_text) > 100

    def test_extract_vendor_gstin_from_mock(self, extractor):
        result = extractor.extract("https://example.com/invoice.jpg")
        assert result.vendor_gstin == "08AABCU9603R1ZM"

    def test_extract_total_amount_from_mock(self, extractor):
        result = extractor.extract("https://example.com/invoice.jpg")
        assert result.total_amount == pytest.approx(78400.0)

    def test_extract_hsn_codes_from_mock(self, extractor):
        result = extractor.extract("https://example.com/invoice.jpg")
        assert "5208" in result.hsn_codes
        assert "5512" in result.hsn_codes

    def test_extract_invoice_date_normalised(self, extractor):
        result = extractor.extract("https://example.com/invoice.jpg")
        assert result.invoice_date == "2026-06-15"

    def test_json_serialisable(self, extractor):
        result = extractor.extract("https://example.com/invoice.jpg")
        dumped = result.model_dump_json()
        parsed = json.loads(dumped)
        assert "vendor_gstin" in parsed
        assert "tax" in parsed
        assert isinstance(parsed["hsn_codes"], list)


# ---------------------------------------------------------------------------
# LLM prompt engineering quality tests
# ---------------------------------------------------------------------------

class TestPromptEngineering:
    def test_system_prompt_mentions_hindi(self):
        assert "HINDI" in LLM_SYSTEM_PROMPT.upper() or "Hindi" in LLM_SYSTEM_PROMPT

    def test_system_prompt_mentions_hinglish(self):
        assert "Hinglish" in LLM_SYSTEM_PROMPT or "HINGLISH" in LLM_SYSTEM_PROMPT.upper()

    def test_system_prompt_mentions_gstin(self):
        assert "GSTIN" in LLM_SYSTEM_PROMPT

    def test_system_prompt_mentions_hsn(self):
        assert "HSN" in LLM_SYSTEM_PROMPT

    def test_system_prompt_mentions_igst(self):
        assert "IGST" in LLM_SYSTEM_PROMPT

    def test_system_prompt_mentions_cgst_sgst(self):
        assert "CGST" in LLM_SYSTEM_PROMPT
        assert "SGST" in LLM_SYSTEM_PROMPT

    def test_system_prompt_mentions_lakh_format(self):
        assert "lakh" in LLM_SYSTEM_PROMPT.lower() or "1,00,000" in LLM_SYSTEM_PROMPT

    def test_system_prompt_mentions_date_normalisation(self):
        assert "DD/MM/YYYY" in LLM_SYSTEM_PROMPT or "YYYY-MM-DD" in LLM_SYSTEM_PROMPT

    def test_system_prompt_requests_json_only(self):
        assert "JSON" in LLM_SYSTEM_PROMPT

    def test_gstin_state_codes_populated(self):
        assert len(GSTIN_STATE_CODES) >= 30
        assert GSTIN_STATE_CODES["07"] == "Delhi"
        assert GSTIN_STATE_CODES["27"] == "Maharashtra"
        assert GSTIN_STATE_CODES["33"] == "Tamil Nadu"


# ---------------------------------------------------------------------------
# TaxBreakdown model tests
# ---------------------------------------------------------------------------

class TestTaxBreakdown:
    def test_default_tax_breakdown_all_none(self):
        t = TaxBreakdown()
        assert t.cgst_rate is None
        assert t.sgst_rate is None
        assert t.igst_rate is None
        assert t.cess_amount is None
        assert t.total_tax_amount is None

    def test_tax_breakdown_with_values(self):
        t = TaxBreakdown(cgst_rate=9.0, cgst_amount=900.0, sgst_rate=9.0, sgst_amount=900.0)
        assert t.cgst_rate == 9.0
        assert t.total_tax_amount is None

    def test_invoice_data_default_tax(self):
        inv = InvoiceData()
        assert isinstance(inv.tax, TaxBreakdown)
        assert inv.hsn_codes == []
        assert inv.parse_warnings == []
        assert inv.confidence == "low"

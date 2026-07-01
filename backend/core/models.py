"""Shared Pydantic models."""
from typing import List, Optional
from pydantic import BaseModel


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


class InviteClientReq(BaseModel):
    name: str
    business_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    gstin: Optional[str] = None
    city: Optional[str] = None


class MarkFiledReq(BaseModel):
    vendor_id: str
    period: str
    return_type: str  # "gstr1" | "gstr3b"
    status: str = "filed"
    ack_number: Optional[str] = None


class FileReturnReq(BaseModel):
    """Vendor-initiated filing via GSP."""
    return_type: str  # gstr1 | gstr3b
    period: str  # YYYY-MM


class FileOtpReq(BaseModel):
    filing_id: str
    otp: str

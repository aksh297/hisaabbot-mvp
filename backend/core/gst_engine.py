"""GSTR-1 / GSTR-3B calculation engine and deadline utilities."""
from datetime import datetime, timezone
from typing import List, Optional


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
    next_month = m + 1 if m < 12 else 1
    year_of_next = y if m < 12 else y + 1
    dates = []
    for return_type, day in [("GSTR-1", 11), ("GSTR-3B", 20)]:
        due = datetime(year_of_next, next_month, day, 23, 59, tzinfo=timezone.utc)
        if due < today:
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

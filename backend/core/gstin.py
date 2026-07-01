"""GSTIN validation utility."""
import re

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
    if not gstin:
        return {"valid": False, "error": "GSTIN required"}
    g = gstin.strip().upper()
    if not GSTIN_REGEX.match(g):
        return {"valid": False, "gstin": g, "error": "Invalid GSTIN format"}
    state = STATE_CODES.get(g[:2], "Unknown")
    pan = g[2:12]
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

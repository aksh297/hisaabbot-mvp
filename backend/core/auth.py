"""Password hashing, JWT tokens, current-user dependency."""
from datetime import datetime, timezone, timedelta
from typing import Optional

import bcrypt
import jwt
from bson import ObjectId
from fastapi import HTTPException, Request

from .config import JWT_SECRET, JWT_ALGO
from .db import db


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


def user_public(u: dict) -> dict:
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


def ensure_ca(user: dict):
    if user.get("role") != "ca":
        raise HTTPException(status_code=403, detail="Only CA accounts can access this")

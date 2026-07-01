"""Auth router: register, login, logout, me."""
from datetime import datetime, timezone

from fastapi import APIRouter, Response, Depends, HTTPException

from core.auth import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    user_public, get_current_user,
)
from core.db import db
from core.gstin import validate_gstin
from core.models import RegisterReq, LoginReq

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
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
    return {"user": user_public(doc), "access_token": access}


@router.post("/login")
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
    return {"user": user_public(user), "access_token": access}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}


@router.get("/me")
async def me(current=Depends(get_current_user)):
    return user_public(current)

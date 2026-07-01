"""HisaabBot backend — slim entry that mounts all routers.

Structure:
  core/       — config, db, auth, models, LLM, GSTIN, GST engine, Gupshup, GSP, seed
  routers/    — auth, invoices, voice, upi, gst, chat, ca, whatsapp
"""
from datetime import datetime, timezone

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core import seed as seed_module
from core.config import UPLOAD_DIR, ADMIN_EMAIL, DEMO_EMAIL
from core.db import create_indexes
from routers import auth as auth_router
from routers import ca as ca_router
from routers import chat as chat_router
from routers import gst as gst_router
from routers import invoices as invoices_router
from routers import upi as upi_router
from routers import voice as voice_router
from routers import whatsapp as whatsapp_router

app = FastAPI(title="HisaabBot API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded images so we can preview them via public URL
app.mount("/api/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

api = APIRouter(prefix="/api")


@api.get("/")
async def root():
    return {"ok": True, "service": "HisaabBot API", "version": "2.0.0"}


@api.get("/health")
async def health():
    return {"status": "healthy", "time": datetime.now(timezone.utc).isoformat()}


# Mount feature routers
api.include_router(auth_router.router)
api.include_router(invoices_router.router)
api.include_router(voice_router.router)
api.include_router(upi_router.router)
api.include_router(gst_router.router)
api.include_router(chat_router.router)
api.include_router(ca_router.router)
api.include_router(whatsapp_router.router)

app.include_router(api)


@app.on_event("startup")
async def startup():
    await create_indexes()
    await seed_module.run_all()
    print(f"[startup] HisaabBot ready. Admin={ADMIN_EMAIL}, Demo={DEMO_EMAIL}")

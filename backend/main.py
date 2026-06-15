"""
FastAPI Main Application — AI Customer Support Agent
"""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import settings
from api.chat import router as chat_router
from api.voice import router as voice_router
from api.admin import router as admin_router
from api.auth  import router as auth_router

# ─── App Setup ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description="AI-powered e-commerce customer support agent with refund processing.",
)

ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(voice_router)
app.include_router(admin_router)

# ─── Static Frontend ─────────────────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    @app.get("/admin")
    async def serve_admin():
        return FileResponse(str(FRONTEND_DIR / "admin.html"))
else:
    @app.get("/")
    async def root():
        return {
            "message": "AI Customer Support Agent API",
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "frontend": "Frontend directory not found. Place frontend/ next to backend/.",
        }


# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": settings.OPENAI_MODEL,
        "api_key_set": bool(settings.OPENAI_API_KEY),
    }


# ─── Entry Point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        ws_ping_interval=20,
        ws_ping_timeout=30,
    )

"""
FastAPI Main Application — AI Customer Support Agent
"""
import os
import sys
import traceback
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from ws_debug_middleware import WSDebugMiddleware
from config import settings

# ─── App Setup ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description="AI-powered e-commerce customer support agent with refund processing.",
)

app.add_middleware(WSDebugMiddleware)
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
# IMPORTANT: chat.py imports agent.graph, which imports langgraph/langchain.
# If those packages are missing or fail to import, the route never registers,
# and every WebSocket upgrade to /ws/chat/{id} or /ws/admin returns
# a generic 400 Bad Request with no useful log message.
#
# We import each router defensively so the app still starts, surfaces the
# real traceback in the startup logs, and returns a clear JSON error from
# the affected endpoints instead of a silent 400 on every connection.

_startup_errors: dict[str, str] = {}


def _safe_import_router(module_path: str, router_attr: str = "router"):
    try:
        module = __import__(module_path, fromlist=[router_attr])
        return getattr(module, router_attr)
    except Exception:
        tb = traceback.format_exc()
        _startup_errors[module_path] = tb
        print(f"\n{'=' * 70}")
        print(f"[STARTUP ERROR] Failed to import '{module_path}' router")
        print(f"{'=' * 70}")
        print(tb)
        print(f"{'=' * 70}\n")
        return None


auth_router = _safe_import_router("api.auth")
chat_router = _safe_import_router("api.chat")
voice_router = _safe_import_router("api.voice")
admin_router = _safe_import_router("api.admin")

for _router, _name in [
    (auth_router, "auth"),
    (chat_router, "chat"),
    (voice_router, "voice"),
    (admin_router, "admin"),
]:
    if _router is not None:
        app.include_router(_router)
    else:
        print(f"[STARTUP] Skipping '{_name}' router due to import error — "
              f"its endpoints/WebSockets will NOT be available.")

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
        "status": "ok" if not _startup_errors else "degraded",
        "model": settings.OPENAI_MODEL,
        "api_key_set": bool(settings.OPENAI_API_KEY),
        "startup_errors": list(_startup_errors.keys()) or None,
    }


# ─── Startup error detail (for debugging only) ────────────────────────────────
@app.get("/debug/startup-errors")
async def debug_startup_errors():
    """
    Returns full tracebacks for any router that failed to import.
    If 'api.chat' shows up here with a langgraph/langchain ImportError,
    that's why /ws/chat and /ws/admin return 400 on every connection —
    the routes were never registered.

    Fix: run `pip install -r requirements.txt --break-system-packages`
    (or inside your venv without the flag) and restart the server.
    """
    if not _startup_errors:
        return {"status": "ok", "message": "All routers imported successfully."}
    return JSONResponse(status_code=500, content=_startup_errors)


# ─── Entry Point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    if _startup_errors:
        print("\n" + "!" * 70)
        print("WARNING: One or more routers failed to import.")
        print("The following endpoints/WebSockets are UNAVAILABLE:")
        for mod in _startup_errors:
            print(f"  - {mod}")
        print("See /debug/startup-errors for full tracebacks once the server starts.")
        print("!" * 70 + "\n")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        ws_ping_interval=20,
        ws_ping_timeout=30,
    )
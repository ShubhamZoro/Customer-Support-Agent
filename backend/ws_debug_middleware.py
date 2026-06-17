"""
ws_debug_middleware.py — Temporary diagnostic middleware.

Add this to main.py to log the exact path, query string, and headers
of every WebSocket connection attempt BEFORE Starlette's router rejects it.

This is the only way to see what's actually being requested when you get
a 400 Bad Request that never reaches your @router.websocket handler —
those 400s happen at the routing layer (path doesn't match any route),
not inside chat_websocket() or admin_websocket().

USAGE in main.py (add near the top, after `app = FastAPI(...)`):

    from ws_debug_middleware import WSDebugMiddleware
    app.add_middleware(WSDebugMiddleware)

Remove once the issue is identified.
"""
from starlette.types import ASGIApp, Receive, Scope, Send


class WSDebugMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "websocket":
            path = scope.get("path", "")
            query = scope.get("query_string", b"").decode()
            headers = dict(scope.get("headers", []))
            origin = headers.get(b"origin", b"").decode()
            print(
                f"\n[WS DEBUG] Incoming WebSocket connection:\n"
                f"  path        : {path!r}\n"
                f"  query       : {query!r}\n"
                f"  origin      : {origin!r}\n"
                f"  full target : ws://...{path}?{query}\n"
            )
        await self.app(scope, receive, send)
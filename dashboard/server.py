"""
MAD-CAT dashboard server (FastAPI + Server-Sent Events).

  POST /ingest   <- structured events from event_emitter.DashboardHandler
  GET  /events   -> SSE stream to the browser (one direction, hence SSE not WS)
  GET  /         -> serves static/index.html
  GET  /health   -> liveness + subscriber count
  POST /reset    -> clear buffer + tell panels to reset (handy after restore_data.py)

Run (from repo root):
  uvicorn dashboard.server:app --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="MAD-CAT Dashboard")

_subscribers: "set[asyncio.Queue]" = set()
_recent: "list[dict]" = []          # small replay buffer for late-joining panels
_RECENT_MAX = 200

_STATIC = Path(__file__).parent / "static"
_INDEX = _STATIC / "index.html"

# Serve the front-end assets (css/js) as static files.
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


async def _broadcast(event: dict) -> None:
    # Control signals (e.g. reset) are transient; only telemetry is replayed to
    # late-joining panels.
    if event.get("type") != "control":
        _recent.append(event)
        if len(_recent) > _RECENT_MAX:
            del _recent[0]
    for q in list(_subscribers):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass  # a stuck client must not stall the others


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


@app.post("/ingest")
async def ingest(request: Request):
    try:
        event = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)
    if not isinstance(event, dict):
        return JSONResponse({"ok": False, "error": "expected a json object"}, status_code=400)
    await _broadcast(event)
    return {"ok": True}


@app.get("/events")
async def events(replay: int = 1):
    q: asyncio.Queue = asyncio.Queue(maxsize=1000)
    _subscribers.add(q)

    async def gen():
        # Do NOT poll request.is_disconnected() here: StreamingResponse runs its
        # own disconnect watcher on the same receive channel. On real client
        # disconnect this generator is cancelled and the finally below runs.
        try:
            # Get bytes on the wire immediately and hint the reconnect backoff,
            # then ping every 3s. uvicorn's default --timeout-keep-alive is 5s,
            # so anything slower than that lets the idle connection get closed
            # before the first ping (which showed up as "reconnecting").
            yield "retry: 3000\n\n"
            yield ": connected\n\n"
            if replay:
                for e in list(_recent):
                    yield _sse(e)
            while True:
                try:
                    e = await asyncio.wait_for(q.get(), timeout=3)
                    yield _sse(e)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            _subscribers.discard(q)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/reset")
async def reset():
    _recent.clear()
    await _broadcast({"type": "control", "action": "reset"})
    return {"ok": True}


@app.get("/health")
async def health():
    return {"ok": True, "subscribers": len(_subscribers), "buffered": len(_recent)}


@app.get("/", response_class=HTMLResponse)
async def index():
    if _INDEX.exists():
        return HTMLResponse(_INDEX.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>static/index.html not found next to server.py</h1>", status_code=500)
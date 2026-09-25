# MAD-CAT Dashboard

The attackers' existing logger -> structured JSON events -> FastAPI ingest -> SSE -> browser panel that shows attack progression in real time. Attacker corruption logic is untouched.

```
MAD-CAT terminal --(logging.Handler)--> POST /ingest --> SSE /events --> panel
```

## Files
- `event_emitter.py`: `logging.Handler` that turns log lines into events and POSTs them (stdlib only, non-blocking).
- `server.py`: FastAPI endpoints for `POST /ingest`, `GET /events` (SSE), `GET /` (panel), `GET /health`, `POST /reset`.
- `index.html`: Status dashboard with live event stream, served at `/`.
- `run_with_dashboard.py`: Optional wrapper launcher (Mode B).

## Installation
```
pip install fastapi "uvicorn[standard]"
```

## Wire the emitter - pick one

**Mode A (recommended, 2 lines).** In `mad_cat.py`'s main, *after* its own
logging is configured and before the attack runs:
```python
from dashboard.event_emitter import attach_dashboard_logging
attach_dashboard_logging()   # attaches to the root logger; captures every attacker's self.logger
```

**Mode B (zero edits).** Launch through the wrapper instead of calling
`mad_cat.py` directly:
```python
python3 dashboard/run_with_dashboard.py -c list.csv --yes
```
Mode B relies on the attacker loggers propagating to the root logger (the
default). If nothing shows up in the event stream, the loggers don't propagate - 
use Mode A.

## Run it (order matters for a clean demo)
```
# 0. confirm the lab is seeded FIRST - expect 25 clean records, no -MEOW
python3 fetch_data.py

# 1. dashboard (terminal 1)
uvicorn dashboard.server:app --host 127.0.0.1 --port 8000
#    open http://127.0.0.1:8000  -> panel shows OPERATIONAL (green)

# 2. attack (terminal 2)               # Mode A:
python3 mad_cat.py -c list.csv --yes   #   panel flips ACTIVE (amber) -> CORRUPTED (red)
#                                      # Mode B: python3 dashboard/run_with_dashboard.py -c list.csv --yes

# 3. reset the lab, then the panel
python3 restore_data.py
#    click Reset on the panel (or: curl -X POST http://127.0.0.1:8000/reset)
```

The panel's **system** selector points the hero panel at any of the six DBs (default MongoDB). The **Event stream** shows raw events from the logger so `event_emitter.py`'s phase/service regexes can be tuned to the actual log output (see `_PHASE_PATTERNS` / `SERVICE_BY_KEYWORD`).

## Testing
Emitter classification/routing/count-extraction/noise-filtering and the server's ingest + SSE replay/live-push/reset paths are unit-tested. Live validation against the lab confirms whether real attacker log lines match the phase/service patterns.

## Future
Expand the dashboard with additional HIPAA overlays: PHI-at-risk counter, Security-Rule safeguard mapping, CIA-triad badge, Breach Notification clock.
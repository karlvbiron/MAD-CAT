"""
MAD-CAT event emitter.

Turns the attackers' existing ``self.logger.info(...)`` phase-transition lines
into structured JSON events and ships them to the dashboard's ``/ingest``
endpoint. Hooks the existing logger without modifying attacker code.

Design guarantees:
  * Corruption logic is never touched. This is a stdlib ``logging.Handler`` that
    you attach to a logger; the attackers keep logging exactly as they did.
  * Non-blocking. Events go onto an in-memory queue drained by a daemon thread.
    If the dashboard is down or slow the attack is never delayed and never
    crashes (every network error is swallowed).
  * Stdlib only on the attacker side (``urllib``) so nothing new is imported
    into the attack process.

Attach it one of two ways (see dashboard/README.md):
  A. two lines inside mad_cat.py's main, after its logging is configured; or
  B. the zero-edit launcher dashboard/run_with_dashboard.py.
"""
from __future__ import annotations


import atexit
import json
import logging
import os
import queue
import re
import threading
from datetime import datetime, timezone
from urllib import request as _urlrequest

DEFAULT_URL = os.environ.get("MADCAT_DASHBOARD_URL", "http://127.0.0.1:8000/ingest")

# ---------------------------------------------------------------------------
# Classification. All best-effort and easy to tighten once we see real log
# lines from a run - nothing downstream breaks if a guess is wrong; the event
# still flows through with phase="log" / service=None and shows in the raw feed.
# ---------------------------------------------------------------------------

# Fixed lab IPs -> canonical service names.
SERVICE_BY_IP = {
    "192.168.1.11": "mongodb",
    "192.168.1.12": "elasticsearch",
    "192.168.1.13": "cassandra",
    "192.168.1.14": "redis",
    "192.168.1.15": "couchdb",
    "192.168.1.16": "hadoop",
}
_IP_RE = re.compile(r"(192\.168\.1\.1[1-6])")

# Keyword fallbacks (case-insensitive substring on the message).
SERVICE_BY_KEYWORD = [
    ("mongo", "mongodb"),
    ("elastic", "elasticsearch"),
    ("cassandra", "cassandra"),
    ("redis", "redis"),
    ("couch", "couchdb"),
    ("hadoop", "hadoop"),
    ("hdfs", "hadoop"),
]

# Phase detection, ordered so the more specific / later-in-the-loop patterns
# win. The loop is: connect -> get_databases -> get_collections -> meow_data ->
# close. "meow" is checked first so a "Modified N documents" line classifies as
# corruption even though it also contains "documents".
_PHASE_PATTERNS = [
    ("meow",        re.compile(r"meow|-MEOW|modif|corrupt|append|overwrit", re.I)),
    ("close",       re.compile(r"clos|disconnect|finish|complete|\bdone\b", re.I)),
    # specific database lines first, so "Processing database: my_index" is not
    # mislabelled "collections" just because the value contains "index".
    ("databases",   re.compile(r"processing database|found \d+ database", re.I)),
    ("collections", re.compile(r"collection|\btable|keyspace|index|bucket", re.I)),
    ("databases",   re.compile(r"database|\bdbs?\b", re.I)),
    ("connect",     re.compile(r"connect", re.I)),
    ("start",       re.compile(r"start|begin|execut|attack", re.I)),
]

# Third-party loggers whose chatter we never want on the dashboard. Attacker
# confirmations come from the attacker's own logger, not these transports, so
# these are dropped outright. Kept deliberately tight: driver names that could
# collide with an attacker module (elasticsearch, cassandra, pymongo) are NOT
# listed, so a real attacker line is never dropped by accident. Those drivers
# log mostly at DEBUG and won't flood at INFO.
_NOISE_LOGGERS = {
    "urllib3", "asyncio", "httpx", "httpcore",
    "charset_normalizer", "werkzeug", "elastic_transport", "uvicorn",
}

_COUNT_RE = re.compile(
    r"\b(\d{1,9})\s+(?:record|document|doc|row|key|value|item|collection|file)s?\b",
    re.I,
)


def _extract_count(msg: str) -> int | None:
    # Only trust a number that is explicitly followed by a unit word, so a path
    # like "user15.json" or a port never gets read as a count.
    m = _COUNT_RE.search(msg)
    return int(m.group(1)) if m else None

# Per-thread memory of the service last connected to, so a bare "Modified 25
# documents" line inherits the service from the preceding "Connecting to
# 192.168.1.11" line on the same worker.
_ctx = threading.local()


def _classify_service(msg: str) -> str | None:
    m = _IP_RE.search(msg)
    if m and m.group(1) in SERVICE_BY_IP:
        return SERVICE_BY_IP[m.group(1)]
    low = msg.lower()
    for kw, svc in SERVICE_BY_KEYWORD:
        if kw in low:
            return svc
    return None


def _service_for(msg: str, phase: str) -> str | None:
    svc = _classify_service(msg)
    if svc:
        _ctx.service = svc
    else:
        svc = getattr(_ctx, "service", None)
    if phase == "close":
        _ctx.service = None
    return svc


def _classify_phase(msg: str) -> str:
    for phase, pat in _PHASE_PATTERNS:
        if pat.search(msg):
            return phase
    return "log"


def _should_emit(logger_name: str, phase: str) -> bool:
    # phase is accepted for future policy; driver loggers are dropped outright.
    root = logger_name.split(".", 1)[0]
    return root not in _NOISE_LOGGERS


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

class DashboardHandler(logging.Handler):
    def __init__(self, url: str = DEFAULT_URL, maxsize: int = 2000):
        super().__init__()
        self.url = url
        self._q: "queue.Queue[dict]" = queue.Queue(maxsize=maxsize)
        self._stop = threading.Event()
        self._worker = threading.Thread(
            target=self._run, name="madcat-dashboard-emitter", daemon=True
        )
        self._worker.start()
        atexit.register(self.close)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = record.getMessage()
            phase = _classify_phase(msg)
            if not _should_emit(record.name, phase):
                return
            event = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "service": _service_for(msg, phase),
                "phase": phase,
                "message": msg,
                "logger": record.name,
            }
            if phase == "meow":
                c = _extract_count(msg)
                if c is not None:
                    event["records_affected"] = c
            self._q.put_nowait(event)
        except queue.Full:
            pass  # drop rather than block the attack
        except Exception:  # a logging handler must never raise into caller
            pass

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                event = self._q.get(timeout=0.25)
            except queue.Empty:
                continue
            self._post(event)

    def _post(self, event: dict) -> None:
        try:
            data = json.dumps(event).encode("utf-8")
            req = _urlrequest.Request(
                self.url, data=data,
                headers={"Content-Type": "application/json"}, method="POST",
            )
            _urlrequest.urlopen(req, timeout=0.5).close()
        except Exception:
            pass  # dashboard down/slow: telemetry loss must never affect the run

    def close(self) -> None:
        self._stop.set()
        super().close()


def attach_dashboard_logging(
    url: str = DEFAULT_URL,
    level: int = logging.INFO,
    logger_name: str | None = None,
) -> DashboardHandler:
    """Attach a DashboardHandler. Default target is the root logger, so every
    attacker's propagated records are captured without knowing its logger name.
    Call this AFTER the attacker configures its own logging (Mode A) so nothing
    it prints to the console is suppressed."""
    logger = logging.getLogger(logger_name)  # None -> root
    if logger.level == logging.NOTSET or logger.level > level:
        logger.setLevel(level)
    handler = DashboardHandler(url=url)
    handler.setLevel(level)
    logger.addHandler(handler)
    return handler


if __name__ == "__main__":
    # Self-test: emit a fake attack sequence to the running dashboard so you can
    # watch the panel react without touching the lab.
    #   Terminal 1:  uvicorn dashboard.server:app --port 8000
    #   Terminal 2:  python3 dashboard/event_emitter.py
    import time

    attach_dashboard_logging()
    log = logging.getLogger("mad_cat.selftest")
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    sequence = [
        "Starting attack run over list.csv",
        "Connecting to 192.168.1.11:27017",
        "Getting databases on my_database",
        "Found collection my_table",
        "Modified 25 documents with -MEOW in my_database",
        "Closing connection to 192.168.1.11",
    ]
    for line in sequence:
        log.info(line)
        time.sleep(0.8)
    time.sleep(1.5)  # let the daemon thread drain
    print("self-test emitted", len(sequence), "lines ->", DEFAULT_URL)
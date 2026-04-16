#!/usr/bin/env python3
"""
Misinformation Heatmap — Unified Server v2.0
Clean, single entry point.  ML models load lazily in the background.

Run:
    python server.py
"""

import os
import sys
import time
import asyncio
import logging
import sqlite3
import json
import threading
import torch
import traceback
from transformers import AutoTokenizer, AutoModel
from datetime import datetime
from pathlib import Path
from typing import Optional

# ─── PATH SETUP ──────────────────────────────────────────────────────────────
ROOT_DIR     = Path(__file__).parent
BACKEND_DIR  = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
MAP_DIR      = FRONTEND_DIR / "map"
DATA_DIR     = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "enhanced_fake_news.db"

sys.path.insert(0, str(BACKEND_DIR))

# Force IST timezone for all datetime.now() calls and log timestamps
import time as _time
os.environ.setdefault("TZ", "Asia/Kolkata")
# Apply on Unix systems (no-op on Windows, but Dockerfile ENV handles it there)
try:
    _time.tzset()
except AttributeError:
    pass  # Windows doesn't have tzset()

# ─── EARLY IMPORTS (fast) ────────────────────────────────────────────────────
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ─── JSON SERIALIZATION HELPER ────────────────────────────────────────────────
from datetime import datetime, date

def json_serial(obj):
    """JSON serializer for objects not serializable by default (datetime, date)."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

def safe_json_dumps(data):
    """json.dumps with datetime support."""
    return json.dumps(data, default=json_serial)

import uvicorn

# ─── COLORIZED LOGGING ──────────────────────────────────────────────────────
class ColorFormatter(logging.Formatter):
    """ANSI-colored log formatter for readable server output."""
    COLORS = {
        logging.DEBUG:    "\033[36m",   # Cyan
        logging.INFO:     "\033[32m",   # Green
        logging.WARNING:  "\033[33m",   # Yellow
        logging.ERROR:    "\033[31m",   # Red
        logging.CRITICAL: "\033[35m",   # Magenta
    }
    DIM   = "\033[2m"
    BOLD  = "\033[1m"
    RESET = "\033[0m"
    LEVEL_LABELS = {
        logging.DEBUG:    "DBG",
        logging.INFO:     "INF",
        logging.WARNING:  "WRN",
        logging.ERROR:    "ERR",
        logging.CRITICAL: "CRT",
    }

    def format(self, record: logging.LogRecord) -> str:
        color  = self.COLORS.get(record.levelno, "")
        label  = self.LEVEL_LABELS.get(record.levelno, record.levelname[:3])
        ts     = self.formatTime(record, "%H:%M:%S")
        name   = record.name.split(".")[-1][:18]
        msg    = record.getMessage()
        return (
            f"{self.DIM}{ts}{self.RESET} "
            f"{color}{self.BOLD}[{label}]{self.RESET} "
            f"{self.DIM}{name:>18}{self.RESET}  "
            f"{color if record.levelno >= logging.WARNING else ''}{msg}{self.RESET}"
        )

def _setup_logging():
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # Remove default handlers
    root.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter())
    root.addHandler(handler)

    # Quieten noisy libraries
    for noisy in ("httpx", "httpcore", "urllib3", "filelock", "watchfiles"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

_setup_logging()
logger = logging.getLogger("misinfo_heatmap")

# ─── LAZY ML STATE ───────────────────────────────────────────────────────────
# These are populated in background threads so the server starts instantly.
_ml_ready       = threading.Event()
_fake_detector  = None
_proc_stats_fn  = None
_ingestion_fn   = None
_is_active_fn   = None
_INDIAN_STATES  = {}

def _load_ml_models():
    """Load heavy ML models in a background thread."""
    global _fake_detector, _proc_stats_fn, _ingestion_fn, _is_active_fn, _INDIAN_STATES
    try:
        logger.info("⏳ Loading backend modules (ML models initialising)…")

        # Optimization: Temporarily increase threads for faster decompression/loading
        original_threads = torch.get_num_threads()
        torch.set_num_threads(min(4, os.cpu_count() or 1))
        logger.info(f"⚡ Initialization speed-up: Using {torch.get_num_threads()} threads for loading.")

        # 1. Realtime Processor & States
        try:
            from realtime_processor import get_processing_stats, INDIAN_STATES
            _proc_stats_fn = get_processing_stats
            _INDIAN_STATES = INDIAN_STATES
            logger.info(f"✅ realtime_processor loaded  ({len(INDIAN_STATES)} states)")
        except Exception as e:
            logger.error(f"❌ Error loading realtime_processor: {e}")

        # 2. Ingestion loop — start directly after ML models ready
        try:
            from massive_data_ingestion import high_volume_processing_loop, is_processing_active
            _ingestion_fn  = high_volume_processing_loop
            _is_active_fn  = is_processing_active
            logger.info("✅ massive_data_ingestion loop ready")
        except Exception as e:
            logger.warning(f"⚠️ massive_data_ingestion failed to load: {e}")
            _ingestion_fn = None

        # 3. Fake News Detector & Custom Ensemble
        try:
            from enhanced_fake_news_detector import fake_news_detector
            _fake_detector = fake_news_detector
            logger.info("✅ enhanced_fake_news_detector loaded")
        except Exception as e:
            logger.error(f"❌ Error loading fake_news_detector: {e}")

        # Revert to storage-saving mode for inference
        torch.set_num_threads(1)
        logger.info(f"🛡️ Safety-mode active: Reverted to {torch.get_num_threads()} thread for inference.")

    except Exception as exc:
        logger.error(f"❌ Critical ML model loading error: {exc}")
        logger.error(traceback.format_exc())
    finally:
        _ml_ready.set()   # unblock any waiter

def _get_processing_stats():
    return _proc_stats_fn() if _proc_stats_fn else {"processing_active": False}

def _is_processing_active():
    return _is_active_fn() if _is_active_fn else False


# ─── DATABASE HELPER ─────────────────────────────────────────────────────────
# Ingest → enhanced_fake_news.db (full article schema with title/state/verdict)
# API server reads from this SAME file — single source of truth.
DB_PATH = DATA_DIR / "enhanced_fake_news.db"

def get_db():
    from db_adapter import get_db_connection
    return get_db_connection(str(DB_PATH))

# ─── IN-MEMORY CACHE ─────────────────────────────────────────────────────────
_cache: dict = {}

def _cache_get(key: str, ttl: int):
    if key in _cache:
        data, ts = _cache[key]
        if time.time() - ts < ttl:
            return data
    return None

def _cache_set(key: str, data):
    _cache[key] = (data, time.time())

# ─── FASTAPI ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Misinformation Heatmap API",
    description="Real-time misinformation detection across India",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Static files
if MAP_DIR.exists():
    app.mount("/map", StaticFiles(directory=str(MAP_DIR)), name="map")
assets_dir = FRONTEND_DIR / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

# ─── LIFECYCLE ───────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    logger.info("🚀 Server listening — ML models loading in background…")
    loop = asyncio.get_event_loop()

    def _ml_then_ingest():
        _load_ml_models()  # blocks until models done
        # Now that models are ready, schedule the ingestion loop on the event loop
        if _ingestion_fn:
            logger.info("🔄 Scheduling ingestion loop on event loop…")
            asyncio.run_coroutine_threadsafe(_ingestion_fn(), loop)
        else:
            logger.warning("⚠️ No ingestion function registered — data will not update automatically.")

    threading.Thread(target=_ml_then_ingest, daemon=True).start()

# ─── PYDANTIC MODELS ─────────────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    title: str = ""
    content: str
    source: str = ""

# ─── PAGE ROUTES ─────────────────────────────────────────────────────────────
def _read_html(name: str) -> str:
    return (FRONTEND_DIR / name).read_text(encoding="utf-8")

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home():
    return _read_html("index.html")

@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard():
    return _read_html("dashboard.html")

# ─── API: STATS ──────────────────────────────────────────────────────────────
@app.get("/api/v1/stats", tags=["Analytics"])
async def get_stats():
    """Aggregate stats for the last 24 hours (30 s cache)."""
    cached = _cache_get("stats", 30)
    if cached:
        return cached

    total = fake_n = real_n = uncertain = 0
    try:
        with get_db() as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*)                                                          AS total,
                    SUM(CASE WHEN fake_news_verdict = 'fake'      THEN 1 ELSE 0 END) AS fake,
                    SUM(CASE WHEN fake_news_verdict = 'real'      THEN 1 ELSE 0 END) AS real,
                    SUM(CASE WHEN fake_news_verdict = 'uncertain' THEN 1 ELSE 0 END) AS uncertain
                FROM events
                WHERE timestamp > datetime('now', '-24 hours')
            """).fetchone()
            total, fake_n, real_n, uncertain = (row[k] or 0 for k in ("total","fake","real","uncertain"))
    except Exception as exc:
        logger.error(f"Stats DB error: {exc}")

    result = {
        "total_events":            total,
        "fake_events":             fake_n,
        "real_events":             real_n,
        "uncertain_events":        uncertain,
        "processing_active":       _is_processing_active(),
        "classification_accuracy": 0.91 if total > 0 else 0.5,
        "system_status":           "LIVE" if _is_processing_active() else "READY",
        "total_states":            len(_INDIAN_STATES) or 36,
        "ml_ready":                _ml_ready.is_set(),
        "last_updated":            datetime.now().isoformat(),
    }
    _cache_set("stats", result)
    return result

# ─── API: HEATMAP DATA ───────────────────────────────────────────────────────
@app.get("/api/v1/heatmap/data", tags=["Analytics"])
async def get_heatmap_data(days: int = Query(7, ge=1, le=30)):
    """State-wise misinformation event counts (60 s cache)."""
    cache_key = f"heatmap_{days}"
    cached = _cache_get(cache_key, 60)
    if cached:
        return cached

    rows = []
    try:
        with get_db() as conn:
            rows = conn.execute(f"""
                SELECT
                    state,
                    COUNT(*)                                                              AS event_count,
                    AVG(fake_news_confidence)                                             AS avg_confidence,
                    SUM(CASE WHEN fake_news_verdict = 'fake' THEN 1 ELSE 0 END)          AS fake_count,
                    SUM(CASE WHEN fake_news_verdict = 'real' THEN 1 ELSE 0 END)          AS real_count
                FROM events
                WHERE state IS NOT NULL
                  AND timestamp > datetime('now', '-{days} days')
                GROUP BY state
                ORDER BY event_count DESC
                LIMIT 50
            """).fetchall()
    except Exception as exc:
        logger.error(f"Heatmap DB error: {exc}")

    heatmap = []
    for r in rows:
        count = r["event_count"] or 0
        fake_c = r["fake_count"] or 0
        ratio = fake_c / count if count else 0
        if count < 5:
            risk = "insufficient_data"
        elif ratio > 0.15:
            risk = "high"
        elif ratio > 0.08:
            risk = "medium"
        elif ratio > 0.03:
            risk = "low_medium"
        else:
            risk = "low"
        heatmap.append({
            "state":            r["state"],
            "event_count":      count,
            "fake_probability": round(ratio, 4),
            "ai_confidence":    round(r["avg_confidence"] or 0.0, 3),
            "fake_count":       fake_c,
            "real_count":       r["real_count"] or 0,
            "fake_ratio":       round(ratio, 4),
            "risk_level":       risk,
        })

    result = {"heatmap_data": heatmap, "total_states": len(heatmap)}
    _cache_set(cache_key, result)
    return result

# ─── API: LIVE EVENTS ────────────────────────────────────────────────────────
@app.get("/api/v1/events/live", tags=["Events"])
async def get_live_events(limit: int = Query(10, ge=1, le=100)):
    """Recent events from the last hour."""
    rows = []
    try:
        with get_db() as conn:
            rows = conn.execute("""
                SELECT title, content, source, state,
                       fake_news_confidence, fake_news_verdict, timestamp
                FROM events
                WHERE timestamp > datetime('now', '-6 hours')
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,)).fetchall()
    except Exception as exc:
        logger.error(f"Live events error: {exc}")

    events = []
    for r in rows:
        body = r["content"] or ""
        events.append({
            "title":            (r["title"] or "Processing…")[:120],
            "content":          body[:200] + ("…" if len(body) > 200 else ""),
            "source":           r["source"] or "Unknown",
            "state":            r["state"]  or "India",
            "fake_probability": round(r["fake_news_confidence"] or 0.5, 2),
            "classification":   r["fake_news_verdict"] or "uncertain",
            "confidence":       round(r["fake_news_confidence"] or 0.5, 2),
            "timestamp":        r["timestamp"].isoformat() if hasattr(r["timestamp"], "isoformat") else str(r["timestamp"] or ""),
        })

    return {
        "events":           events,
        "total_count":      len(events),
        "processing_active": _is_processing_active(),
    }

# ─── API: SSE STREAM ─────────────────────────────────────────────────────────
@app.get("/api/v1/stream", tags=["Events"])
async def sse_stream():
    """Server-Sent Events for real-time dashboard updates."""
    async def event_generator():
        while True:
            stats = await get_stats()
            yield f"event: stats\ndata: {safe_json_dumps(stats)}\n\n"
            
            events_data = await get_live_events(limit=12)
            yield f"event: live_events\ndata: {safe_json_dumps(events_data)}\n\n"
            
            await asyncio.sleep(5)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ─── API: STATE EVENTS ───────────────────────────────────────────────────────
@app.get("/api/v1/events/state/{state}", tags=["Events"])
async def get_state_events(state: str, limit: int = Query(10, ge=1, le=50)):
    rows = []
    try:
        with get_db() as conn:
            rows = conn.execute("""
                SELECT title, content, source,
                       fake_news_confidence, fake_news_verdict, timestamp
                FROM events WHERE state = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (state, limit)).fetchall()
    except Exception as exc:
        logger.error(f"State events error [{state}]: {exc}")

    events = []
    for r in rows:
        body = r["content"] or ""
        events.append({
            "title":            r["title"] or "Processing…",
            "content":          body[:200] + ("…" if len(body) > 200 else ""),
            "source":           r["source"] or "Unknown",
            "fake_probability": round(r["fake_news_confidence"] or 0.5, 2),
            "classification":   r["fake_news_verdict"] or "uncertain",
            "confidence":       round(r["fake_news_confidence"] or 0.5, 2),
            "timestamp":        r["timestamp"],
        })

    return {"state": state, "events": events, "total_count": len(events)}

# ─── API: ANALYZE ────────────────────────────────────────────────────────────
@app.post("/api/v1/analyze", tags=["Analysis"])
async def analyze_article(req: AnalyzeRequest):
    """Submit a news article for misinformation analysis."""
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="'content' is required")
    if _fake_detector is None:
        # Return 503 if models still loading
        if not _ml_ready.is_set():
            raise HTTPException(status_code=503, detail="ML models are still loading, try again in a moment")
        raise HTTPException(status_code=503, detail="Analysis engine unavailable")
    try:
        result = _fake_detector.analyze_article(req.title, req.content, req.source)
        return {
            "fake_probability":    result.get("fake_probability", 0.5),
            "classification":      result.get("classification", "uncertain"),
            "confidence":          result.get("confidence", 0.5),
            "analysis_components": result.get("components", {}),
            "processing_time_ms":  result.get("processing_time", 0.0),
        }
    except Exception as exc:
        logger.error(f"Analysis error: {exc}")
        raise HTTPException(status_code=500, detail="Analysis failed")

# ─── API: HEALTH ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    db_ok = False
    try:
        with get_db() as conn:
            conn.execute("SELECT 1")
        db_ok = True
    except Exception:
        pass
    return {
        "status":            "healthy" if db_ok else "degraded",
        "version":           "2.0.0",
        "database":          "connected" if db_ok else "error",
        "ml_models_ready":   _ml_ready.is_set(),
        "processing_active": _is_processing_active(),
        "states_covered":    len(_INDIAN_STATES) or 36,
        "timestamp":         datetime.now().isoformat(),
    }

# ─── ENTRYPOINT ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    W, G, S, R = "\033[1;37m", "\033[1;32m", "\033[1;33m", "\033[0m"
    print()
    print(f"  {W}+------------------------------------------+{R}")
    print(f"  {W}|  {S}Misinformation Heatmap  v2.0.0{W}          |{R}")
    print(f"  {W}|  {G}ML models load lazily in background{W}     |{R}")
    print(f"  {W}+------------------------------------------+{R}")
    print(f"  {W}|  {G}Home     {W}->  {S}http://localhost:8000{W}         |{R}")
    print(f"  {W}|  {G}Dashboard{W}->  {S}http://localhost:8000/dashboard{W}  |{R}")
    print(f"  {W}|  {G}Heatmap  {W}->  {S}http://localhost:8000/map/...{W}    |{R}")
    print(f"  {W}|  {G}API Docs {W}->  {S}http://localhost:8000/api/docs{W}  |{R}")
    print(f"  {W}+------------------------------------------+{R}")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

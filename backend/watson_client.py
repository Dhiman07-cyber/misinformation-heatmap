"""
GDELT Project Client — Zero-cost replacement for IBM Watson Discovery.

GDELT (Global Database of Events, Language, and Tone) is the world's largest
open-source realtime news database. It updates every 15 minutes, covers 65+
languages, and is completely free with no API keys or rate limits.

Instead of 30,000 Watson NLP units/month, we get unlimited real-time news
ingestion from 100+ global sources, all filtered for India-specific content.
"""

import logging
import time
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import requests

logger = logging.getLogger(__name__)

# ─── GDELT ENDPOINTS ──────────────────────────────────────────────────────────
# GDELT DOC 2.0 API — free, no auth, no rate limits
GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"

# GDELT GKG (Global Knowledge Graph) — pre-enriched with themes, tone, entities
GDELT_GKG_API = "https://api.gdeltproject.org/api/v2/gkg/gkg"

# Specific themes to filter for misinformation-relevant content
MISINFORMATION_THEMES = [
    "CRISISLEX_T10_CAUTION_AND_ADVICE",
    "HEALTH",
    "PROTEST",
    "ELECTION_FRAUD",
    "CONSPIRACY",
    "MEDICAL",
    "DISEASE",
    "VACCINATION",
    "DISASTER",
    "ENVIRONMENT",
]

# India-specific location filters
INDIA_SOURCECOUNTRY = "India"

# Cache TTL aligned to GDELT's 15-minute update cycle
CACHE_TTL_SECONDS = 900  # 15 minutes


class GDELTClient:
    """
    Zero-cost, unlimited real-time news ingestion using the GDELT Project API.
    
    Replaces IBM Watson Discovery with no NLP unit limits.
    Implements the same interface as WatsonDiscoveryClient so no downstream
    changes are needed in ingestion_manager.py.
    """

    def __init__(self):
        self.enabled = True  # Always enabled — no API key needed
        self._cache: Dict[str, Any] = {}
        self._cache_path = Path(__file__).parent.parent / "data" / "gdelt_cache.json"
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_fetch: float = 0.0
        self._load_disk_cache()

    # ── Public Interface (mirrors WatsonDiscoveryClient) ──────────────────────

    async def initialize(self) -> bool:
        """Always succeeds — GDELT needs no authentication."""
        logger.info("✅ GDELT Client ready (zero-cost, no API key needed).")
        return True

    async def ingest_and_enhance_content(self, events: List[Dict]) -> List[Dict]:
        """
        Enhance existing RSS events AND append new GDELT-sourced events.
        Drop-in replacement for watson_client's method.
        """
        gdelt_events = await self._fetch_gdelt_events()

        if gdelt_events:
            logger.info(f"📡 GDELT contributed {len(gdelt_events)} new India events.")
            events = events + gdelt_events
        else:
            logger.info("📡 GDELT: no new events this cycle (cache still valid).")

        return events

    # ── GDELT Fetching Logic ──────────────────────────────────────────────────

    async def _fetch_gdelt_events(self) -> List[Dict]:
        """
        Fetch recent India-related news from GDELT DOC API.
        Uses a 15-minute local cache to avoid redundant requests.
        """
        now = time.time()

        # Check in-memory cache first
        cached = self._cache.get("gdelt_india")
        if cached and (now - cached["fetched_at"]) < CACHE_TTL_SECONDS:
            age_mins = int((now - cached["fetched_at"]) / 60)
            logger.debug(f"GDELT cache hit (age: {age_mins}m). Skipping fetch.")
            return []  # Return empty so we don't re-process same events

        logger.info("🌐 Fetching fresh India news from GDELT Project...")

        try:
            events = await self._query_gdelt_doc_api()
            if not events:
                events = await self._query_gdelt_gkg_api()

            # Cache results
            self._cache["gdelt_india"] = {
                "events": [e["title"] for e in events],  # store titles for dedup
                "fetched_at": now,
                "count": len(events),
            }
            self._save_disk_cache()

            logger.info(f"✅ GDELT fetched {len(events)} India news events.")
            return events

        except Exception as exc:
            logger.error(f"❌ GDELT fetch failed: {exc}. RSS pipeline continues.")
            return []

    async def _query_gdelt_doc_api(self) -> List[Dict]:
        """Query GDELT DOC 2.0 API for India-related articles."""
        # GDELT query syntax: space = AND, parentheses ONLY around OR-groups
        # Run two queries to maximize coverage
        queries = [
            "India misinformation",
            "India fake news",
            "India protest",
            "India health rumor",
        ]

        all_articles: List[Dict] = []
        seen_urls: set = set()

        for q in queries:
            try:
                params = {
                    "query": q,
                    "mode": "artlist",
                    "maxrecords": "25",
                    "sort": "DateDesc",
                    "format": "json",
                }

                resp = requests.get(GDELT_DOC_API, params=params, timeout=12)
                if not resp.ok:
                    continue

                content_type = resp.headers.get("content-type", "")
                if "json" not in content_type:
                    logger.warning(f"GDELT [{q}] non-JSON: {resp.text[:120]}")
                    continue

                data = resp.json()
                for a in data.get("articles", []):
                    url = a.get("url", "")
                    if url not in seen_urls:
                        seen_urls.add(url)
                        if self._is_india_relevant(a):
                            all_articles.append(self._normalize_doc_article(a))

            except Exception as ex:
                logger.debug(f"GDELT sub-query [{q}] failed: {ex}")
                continue

        return all_articles

    async def _query_gdelt_gkg_api(self) -> List[Dict]:
        """
        Fallback: Query GDELT GKG API for India-sourced knowledge graph entries.
        Returns pre-enriched events with themes, tone, and entity info.
        """
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(minutes=30)

        params = {
            "query": "India",
            "mode": "artlist",
            "maxrecords": 50,
            "format": "json",
            "startdatetime": start_dt.strftime("%Y%m%d%H%M%S"),
            "enddatetime": end_dt.strftime("%Y%m%d%H%M%S"),
        }

        resp = requests.get(GDELT_GKG_API, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        articles = data.get("articles", [])
        return [self._normalize_doc_article(a) for a in articles if self._is_india_relevant(a)]

    # ── Normalization & Filtering ─────────────────────────────────────────────

    def _is_india_relevant(self, article: Dict) -> bool:
        """Check if the article is genuinely India-relevant."""
        title = (article.get("title") or "").lower()
        url = (article.get("url") or "").lower()
        seendate = article.get("seendate", "")

        # Must contain India-related keywords
        india_keywords = [
            "india", "indian", "modi", "delhi", "mumbai", "bangalore",
            "kolkata", "chennai", "hyderabad", "punjab", "kerala",
            "rajasthan", "gujarat", "maharashtra", "karnataka",
        ]
        if not any(kw in title or kw in url for kw in india_keywords):
            return False

        # Skip articles older than 3 hours to ensure real-time freshness
        if seendate:
            try:
                pub = datetime.strptime(seendate, "%Y%m%dT%H%M%SZ")
                if (datetime.utcnow() - pub).total_seconds() > 10800:
                    return False
            except Exception:
                pass

        return True

    def _normalize_doc_article(self, article: Dict) -> Dict:
        """Convert GDELT article format to our internal event format."""
        title = article.get("title", "")
        url = article.get("url", "")
        seendate = article.get("seendate", "")
        domain = article.get("domain", "")
        language = article.get("language", "English")

        # Parse timestamp
        ts = datetime.utcnow()
        if seendate:
            try:
                ts = datetime.strptime(seendate, "%Y%m%dT%H%M%SZ")
            except Exception:
                pass

        # Generate a stable ID based on URL
        event_id = hashlib.md5(url.encode()).hexdigest()[:16]

        # Tone from GDELT ranges -100 to +100; negative = negative tone
        tone = float(article.get("tone", 0) or 0)
        # Map tone to our virality_score concept: very negative news → higher virality
        virality_hint = max(0.1, min(1.0, (abs(tone) / 100.0) + 0.3))

        return {
            "event_id": f"gdelt_{event_id}",
            "source": f"GDELT:{domain}",
            "title": title,
            "content": title,  # GDELT doesn't provide full article text
            "url": url,
            "timestamp": ts,
            "reliability": 0.65,  # Neutral reliability for GDELT-sourced news
            "gdelt_enriched": True,
            "gdelt_tone": tone,
            "gdelt_language": language,
            "cloud_source": "GDELT",
            "virality_hint": virality_hint,
        }

    # ── Disk Cache ────────────────────────────────────────────────────────────

    def _load_disk_cache(self):
        """Load cache from disk to survive server restarts."""
        try:
            if self._cache_path.exists():
                with open(self._cache_path, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                logger.debug("✅ GDELT disk cache loaded.")
        except Exception as e:
            logger.warning(f"Could not load GDELT disk cache: {e}")
            self._cache = {}

    def _save_disk_cache(self):
        """Persist cache to disk."""
        try:
            with open(self._cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f)
        except Exception as e:
            logger.warning(f"Could not save GDELT disk cache: {e}")


# ── Singleton (same interface as the old WatsonDiscoveryClient singleton) ─────
cloud_ingestion_manager = GDELTClient()

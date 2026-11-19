from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import requests


ALLOWED_DOMAINS = {"eci.gov.in", "sansad.in", "loksabha.nic.in", "rajyasabha.nic.in"}


def _allowed(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").lower()
    return any(hostname == domain or hostname.endswith("." + domain) for domain in ALLOWED_DOMAINS)


def fetch_official_evidence(url: str, timeout: float = 8.0) -> dict[str, Any]:
    """Fetch a bounded public official page for an admin-controlled job.

    No arbitrary user URLs are accepted: callers must pass an allowlisted
    government domain, and only a small text excerpt is stored.
    """
    if not _allowed(url):
        raise ValueError("Only allowlisted public government domains are supported")
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "ELECTORaW-research/1.0 (+public-data; contact project maintainer)"})
    response.raise_for_status()
    text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>", " ", response.text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    excerpt = text[:5000]
    return {
        "source_url": url, "source_title": urlparse(url).netloc,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "evidence_excerpt": excerpt, "evidence_hash": hashlib.sha256(excerpt.encode()).hexdigest(),
        "verification_status": "unreviewed",
    }

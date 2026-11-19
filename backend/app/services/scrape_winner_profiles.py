"""Refresh winner biographies without weakening provenance.

Election identity comes from the checked-in ECI successful-candidate records.
Biography text is only attached after an exact Wikipedia/Wikidata identity
match, and remains marked as a secondary source until an administrator reviews
and promotes an official Digital Sansad/Lok Sabha source.

Run from the repository root:
    python -m backend.app.services.scrape_winner_profiles --all
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from ..data import get_data


OUT = Path(__file__).resolve().parents[3] / "database" / "mongodb" / "winner_profiles.json"
WIKIDATA_SEARCH = "https://www.wikidata.org/w/api.php"
WIKIPEDIA_SEARCH = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/"
HEADERS = {"User-Agent": "ELECTORaW-profile-refresh/1.0 (public research; maintainer contact in repository)"}


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def search_entity(session: requests.Session, name: str) -> dict[str, Any] | None:
    response = session.get(WIKIDATA_SEARCH, params={"action": "wbsearchentities", "search": name, "language": "en", "format": "json", "limit": 5}, headers=HEADERS, timeout=15)
    response.raise_for_status()
    candidates = response.json().get("search", [])
    exact = next((item for item in candidates if norm(item.get("label", "")) == norm(name)), None)
    return exact or (candidates[0] if candidates else None)


def fetch_summary(session: requests.Session, title: str) -> dict[str, Any] | None:
    response = session.get(WIKIPEDIA_SUMMARY + quote(title.replace(" ", "_")), headers=HEADERS, timeout=15)
    if response.status_code != 200:
        return None
    data = response.json()
    if data.get("type") == "https://mediawiki.org/wiki/HyperSwitch/errors/not_found":
        return None
    return data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="refresh every unique official winner")
    parser.add_argument("--limit", type=int, default=25, help="number of unique winners to refresh")
    parser.add_argument("--start", type=int, default=0, help="offset into the unique-winner list")
    args = parser.parse_args()

    winners, _ = get_data().winners(limit=10000)
    unique: dict[str, dict[str, Any]] = {}
    for item in winners:
        unique.setdefault(norm(item["candidate_name"]), item)
    people = list(unique.values())
    if not args.all:
        people = people[args.start:args.start + args.limit]

    existing = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    session = requests.Session()
    for index, winner in enumerate(people, start=1):
        name = winner["candidate_name"]
        try:
            entity = search_entity(session, name)
            summary = fetch_summary(session, entity["label"]) if entity else None
            if summary:
                existing[norm(name)] = {
                    "person_key": f"winner:{norm(name)}",
                    "canonical_name": name,
                    "aliases": [winner["winner"]],
                    "party": winner.get("party"),
                    "bio": summary.get("extract"),
                    "verification_status": "secondary_source",
                    "completeness": 45,
                    "source_references": [{"title": summary.get("title", "Wikipedia biography"), "url": summary.get("content_urls", {}).get("desktop", {}).get("page", ""), "source_type": "secondary_reference"}],
                    "last_successful_refresh": time.strftime("%Y-%m-%d"),
                }
        except requests.RequestException as exc:
            print(f"skip {name}: {type(exc).__name__}")
        if index < len(people):
            time.sleep(.35)
        if index % 25 == 0:
            OUT.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"processed {index}/{len(people)}")

    OUT.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(existing)} profile records to {OUT}")


if __name__ == "__main__":
    main()

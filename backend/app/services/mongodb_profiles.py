from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..config import settings
from ..data import _norm


SEED_PATH = Path(__file__).resolve().parents[3] / "database" / "mongodb" / "seed_profiles.json"
WINNER_PROFILES_PATH = Path(__file__).resolve().parents[3] / "database" / "mongodb" / "winner_profiles.json"


def seed_documents() -> list[dict[str, Any]]:
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def profile_documents() -> list[dict[str, Any]]:
    documents = {item["person_key"]: item for item in seed_documents()}
    if WINNER_PROFILES_PATH.exists():
        generated = json.loads(WINNER_PROFILES_PATH.read_text(encoding="utf-8"))
        for item in generated.values():
            # Curated official biographies always win over bulk secondary data.
            documents.setdefault(item["person_key"], item)
    return list(documents.values())


class ProfileStore:
    def __init__(self) -> None:
        self.client = None
        self.collection = None
        self._documents_cache: list[dict[str, Any]] | None = None
        try:
            from pymongo import MongoClient
            self.client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=700, connectTimeoutMS=700)
            self.client.admin.command("ping")
            self.collection = self.client[settings.mongodb_database]["candidate_profiles"]
            self.collection.create_index("person_key", unique=True)
            self.collection.create_index("aliases")
        except Exception:
            self.client = None
            self.collection = None

    @property
    def connected(self) -> bool:
        return self.collection is not None

    def get(self, candidate_name: str) -> dict[str, Any] | None:
        if self.collection is not None:
            if self._documents_cache is None:
                self._documents_cache = list(self.collection.find({}, {"_id": 0}))
            documents = self._documents_cache
        else:
            documents = profile_documents()
        target = _norm(candidate_name)
        for document in documents:
            values = [document.get("canonical_name", ""), *document.get("aliases", [])]
            if any(_norm(value) == target for value in values):
                document.pop("_id", None)
                return document
        return None

    def featured(self, limit: int = 3) -> list[dict[str, Any]]:
        if self.collection is not None:
            return list(self.collection.find({}, {"_id": 0}).sort("completeness", -1).limit(limit))
        return sorted(profile_documents(), key=lambda item: (item.get("verification_status") != "official_source", -item.get("completeness", 0)))[:limit]

    def seed(self) -> dict[str, Any]:
        if self.collection is None:
            return {"connected": False, "inserted": 0, "message": "MongoDB is not reachable"}
        from pymongo import UpdateOne
        operations = [UpdateOne({"person_key": item["person_key"]}, {"$set": item}, upsert=True) for item in profile_documents()]
        result = self.collection.bulk_write(operations, ordered=False)
        return {"connected": True, "inserted": result.upserted_count, "modified": result.modified_count, "collection": "candidate_profiles"}


@lru_cache(maxsize=1)
def get_profile_store() -> ProfileStore:
    return ProfileStore()

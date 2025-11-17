import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from pymongo import MongoClient
from pymongo.collection import Collection

DATABASE_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017/")
DATABASE_NAME = os.getenv("DATABASE_NAME", "appdb")

_client = MongoClient(DATABASE_URL)
db = _client[DATABASE_NAME]


def get_collection(name: str) -> Collection:
    return db[name]


def create_document(collection_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.utcnow()
    payload = {
        **data,
        "created_at": now,
        "updated_at": now,
    }
    col = get_collection(collection_name)
    result = col.insert_one(payload)
    payload["_id"] = result.inserted_id
    return payload


def get_documents(collection_name: str, filter_dict: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[Dict[str, Any]]:
    col = get_collection(collection_name)
    cursor = col.find(filter_dict or {}).limit(limit)
    return list(cursor)

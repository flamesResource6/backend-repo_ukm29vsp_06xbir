from datetime import datetime
from io import StringIO
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from database import db, get_collection
from schemas import MoodEntry

app = FastAPI(title="Mood Tracker API")

# CORS - allow all origins by default; in production, restrict
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/test")
def test_connection():
    # simple ping to verify database
    try:
        db.list_collection_names()
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


@app.post("/api/moods")
def upsert_mood(entry: MoodEntry):
    col = get_collection("moodentry")
    # upsert by date
    existing = col.find_one({"date": entry.date})
    payload = {"date": entry.date, "mood": entry.mood, "note": entry.note, "updated_at": datetime.utcnow()}
    if existing:
        col.update_one({"_id": existing["_id"]}, {"$set": payload})
    else:
        payload["created_at"] = datetime.utcnow()
        col.insert_one(payload)
    return {"ok": True}


@app.get("/api/moods")
def list_moods(start: Optional[str] = None, end: Optional[str] = None, limit: int = 365):
    col = get_collection("moodentry")
    q: Dict[str, Any] = {}
    if start or end:
        q["date"] = {}
        if start:
            q["date"]["$gte"] = start
        if end:
            q["date"]["$lte"] = end
    cursor = col.find(q).sort("date", 1).limit(max(1, min(limit, 365)))
    items: List[Dict[str, Any]] = []
    for doc in cursor:
        items.append({
            "date": doc.get("date"),
            "mood": doc.get("mood"),
            "note": doc.get("note"),
        })
    return {"items": items}


@app.get("/api/moods/export")
def export_csv():
    col = get_collection("moodentry")
    cursor = col.find({}).sort("date", 1)
    rows = ["date,mood,note"]
    for doc in cursor:
        d = doc.get("date", "")
        m = doc.get("mood", "")
        n = (doc.get("note") or "").replace("\n", " ").replace(",", ";")
        rows.append(f"{d},{m},{n}")
    data = "\n".join(rows)
    stream = StringIO(data)
    return StreamingResponse(stream, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=moods.csv"})

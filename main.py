import os
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import MoodEntry

app = FastAPI(title="Mood Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Mood Tracker Backend is running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


# -------- Mood Tracker Endpoints --------

class CreateMoodEntry(BaseModel):
    date: str
    mood: MoodEntry.model_fields['mood'].annotation  # Literal type reuse
    note: Optional[str] = None


@app.post("/api/moods")
def add_mood(entry: CreateMoodEntry):
    # Upsert by date: if an entry for the date exists, update it; else insert new
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    existing = db["moodentry"].find_one({"date": entry.date})
    data = {"date": entry.date, "mood": entry.mood, "note": entry.note}
    if existing:
        db["moodentry"].update_one({"_id": existing["_id"]}, {"$set": {**data, "updated_at": datetime.now(timezone.utc)}})
        return {"status": "updated", "id": str(existing["_id"]) }
    else:
        inserted_id = create_document("moodentry", data)
        return {"status": "created", "id": inserted_id}


@app.get("/api/moods")
def list_moods(start: Optional[str] = Query(None), end: Optional[str] = Query(None), limit: int = Query(365, ge=1, le=1000)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    filt = {}
    if start and end:
        filt["date"] = {"$gte": start, "$lte": end}
    elif start:
        filt["date"] = {"$gte": start}
    elif end:
        filt["date"] = {"$lte": end}

    docs = db["moodentry"].find(filt).sort("date", 1).limit(limit)
    result = []
    for d in docs:
        result.append({
            "id": str(d.get("_id")),
            "date": d.get("date"),
            "mood": d.get("mood"),
            "note": d.get("note"),
            "created_at": d.get("created_at"),
            "updated_at": d.get("updated_at"),
        })
    return {"items": result}


@app.get("/api/moods/export")
def export_moods():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    def generate_csv():
        yield "date,mood,note\n"
        for d in db["moodentry"].find().sort("date", 1):
            date = d.get("date", "")
            mood = d.get("mood", "")
            note = (d.get("note", "") or "").replace('\n', ' ').replace('"', "''")
            yield f"{date},{mood},\"{note}\"\n"

    return StreamingResponse(generate_csv(), media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=moods.csv"
    })


@app.delete("/api/moods/{entry_id}")
def delete_mood(entry_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        oid = ObjectId(entry_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    res = db["moodentry"].delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"status": "deleted"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .config import settings
from .pipeline import process_logs, INCIDENTS, get_incident, run_investigation

class TextPayload(BaseModel):
    text: str = Field(min_length=1)

app = FastAPI(title=settings.app_name, version="1.0.0",
              description="AI-assisted log anomaly detection and incident investigation")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name}

@app.post("/ingest/text")
def ingest_text(payload: TextPayload):
    return process_logs(payload.text)

@app.post("/ingest")
async def ingest_file(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".log", ".txt")):
        raise HTTPException(status_code=400, detail="Upload a .log or .txt file.")
    raw = await file.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB.")
    return process_logs(raw.decode("utf-8", errors="replace"))

@app.get("/incidents")
def list_incidents():
    return sorted(INCIDENTS.values(), key=lambda x: x.get("start_time") or "", reverse=True)

@app.get("/incidents/{incident_id}")
def incident_detail(incident_id: str):
    result = get_incident(incident_id)
    if not result:
        raise HTTPException(status_code=404, detail="Incident not found.")
    return result

@app.post("/investigate/{incident_id}")
def investigate_incident(incident_id: str):
    result = run_investigation(incident_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Incident not found.")
    return result

from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .config import settings
from .pipeline import process_logs, INCIDENTS, get_incident, run_investigation, knowledge_base
from . import storage

class TextPayload(BaseModel): text:str=Field(min_length=1)
class KnowledgePayload(BaseModel): source:str=Field(min_length=1); content:str=Field(min_length=1); source_type:str='runbook'
class FeedbackPayload(BaseModel): hypothesis:str=Field(min_length=1); verdict:str=Field(pattern='^(confirmed|rejected|inconclusive)$'); notes:str=''
class ResolutionPayload(BaseModel): resolution:str=''

@asynccontextmanager
async def lifespan(_app):
    storage.init_db()
    yield

app=FastAPI(title=settings.app_name,version='2.0.0',description='Context-aware AI log anomaly detection, RAG and causal incident investigation',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])

@app.get('/health')
def health(): return {'status':'ok','service':settings.app_name,'version':'2.0.0','incidents':len(storage.list_incidents())}

@app.post('/ingest/text')
def ingest_text(payload:TextPayload): return process_logs(payload.text)

@app.post('/ingest')
async def ingest_file(file:UploadFile=File(...)):
    if not file.filename.lower().endswith(('.log','.txt')):raise HTTPException(400,'Upload a .log or .txt file.')
    raw=await file.read()
    if len(raw)>10*1024*1024:raise HTTPException(413,'File exceeds 10 MB.')
    return process_logs(raw.decode('utf-8',errors='replace'))

@app.post('/knowledge/ingest')
def ingest_knowledge(payload:KnowledgePayload):
    return knowledge_base.add_document(payload.source,payload.content,payload.source_type)

@app.post('/knowledge/ingest-directory')
def ingest_knowledge_directory(path:str|None=None):
    if path and not Path(path).exists():raise HTTPException(404,'Directory does not exist.')
    return knowledge_base.ingest_directory(path)

@app.get('/knowledge/stats')
def knowledge_stats():
    rows=storage.list_knowledge(); return {'chunks':len(rows),'sources':len({r['source'] for r in rows}),
      'by_type':{t:sum(r['source_type']==t for r in rows) for t in {r['source_type'] for r in rows}}}

@app.get('/incidents')
def list_incidents(): return storage.list_incidents()

@app.get('/incidents/{incident_id}')
def incident_detail(incident_id:str):
    result=get_incident(incident_id)
    if not result:raise HTTPException(404,'Incident not found.')
    result['feedback']=storage.list_feedback(incident_id)
    return result

@app.post('/investigate/{incident_id}')
def investigate_incident(incident_id:str):
    result=run_investigation(incident_id)
    if result is None:raise HTTPException(404,'Incident not found.')
    return result

@app.post('/incidents/{incident_id}/feedback')
def incident_feedback(incident_id:str,payload:FeedbackPayload):
    if not get_incident(incident_id):raise HTTPException(404,'Incident not found.')
    feedback_id=storage.add_feedback(incident_id,payload.hypothesis,payload.verdict,payload.notes)
    return {'feedback_id':feedback_id,'incident_id':incident_id,'verdict':payload.verdict}

@app.get('/incidents/{incident_id}/feedback')
def get_feedback(incident_id:str):
    if not get_incident(incident_id):raise HTTPException(404,'Incident not found.')
    return storage.list_feedback(incident_id)

@app.post('/incidents/{incident_id}/resolution')
def resolve_incident(incident_id:str,payload:ResolutionPayload):
    incident=get_incident(incident_id)
    if not incident:raise HTTPException(404,'Incident not found.')
    knowledge_base.add_incident(incident,payload.resolution)
    return {'status':'stored','incident_id':incident_id,'resolution_indexed':True}

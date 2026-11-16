import os
os.environ['USE_SENTENCE_TRANSFORMERS']='false'
os.environ['DATA_DIR']='./test_data'
from fastapi.testclient import TestClient
from app.main import app

def test_health_endpoint():
    with TestClient(app) as client:
        response=client.get('/health')
        assert response.status_code==200
        assert response.json()['status']=='ok'

def test_ingest_text_endpoint():
    text='\n'.join([f'2026-01-01 10:00:{i:02d} INFO api: request completed' for i in range(10)]+
                   ['2026-01-01 10:01:00 ERROR database: connection pool exhausted'])
    with TestClient(app) as client:
        response=client.post('/ingest/text',json={'text':text})
        assert response.status_code==200
        assert response.json()['event_count']==11

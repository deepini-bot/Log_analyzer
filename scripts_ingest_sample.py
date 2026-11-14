from pathlib import Path
import requests
BASE='http://localhost:8000'
root=Path(__file__).parent
logs=root/'data'/'sample_logs'/'sample_incident.log'
with logs.open('rb') as handle:
    response=requests.post(BASE+'/ingest',files={'file':(logs.name,handle,'text/plain')},timeout=90)
response.raise_for_status(); print(response.json())
runbooks=root/'data'/'knowledge'
print(requests.post(BASE+'/knowledge/ingest-directory',timeout=90).json())

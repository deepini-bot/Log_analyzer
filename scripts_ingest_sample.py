from pathlib import Path
import requests
text = Path("data/sample_logs/sample_incident.log").read_text(encoding="utf-8")
response = requests.post("http://localhost:8000/ingest/text", json={"text": text}, timeout=90)
response.raise_for_status()
result = response.json()
print("Events:", result["event_count"], "Anomalies:", result["anomaly_count"])
for item in result["incidents"]:
    print(item["incident_id"], item["severity"], item["title"])

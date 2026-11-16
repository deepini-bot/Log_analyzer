from app.correlator import correlate_incidents
from app.embeddings import EmbeddingService

def test_cross_service_events_correlate_in_time():
    events=[
      {'timestamp':'2026-01-01T10:00:00','service':'database','level':'ERROR','message':'connection pool exhausted','template':'connection pool exhausted','is_anomaly':True},
      {'timestamp':'2026-01-01T10:00:10','service':'api-gateway','level':'ERROR','message':'upstream request timeout','template':'upstream request timeout','is_anomaly':True},
      {'timestamp':'2026-01-01T10:00:20','service':'worker','level':'ERROR','message':'job failed after retry timeout','template':'job failed after retry timeout','is_anomaly':True},
    ]
    incidents=correlate_incidents(events,EmbeddingService('',False))
    assert len(incidents)==1
    assert len(incidents[0]['services'])==3
    assert incidents[0]['root_candidate']=='connection pool exhausted'

def test_incident_title_uses_original_message_not_template():
    event={'timestamp':'2026-01-01T10:00:00','service':'api','level':'ERROR',
           'message':'Request 503 failed','template':'request <NUM> failed','is_anomaly':True}
    incident=correlate_incidents([event],EmbeddingService('',False))[0]
    assert incident['title'].endswith('Request 503 failed')
    assert '<NUM>' not in incident['title']

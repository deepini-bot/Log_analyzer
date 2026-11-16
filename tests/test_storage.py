import json
from app import storage

def test_feedback_roundtrip(tmp_path,monkeypatch):
    monkeypatch.setattr(storage,'DB_PATH',tmp_path/'test.db')
    storage.init_db()
    incident={'incident_id':'INC-TEST','title':'test','severity':'low','events':[]}
    storage.save_incident(incident)
    storage.add_feedback('INC-TEST','database issue','confirmed','checked metrics')
    assert storage.get_incident('INC-TEST')['title']=='test'
    assert storage.list_feedback('INC-TEST')[0]['verdict']=='confirmed'

def test_list_incidents_puts_missing_timestamps_last(tmp_path,monkeypatch):
    monkeypatch.setattr(storage,'DB_PATH',tmp_path/'test.db')
    storage.init_db()
    storage.save_incident({'incident_id':'INC-OLD','title':'old','severity':'medium','events':[]})
    storage.save_incident({'incident_id':'INC-NEW','title':'new','severity':'high',
                           'start_time':'2026-11-13T06:00:00','events':[]})

    incidents=storage.list_incidents()

    assert [incident['incident_id'] for incident in incidents] == ['INC-NEW','INC-OLD']

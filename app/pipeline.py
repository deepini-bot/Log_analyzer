from .config import settings
from .parser import parse_logs, assign_template_frequency
from .detector import detect_anomalies, detect_temporal_spikes
from .embeddings import EmbeddingService
from .correlator import correlate_incidents
from .knowledge import KnowledgeBase
from .investigator import investigate
from . import storage

embedding_service=EmbeddingService(settings.embedding_model,settings.use_sentence_transformers)
knowledge_base=KnowledgeBase(embedding_service)
# Rehydrate state on process restart.
INCIDENTS={x['incident_id']:x for x in storage.list_incidents()}

def process_logs(text):
    events=parse_logs(text)
    if not events:return {'event_count':0,'anomaly_count':0,'incidents':[],'events':[],'temporal_spikes':[]}
    assign_template_frequency(events); detect_anomalies(events); spikes=detect_temporal_spikes(events)
    incidents=correlate_incidents(events,embedding_service)
    for incident in incidents:
        INCIDENTS[incident['incident_id']]=incident
        storage.save_incident(incident)
        knowledge_base.add_incident(incident)
    return {'event_count':len(events),'anomaly_count':sum(e['is_anomaly'] for e in events),
            'temporal_spikes':spikes,'incidents':incidents,'events':events}

def get_incident(incident_id):
    return INCIDENTS.get(incident_id) or storage.get_incident(incident_id)

def run_investigation(incident_id):
    incident=get_incident(incident_id)
    if not incident:return None
    result=investigate(incident,knowledge_base)
    incident['investigation']=result; INCIDENTS[incident_id]=incident
    storage.save_investigation(incident_id,result)
    return result

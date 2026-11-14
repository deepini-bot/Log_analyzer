import json
import requests
from .config import settings
from .detector import parse_time

def _causal_analysis(incident, knowledge_base):
    events=sorted(incident.get('events',[]),key=lambda e:parse_time(e.get('timestamp')) or parse_time('9999-12-31T23:59:59'))
    query=incident.get('title','')+' '+' '.join(e.get('message','') for e in events)
    retrieved=knowledge_base.retrieve(query,top_k=5)
    evidence=[]
    for i,e in enumerate(events):
        evidence.append({'evidence_id':f'E{i+1}','timestamp':e.get('timestamp'),'service':e.get('service'),
                         'level':e.get('level'),'message':e.get('message'),'anomaly_score':e.get('anomaly_score',0)})
    db_terms=('connection refused','pool exhausted','database unavailable','database connection','failed to acquire database connection','db timeout','deadlock','too many connections')
    api_terms=('timeout','upstream','gateway','request failed','502','503','504')
    worker_terms=('consumer lag','worker failed','retry exhausted','queue timeout','job failed','message processing')
    db=[e for e in evidence if any(t in e['message'].lower() for t in db_terms)]
    api=[e for e in evidence if any(t in e['message'].lower() for t in api_terms)]
    workers=[e for e in evidence if any(t in e['message'].lower() for t in worker_terms)]
    causes=[]
    if db:
        support=[e['evidence_id'] for e in db[:4]]
        propagation=[e['evidence_id'] for e in (api+workers)[:6]]
        causes.append({'cause':'Database connectivity or connection-pool exhaustion may be the initiating failure',
          'confidence':'high' if api and workers else 'medium','confidence_score':0.82 if api and workers else 0.61,
          'supporting_evidence':support,'propagation_evidence':propagation,
          'reasoning':'Database symptoms occur before or alongside downstream API/worker symptoms. Validate database health and pool metrics.'})
    if api:
        causes.append({'cause':'Downstream latency may be propagating into API request timeouts','confidence':'medium',
          'confidence_score':0.58,'supporting_evidence':[e['evidence_id'] for e in api[:5]],
          'reasoning':'Timeout and upstream failure messages indicate request-path degradation.'})
    if workers:
        causes.append({'cause':'Worker backlog or message-consumer failures may be a downstream effect','confidence':'medium',
          'confidence_score':0.55,'supporting_evidence':[e['evidence_id'] for e in workers[:5]],
          'reasoning':'Worker/queue symptoms appear in the same incident window.'})
    if not causes:
        causes.append({'cause':'Insufficient evidence to isolate a root cause','confidence':'low','confidence_score':0.2,
          'supporting_evidence':[e['evidence_id'] for e in evidence[:5]],
          'reasoning':'No known dependency failure signature was found in the available log messages.'})
    sequence=[]
    for e in evidence:
        sequence.append({'timestamp':e['timestamp'],'service':e['service'],'event':e['message'],
                         'evidence_id':e['evidence_id']})
    return {'mode':'evidence_causal_rag','incident_summary':incident.get('summary'),
      'probable_causes':causes,'causal_sequence':sequence,'evidence':evidence,
      'historical_context':retrieved,'investigation_steps':[
       'Check database availability, connection-pool saturation, active sessions, locks and query latency at the first failure timestamp.',
       'Trace API requests to determine whether their latency aligns with database wait time.',
       'Inspect Kafka consumer lag, worker retries and queue depth after the API/database symptoms.',
       'Compare deployment, configuration and infrastructure changes immediately before the first failure.',
       'Confirm the initiating fault with metrics/traces before marking a hypothesis as the root cause.'],
      'limitations':['Log ordering and keyword signatures suggest causality but do not prove it.','Correlate with distributed traces, metrics and deployment events for confirmation.']}

def investigate(incident, knowledge_base):
    result=_causal_analysis(incident,knowledge_base)
    if settings.llm_base_url and settings.llm_api_key and settings.llm_model:
        prompt=('Review this structured incident investigation and improve clarity without adding unsupported facts. '
                'Return valid JSON. Keep evidence IDs, label all causes as hypotheses, and do not raise confidence without evidence.\n'+json.dumps(result,default=str))
        try:
            response=requests.post(settings.llm_base_url.rstrip('/')+'/chat/completions',
              headers={'Authorization':f'Bearer {settings.llm_api_key}'},
              json={'model':settings.llm_model,'temperature':0.1,
                'messages':[{'role':'system','content':'You are an evidence-grounded SRE investigator. Never invent evidence or claim certainty.'},
                            {'role':'user','content':prompt}]},timeout=60)
            response.raise_for_status(); answer=response.json()['choices'][0]['message']['content']
            try: parsed=json.loads(answer)
            except Exception: parsed={'llm_analysis':answer,'structured_baseline':result}
            result.update({'mode':'llm_rag_causal','llm_analysis':parsed})
        except Exception as exc: result['llm_status']=f'LLM unavailable; deterministic analysis retained ({type(exc).__name__}).'
    result['warning']='All root-cause findings are hypotheses. Engineer validation is required.'
    return result

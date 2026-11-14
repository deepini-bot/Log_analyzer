from collections import Counter, defaultdict
from datetime import datetime
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

LEVEL_WEIGHT = {'TRACE':0.0,'DEBUG':0.05,'INFO':0.1,'WARN':0.55,'ERROR':0.85,'FATAL':1.0,'CRITICAL':1.0}

def parse_time(value):
    try: return datetime.fromisoformat(value.replace(',', '.')) if value else None
    except Exception: return None

def build_features(events):
    by_service = defaultdict(list)
    for i,e in enumerate(events): by_service[e.get('service','unknown')].append((i,e))
    X = np.zeros((len(events), 9)); service_levels = {}
    for service, items in by_service.items():
        previous = None
        levels = [LEVEL_WEIGHT.get(e.get('level','INFO'),.1) for _,e in items]
        service_levels[service] = (float(np.mean(levels)), float(np.std(levels)))
        for i,e in items:
            ts=parse_time(e.get('timestamp')); delta=(ts-previous).total_seconds() if ts and previous else 0
            if ts: previous=ts
            msg=e.get('message',''); avg,std=service_levels[service]
            level=LEVEL_WEIGHT.get(e.get('level','INFO'),.1)
            X[i]=[level,min(len(msg),2000)/2000,1/max(e.get('template_frequency',1),1),
                  min(max(delta,0),3600)/3600,min(len(msg.split()),100)/100,
                  float(level>=.85),abs(level-avg)/(std+.15),
                  float(e.get('template_frequency',1)<=2),float(any(x in msg.lower() for x in ('timeout','refused','unavailable','deadlock','pool exhausted')))]
    return X

def detect_anomalies(events, contamination=.08):
    if not events: return events
    X=build_features(events)
    if len(events)<8:
        raw=X[:,0]*.35+X[:,6]*.25+X[:,7]*.2+X[:,8]*.2
        labels=raw>=max(.48,float(np.quantile(raw,.75)))
    else:
        Xs=StandardScaler().fit_transform(X)
        model=IsolationForest(n_estimators=180,contamination=min(max(contamination,.01),.25),random_state=42)
        model.fit(Xs); raw=-model.decision_function(Xs); labels=model.predict(Xs)==-1
    # Context score: rare templates, service-relative severity and dependency symptoms.
    contextual=np.clip(X[:,6]*.35+X[:,7]*.25+X[:,8]*.4,0,1)
    raw=np.asarray(raw,dtype=float); norm=(raw-raw.min())/(raw.max()-raw.min()+1e-9)
    scores=np.clip(.65*norm+.35*contextual,0,1)
    for i,e in enumerate(events):
        e['anomaly_score']=round(float(scores[i]),4)
        e['context_score']=round(float(contextual[i]),4)
        e['is_anomaly']=bool(labels[i] or scores[i]>=.72)
        reasons=[]
        if e.get('level') in ('ERROR','FATAL','CRITICAL'): reasons.append('high-severity log level')
        if e.get('template_frequency',1)<=2: reasons.append('rare log template')
        if contextual[i]>=.45: reasons.append('deviates from service context or dependency pattern')
        if e['is_anomaly']: reasons.append('unusual feature combination')
        e['reasons']=reasons
    return events

def detect_temporal_spikes(events, window_seconds=60):
    buckets=defaultdict(list)
    for e in events:
        ts=parse_time(e.get('timestamp'))
        if ts: buckets[(e.get('service','unknown'),int(ts.timestamp())//window_seconds)].append(e)
    counts=np.array([len(v) for v in buckets.values()])
    if len(counts)<3:return []
    median=float(np.median(counts)); mad=float(np.median(np.abs(counts-median)))+1e-6
    threshold=max(3.0,median+3.5*1.4826*mad); out=[]
    for (service,bucket),items in buckets.items():
        critical=sum(e.get('level') in ('WARN','ERROR','FATAL','CRITICAL') for e in items)
        if len(items)>=threshold and critical>=2:out.append({'service':service,'bucket':bucket,'count':len(items),'critical_count':critical,'threshold':threshold})
    return out

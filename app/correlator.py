from datetime import datetime
from uuid import uuid4
from .embeddings import cosine_similarity_matrix
from .detector import parse_time

DEPENDENCIES = {
 'database': ('db','database','mysql','postgres','sql','connection pool','query'),
 'api': ('api','http','request','gateway','endpoint','upstream'),
 'worker': ('worker','consumer','kafka','queue','job','task'),
 'cache': ('redis','cache'),
}

def _roles(event):
    text=(event.get('service','')+' '+event.get('message','')).lower(); found=set()
    for role,terms in DEPENDENCIES.items():
        if any(t in text for t in terms): found.add(role)
    return found

def _causal_pair(a, b):
    ra, rb = _roles(a), _roles(b)
    if ('database' in ra and ('api' in rb or 'worker' in rb)) or ('database' in rb and ('api' in ra or 'worker' in ra)):
        return True
    if ('api' in ra and 'worker' in rb) or ('api' in rb and 'worker' in ra):
        return True
    return False

def correlate_incidents(events, embedding_service, similarity_threshold=.48, time_window_seconds=600):
    candidates=[e for e in events if e.get('is_anomaly') or e.get('level') in ('WARN','ERROR','FATAL','CRITICAL')]
    if not candidates:return []
    vectors=embedding_service.encode([e.get('template') or e.get('message','') for e in candidates])
    sims=cosine_similarity_matrix(vectors); parent=list(range(len(candidates)))
    def find(x):
        while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
        return x
    def union(a,b): parent[find(a)]=find(b)
    for i,a in enumerate(candidates):
        ta=parse_time(a.get('timestamp'))
        for j in range(i+1,len(candidates)):
            b=candidates[j]; tb=parse_time(b.get('timestamp'))
            delta=abs((tb-ta).total_seconds()) if ta and tb else 0
            close=(not ta or not tb or delta<=time_window_seconds)
            same_service=a.get('service')==b.get('service')
            cross_role=bool(_roles(a)&_roles(b))
            if close and (sims[i,j]>=similarity_threshold or same_service or cross_role or _causal_pair(a,b)):union(i,j)
    grouped={}
    for i,e in enumerate(candidates):grouped.setdefault(find(i),[]).append(e)
    incidents=[]
    for group in grouped.values():
        group.sort(key=lambda e:parse_time(e.get('timestamp')) or datetime.max)
        times=[parse_time(e.get('timestamp')) for e in group if parse_time(e.get('timestamp'))]
        services=sorted({e.get('service','unknown') for e in group})
        levels=[e.get('level') for e in group]
        severity='critical' if any(x in levels for x in ('FATAL','CRITICAL')) else ('high' if 'ERROR' in levels else 'medium')
        # Causal candidate is the earliest dependency failure, not simply the loudest log.
        root=next((e for e in group if any(x in e.get('message','').lower() for x in ('connection refused','pool exhausted','database unavailable','deadlock','db timeout'))),group[0])
        chain=[]
        for e in group:
            role=next(iter(_roles(e)), 'service')
            chain.append({'timestamp':e.get('timestamp'),'service':e.get('service'),'role':role,
                          'message':e.get('message'),'level':e.get('level'),'is_root_candidate':e is root})
        incidents.append({'incident_id':f'INC-{uuid4().hex[:8].upper()}',
          'title':f"{', '.join(services[:2])} — {(root.get('message') or root.get('template') or 'related failures')[:65]}",
          'severity':severity,'start_time':min(times).isoformat() if times else None,
          'end_time':max(times).isoformat() if times else None,'event_count':len(group),
          'summary':f'{len(group)} correlated events across {len(services)} services.',
          'services':services,'events':group,'causal_sequence':chain,'root_candidate':root.get('message'),
          'investigation':None})
    return sorted(incidents,key=lambda x:x.get('start_time') or '')

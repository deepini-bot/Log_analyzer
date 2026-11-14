import os
import requests
import pandas as pd
import streamlit as st
import plotly.express as px

API=os.getenv('API_URL','http://localhost:8000')
st.set_page_config(page_title='LogMind | Incident Intelligence',page_icon='🧠',layout='wide')
st.title('🧠 LogMind')
st.caption('Context-aware anomaly detection · cross-service correlation · evidence-backed investigations')

def api(method,path,**kwargs):
    response=requests.request(method,API+path,timeout=90,**kwargs); response.raise_for_status(); return response.json()

with st.sidebar:
    st.header('Log ingestion')
    upload=st.file_uploader('Upload .log or .txt',type=['log','txt'])
    if upload and st.button('Analyze logs',type='primary'):
        try:
            st.session_state['result']=api('POST','/ingest',files={'file':(upload.name,upload.getvalue())})
            st.success(f"Processed {st.session_state['result']['event_count']} events")
        except Exception as exc: st.error(f'Ingestion failed: {exc}')
    st.divider(); st.header('Knowledge base')
    doc=st.file_uploader('Add runbook (.md/.txt)',type=['md','txt'],key='knowledge_upload')
    if doc and st.button('Index runbook'):
        try:
            result=api('POST','/knowledge/ingest',json={'source':doc.name,'content':doc.getvalue().decode('utf-8',errors='replace'),'source_type':'runbook'})
            st.success(f"Indexed {result['chunks_indexed']} chunks")
        except Exception as exc: st.error(str(exc))
    if st.button('Index data/knowledge folder'):
        try: st.success(api('POST','/knowledge/ingest-directory'))
        except Exception as exc: st.error(str(exc))
    if st.button('Refresh dashboard'): st.rerun()

try:
    incidents=api('GET','/incidents'); knowledge_stats=api('GET','/knowledge/stats')
except Exception as exc:
    incidents=[]; knowledge_stats={'chunks':0,'sources':0}; st.error(f'API unavailable: {exc}. Start with uvicorn app.main:app --reload')

if 'result' in st.session_state:
    result=st.session_state['result']; a,b,c,d=st.columns(4)
    a.metric('Events processed',result['event_count']); b.metric('Anomalies',result['anomaly_count'])
    c.metric('New incidents',len(result['incidents'])); d.metric('Knowledge chunks',knowledge_stats['chunks'])
    if result.get('temporal_spikes'): st.warning('Temporal spikes detected'); st.dataframe(pd.DataFrame(result['temporal_spikes']),use_container_width=True)

st.subheader('Incident overview')
if incidents:
    frame=pd.DataFrame([{'ID':x['incident_id'],'Title':x['title'],'Severity':x['severity'],'Events':x['event_count'],'Start':x['start_time']} for x in incidents])
    a,b,c=st.columns(3); a.metric('Open incidents',len(incidents)); b.metric('High / critical',sum(x['severity'] in ('high','critical') for x in incidents)); c.metric('Indexed sources',knowledge_stats['sources'])
    left,right=st.columns([1,2])
    with left: st.plotly_chart(px.pie(frame,names='Severity',title='Severity distribution'),use_container_width=True)
    with right: st.dataframe(frame,use_container_width=True,hide_index=True)
    service_rows=[]
    for inc in incidents:
        for svc in inc.get('services',[]): service_rows.append({'Service':svc,'Incident':inc['incident_id'],'Events':sum(e.get('service')==svc for e in inc.get('events',[]))})
    if service_rows:
        st.subheader('Service-level impact')
        sf=pd.DataFrame(service_rows).groupby('Service',as_index=False).agg(Incidents=('Incident','nunique'),Events=('Events','sum'))
        st.plotly_chart(px.bar(sf,x='Service',y='Events',color='Incidents',title='Event impact by service'),use_container_width=True)
    chosen=st.selectbox('Select an incident',[x['incident_id'] for x in incidents])
    try: incident=api('GET',f'/incidents/{chosen}')
    except Exception as exc: st.error(str(exc)); incident=None
    if incident:
        st.markdown('### '+incident['title']); st.write(incident['summary']); st.caption(f"{incident['severity'].upper()} · {incident['event_count']} events · {', '.join(incident.get('services',[]))}")
        events=incident.get('events',[])
        if events:
            st.subheader('Incident timeline')
            timeline=pd.DataFrame([{'Time':e.get('timestamp'),'Service':e.get('service'),'Level':e.get('level'),'Message':e.get('message'),'Anomaly score':e.get('anomaly_score',0)} for e in events])
            st.dataframe(timeline,use_container_width=True,hide_index=True)
        if st.button('Run causal AI investigation',type='primary'):
            try: st.session_state['investigation']=api('POST',f'/investigate/{chosen}')
            except Exception as exc: st.error(f'Investigation failed: {exc}')
        inv=st.session_state.get('investigation')
        if inv:
            st.subheader('Causal investigation'); st.info(inv.get('warning','Validate findings before acting.'))
            st.write(inv.get('incident_summary'))
            for cause in inv.get('probable_causes',[]):
                st.markdown(f"**Hypothesis:** {cause['cause']}  \nConfidence: {cause.get('confidence','unknown')} ({cause.get('confidence_score',0):.0%})")
                st.caption(cause.get('reasoning',''))
                st.write('Supporting evidence: '+', '.join(cause.get('supporting_evidence',[])))
            with st.expander('Causal sequence and raw evidence',expanded=True):
                st.dataframe(pd.DataFrame(inv.get('causal_sequence',[])),use_container_width=True,hide_index=True)
                st.dataframe(pd.DataFrame(inv.get('evidence',[])),use_container_width=True,hide_index=True)
            with st.expander('Retrieved runbooks and historical incidents'):
                st.dataframe(pd.DataFrame(inv.get('historical_context',[])),use_container_width=True,hide_index=True)
            with st.expander('Investigation steps and limitations'):
                st.write(inv.get('investigation_steps',[])); st.write(inv.get('limitations',[]))
            st.subheader('Engineer feedback')
            causes=inv.get('probable_causes',[])
            if causes:
                selected=st.selectbox('Hypothesis to review',[c['cause'] for c in causes])
                verdict=st.radio('Your assessment',['confirmed','rejected','inconclusive'],horizontal=True)
                notes=st.text_input('Notes (optional)')
                if st.button('Submit feedback'):
                    try: st.success(api('POST',f'/incidents/{chosen}/feedback',json={'hypothesis':selected,'verdict':verdict,'notes':notes}))
                    except Exception as exc: st.error(str(exc))
        feedback=incident.get('feedback',[])
        if feedback:
            st.subheader('Previous engineer feedback'); st.dataframe(pd.DataFrame(feedback),use_container_width=True,hide_index=True)
else: st.info('Upload a log file to create incidents. You can index runbooks from the sidebar at any time.')

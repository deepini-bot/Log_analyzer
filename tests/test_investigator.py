from app.investigator import investigate

class EmptyKnowledge:
    def retrieve(self, query, top_k=5):
        return []

def test_database_failure_precedes_downstream_symptoms():
    incident={'title':'database and worker failure','summary':'cross-service failure','severity':'high','events':[
      {'timestamp':'2026-01-01T10:00:00','service':'database','level':'ERROR','message':'Database connection timeout'},
      {'timestamp':'2026-01-01T10:00:10','service':'api','level':'ERROR','message':'upstream request timeout'},
      {'timestamp':'2026-01-01T10:00:20','service':'worker','level':'ERROR','message':'job failed after retry timeout'},
    ]}
    result=investigate(incident,EmptyKnowledge())
    assert result['mode']=='evidence_causal_rag'
    assert 'Database connectivity' in result['probable_causes'][0]['cause']
    assert result['probable_causes'][0]['confidence_score'] >= .6
    assert result['causal_sequence'][0]['service']=='database'

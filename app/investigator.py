import requests
from .config import settings

def investigate(incident, knowledge_base):
    query = incident["title"] + " " + " ".join(e.get("message", "") for e in incident["events"])
    similar = knowledge_base.retrieve(query, top_k=3)
    evidence = [f'{e.get("timestamp") or "unknown"} [{e.get("level")}] {e.get("service")}: {e.get("message")}'
                for e in incident["events"][:30]]
    prompt = f'''Analyze the incident using only the evidence below. Return JSON with incident_summary,
probable_causes (cause, confidence, supporting_evidence), investigation_steps, historical_context, limitations.
Causes must be labelled hypotheses, never confirmed facts.

Incident: {incident["title"]}
Severity: {incident["severity"]}
Log evidence:
{chr(10).join(evidence)}
Retrieved historical context:
{similar}
'''
    if settings.llm_base_url and settings.llm_api_key and settings.llm_model:
        try:
            response = requests.post(
                settings.llm_base_url.rstrip("/") + "/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={"model": settings.llm_model, "temperature": .2,
                      "messages": [{"role": "system", "content": "You are an evidence-grounded SRE assistant. Do not invent facts."},
                                   {"role": "user", "content": prompt}]},
                timeout=60)
            response.raise_for_status()
            answer = response.json()["choices"][0]["message"]["content"]
            return {"mode": "llm_rag", "analysis": answer, "evidence": evidence,
                    "retrieved_context": similar,
                    "warning": "LLM findings are hypotheses and require engineer validation."}
        except Exception as exc:
            llm_error = str(exc)
    else:
        llm_error = "LLM credentials are not configured."
    messages = " ".join(e.get("message", "").lower() for e in incident["events"])
    causes = []
    if any(term in messages for term in ("database", "connection", "sql")):
        causes.append({"cause": "Possible database connectivity or connection-pool issue",
                       "confidence": "medium", "support": "Database/connection terms appear in the logs."})
    if any(term in messages for term in ("timeout", "latency")):
        causes.append({"cause": "Possible downstream latency or timeout propagation",
                       "confidence": "medium", "support": "Timeout/latency terms appear in the logs."})
    if not causes:
        causes.append({"cause": "Insufficient evidence to identify a likely technical cause",
                       "confidence": "low", "support": "No specific dependency failure is visible in the supplied logs."})
    return {"mode": "evidence_rules_fallback",
            "analysis": {"incident_summary": incident["summary"], "probable_causes": causes,
                         "investigation_steps": [
                             "Inspect the first anomalous event and surrounding log context.",
                             "Check dependency health and service metrics for the same time window.",
                             "Compare the incident window with deployments and configuration changes.",
                             "Validate hypotheses using traces, metrics and application state."],
                         "historical_context": similar, "limitations": [llm_error]},
            "evidence": evidence, "retrieved_context": similar,
            "warning": "Probable causes are hypotheses, not confirmed root causes."}

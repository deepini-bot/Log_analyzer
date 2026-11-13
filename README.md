# LogMind — AI Log Anomaly Detection & Incident Investigation

A runnable intermediate-level portfolio project combining unsupervised ML, semantic embeddings, event correlation, RAG, and an optional LLM investigation layer.

## Run locally (Python 3.11 recommended)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
# Copy .env.example to .env
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

In another terminal:
```bash
streamlit run dashboard.py
```
Dashboard: http://localhost:8501

Upload `data/sample_logs/sample_incident.log` or run:
```bash
python scripts_ingest_sample.py
```

## AI configuration

The detector runs locally. For LLM investigation, configure an OpenAI-compatible chat-completions endpoint in `.env`:
```env
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=your_api_key
LLM_MODEL=your_model_name
```
Any compatible provider or local gateway can be used. Without credentials, the app returns a transparent evidence-rule fallback rather than pretending an LLM ran.

Sentence Transformers downloads `all-MiniLM-L6-v2` on first use. Set `USE_SENTENCE_TRANSFORMERS=false` to use TF-IDF fallback. Chroma is optional; JSON lexical retrieval is the fallback.

## API
- `POST /ingest` — upload `.log` or `.txt`
- `POST /ingest/text` — ingest raw log text
- `GET /incidents` — list current-process incidents
- `GET /incidents/{id}` — detail
- `POST /investigate/{id}` — RAG + optional LLM investigation
- `GET /health` — health check

## Detection pipeline
1. Parse timestamps, severity, service and message.
2. Normalize variable values into message templates.
3. Build event features and score with Isolation Forest.
4. Detect temporal bursts in service log volume.
5. Group suspicious events by semantic similarity and time proximity.
6. Retrieve similar incident knowledge and generate evidence-grounded hypotheses.

**Root causes are hypotheses, not verified facts.** Validate with metrics, traces, deployments and service state. This MVP keeps incident state in memory; persistence and streaming ingestion are natural next extensions.

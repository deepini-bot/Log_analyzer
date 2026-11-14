# LogMind — AI Log Anomaly Detection & Causal Incident Investigation

LogMind is an intermediate-level portfolio project for investigating distributed application failures. It combines unsupervised anomaly detection, service-aware context signals, cross-service correlation, local RAG over runbooks and historical incidents, causal-sequence reconstruction, evidence-backed hypotheses, engineer feedback, SQLite persistence and a Streamlit dashboard.

## What is implemented

1. **RAG knowledge ingestion** — index Markdown/text runbooks, troubleshooting guides and resolved incident notes into persistent chunks; retrieve relevant chunks for an investigation.
2. **Context-aware anomaly detection** — Isolation Forest plus service-relative severity, template rarity and dependency-symptom features. Scores and reasons are attached to each event.
3. **Cross-service correlation** — group anomalous/high-severity events using time proximity, semantic similarity and dependency-role signals.
4. **Causal investigation** — order correlated events and identify likely initiating dependency failures (for example DB connection-pool exhaustion followed by API timeouts and worker failures).
5. **Evidence-backed reports** — hypotheses include confidence scores, evidence IDs, supporting log messages, retrieved context, investigation steps and limitations. Optional OpenAI-compatible LLM enrichment is supported.
6. **Incident feedback** — engineers can confirm, reject or mark a hypothesis inconclusive, with notes.
7. **Persistent storage** — SQLite stores incidents, investigations, feedback and knowledge chunks. Incidents survive API restarts.
8. **Dashboard** — incident overview, severity chart, service-level impact, event timeline, investigation, evidence and feedback views.
9. **Automated tests** — parser, detector, knowledge chunking, cross-service correlation, persistence and API tests.

All root-cause outputs are hypotheses, not proof. Production-grade causal certainty requires traces, metrics, deployment events and service topology.

## Quick start (Windows PowerShell)

Use Python 3.11. From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

For a quick first run without downloading a transformer model, set `USE_SENTENCE_TRANSFORMERS=false` in `.env`. This uses a local TF-IDF embedding fallback. For stronger semantic retrieval, set it to `true`; the configured Sentence Transformer model downloads on first use.

Start the API:

```powershell
uvicorn app.main:app --reload
```

In another terminal, activate the same environment and run:

```powershell
streamlit run dashboard.py
```

- API docs: http://localhost:8000/docs
- Dashboard: http://localhost:8501

## Demo flow

1. Upload `data/sample_logs/sample_incident.log` in the dashboard, or call `POST /ingest`.
2. Index the supplied `data/knowledge/runbook_database.md` using **Index data/knowledge folder**. You can also upload `.md` or `.txt` runbooks in the sidebar.
3. Open an incident and click **Run causal AI investigation**.
4. Review the causal sequence, confidence-scored hypotheses, evidence IDs and retrieved runbook chunks.
5. Confirm/reject a hypothesis and add notes. Feedback is persisted.
6. Submit a resolution to `POST /incidents/{incident_id}/resolution` to add the resolved incident to future RAG retrieval.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health and version |
| POST | `/ingest` | Upload `.log` / `.txt` |
| POST | `/ingest/text` | Ingest raw log text |
| POST | `/knowledge/ingest` | Index a runbook or incident note |
| POST | `/knowledge/ingest-directory` | Index supported files in a directory |
| GET | `/knowledge/stats` | Knowledge-base statistics |
| GET | `/incidents` | Persistent incident list |
| GET | `/incidents/{id}` | Incident detail and feedback |
| POST | `/investigate/{id}` | Run RAG + causal investigation |
| POST | `/incidents/{id}/feedback` | Confirm/reject/inconclusive feedback |
| GET | `/incidents/{id}/feedback` | Feedback history |
| POST | `/incidents/{id}/resolution` | Store a resolution in RAG |

Example knowledge payload:

```json
{
  "source": "database-connection-runbook.md",
  "source_type": "runbook",
  "content": "When the connection pool is exhausted, inspect active sessions..."
}
```

Example feedback payload:

```json
{
  "hypothesis": "Database connection-pool exhaustion",
  "verdict": "confirmed",
  "notes": "Pool saturation was visible in database metrics."
}
```

## Configuration

Copy `.env.example` to `.env`:

```env
APP_NAME=LogMind
DATA_DIR=./data
USE_SENTENCE_TRANSFORMERS=false
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
```

Optional LLM configuration uses an OpenAI-compatible chat-completions endpoint. Without credentials, deterministic causal analysis still runs and clearly identifies itself as such.

## Run tests

```powershell
$env:USE_SENTENCE_TRANSFORMERS="false"
$env:DATA_DIR="./test_data"
pytest -q
```

## Docker Compose

Create `.env` from `.env.example`, then:

```bash
docker compose up --build
```

API on port 8000 and dashboard on port 8501. SQLite and indexed knowledge are persisted in the mounted `data/` directory.

## Design notes / current limitations

- The first version is a batch log-analysis MVP, not a streaming collector.
- Correlation uses event time, semantic similarity and lightweight service-role heuristics; it does not infer a guaranteed causal graph.
- Confidence is a heuristic evidence score, not a calibrated probability.
- SQLite is appropriate for a local portfolio demo; a multi-instance deployment would need a server database and coordinated vector store.
- Avoid uploading secrets, tokens, customer identifiers or production personal data into the demo.

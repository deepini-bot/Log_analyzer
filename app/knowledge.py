import json
from pathlib import Path
from .config import settings

class KnowledgeBase:
    def __init__(self):
        self.path = Path(settings.data_dir) / "knowledge" / "incidents.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.records = self._load()
        self.collection = None
        if settings.use_chroma:
            try:
                import chromadb
                client = chromadb.PersistentClient(path=settings.chroma_dir)
                self.collection = client.get_or_create_collection("logmind_incidents")
            except Exception as exc:
                print(f"Chroma unavailable; JSON retrieval fallback: {exc}")

    def _load(self):
        try:
            return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else []
        except Exception:
            return []

    def _save(self):
        self.path.write_text(json.dumps(self.records, indent=2), encoding="utf-8")

    def add_incident(self, incident, resolution=""):
        record = {"id": incident["incident_id"],
                  "text": incident["title"] + " " + incident["summary"] + " " +
                          " ".join(e.get("message", "") for e in incident.get("events", [])),
                  "resolution": resolution, "severity": incident.get("severity", "medium")}
        self.records.append(record)
        self._save()
        if self.collection is not None:
            self.collection.upsert(ids=[record["id"]], documents=[record["text"] + " " + resolution],
                                   metadatas=[{"severity": record["severity"], "resolution": resolution}])

    def retrieve(self, query, top_k=3):
        if self.collection is not None:
            try:
                result = self.collection.query(query_texts=[query], n_results=top_k)
                docs, ids, metas = result["documents"][0], result["ids"][0], result["metadatas"][0]
                return [{"id": i, "text": d, **(m or {})} for i, d, m in zip(ids, docs, metas)]
            except Exception as exc:
                print(f"Chroma query fallback: {exc}")
        terms = set(query.lower().split())
        scored = []
        for rec in self.records:
            words = set(rec["text"].lower().split())
            score = len(terms & words) / max(len(terms), 1)
            if score:
                scored.append((score, rec))
        return [r for _, r in sorted(scored, key=lambda x: x[0], reverse=True)[:top_k]]

"""Local RAG ingestion and retrieval for runbooks, guides and resolved incidents."""
import hashlib
import re
from pathlib import Path
from .config import settings
from .embeddings import EmbeddingService, cosine_similarity_matrix
from .storage import upsert_knowledge, list_knowledge

SUPPORTED = {'.md', '.txt', '.rst', '.log'}

class KnowledgeBase:
    def __init__(self, embedding_service=None):
        self.embedding_service = embedding_service or EmbeddingService(settings.embedding_model, settings.use_sentence_transformers)

    @staticmethod
    def chunk_text(text, chunk_size=900, overlap=140):
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        if not text: return []
        chunks, start = [], 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            if end < len(text):
                boundary = max(text.rfind('\n', start, end), text.rfind('. ', start, end))
                if boundary > start + chunk_size // 2: end = boundary + 1
            part = text[start:end].strip()
            if part: chunks.append(part)
            if end >= len(text): break
            start = max(start + 1, end - overlap)
        return chunks

    def add_document(self, source, text, source_type='runbook', metadata=None):
        rows = []
        for index, content in enumerate(self.chunk_text(text)):
            key = hashlib.sha256(f'{source}:{index}:{content}'.encode()).hexdigest()[:24]
            row = {'chunk_id': key, 'source': str(source), 'source_type': source_type,
                   'content': content, 'metadata': {**(metadata or {}), 'chunk_index': index}}
            upsert_knowledge(row); rows.append(row)
        return {'source': str(source), 'chunks_indexed': len(rows), 'source_type': source_type}

    def ingest_directory(self, directory=None):
        root = Path(directory or (Path(settings.data_dir) / 'knowledge'))
        root.mkdir(parents=True, exist_ok=True)
        results = []
        for path in sorted(root.rglob('*')):
            if path.is_file() and path.suffix.lower() in SUPPORTED and path.name != 'incidents.json':
                try:
                    results.append(self.add_document(str(path), path.read_text(encoding='utf-8', errors='replace'), 'runbook'))
                except OSError:
                    continue
        return {'files_indexed': len(results), 'chunks_indexed': sum(x['chunks_indexed'] for x in results), 'files': results}

    def add_incident(self, incident, resolution=''):
        text = '\n'.join([incident.get('title',''), incident.get('summary',''),
                          *[e.get('message','') for e in incident.get('events', [])],
                          'Resolution: ' + resolution])
        return self.add_document(incident['incident_id'], text, 'historical_incident',
                                 {'severity': incident.get('severity'), 'resolution': resolution})

    def retrieve(self, query, top_k=5):
        records = list_knowledge()
        if not records: return []
        texts = [r['content'] for r in records] + [query]
        vectors = self.embedding_service.encode(texts)
        sims = cosine_similarity_matrix(vectors)[-1, :-1]
        ranked = sorted(zip(sims.tolist(), records), key=lambda x: x[0], reverse=True)
        return [{**r, 'score': round(float(score), 4)} for score, r in ranked[:top_k] if score > 0]

import numpy as np

class EmbeddingService:
    def __init__(self, model_name, use_transformers=True):
        self.model = None
        if use_transformers:
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(model_name)
            except Exception as exc:
                print(f"SentenceTransformer unavailable; TF-IDF fallback enabled: {exc}")

    def encode(self, texts):
        if not texts:
            return np.zeros((0, 1))
        if self.model is not None:
            return np.asarray(self.model.encode(texts, normalize_embeddings=True))
        from sklearn.feature_extraction.text import TfidfVectorizer
        return TfidfVectorizer(ngram_range=(1, 2), max_features=512).fit_transform(texts).toarray()

def cosine_similarity_matrix(vectors):
    if len(vectors) == 0:
        return np.zeros((0, 0))
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    normalized = vectors / np.maximum(norms, 1e-12)
    return normalized @ normalized.T

"""Qdrant vector store: semantic memory of bugs, fixes, docs and past runs."""
import os, uuid
from qdrant_client import AsyncQdrantClient, models
from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None


def embed(texts: list[str]) -> list[list[float]]:
    global _model
    _model = _model or SentenceTransformer(os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"))
    return _model.encode(texts, normalize_embeddings=True).tolist()


class VectorStore:
    DIM = 384

    def __init__(self):
        self.c = AsyncQdrantClient(url=os.getenv("QDRANT_URL", "http://qdrant:6333"),
                                   api_key=os.getenv("QDRANT_API_KEY") or None)
        self.col = os.getenv("QDRANT_COLLECTION", "typhoid_bugs")

    async def ensure(self):
        if not await self.c.collection_exists(self.col):
            await self.c.create_collection(self.col, vectors_config=models.VectorParams(size=self.DIM, distance=models.Distance.COSINE))

    async def upsert(self, text: str, payload: dict):
        await self.ensure()
        await self.c.upsert(self.col, [models.PointStruct(id=str(uuid.uuid4()), vector=embed([text])[0], payload={**payload, "text": text})])

    async def search(self, query: str, k: int = 5, repo: str | None = None) -> list[dict]:
        await self.ensure()
        flt = models.Filter(must=[models.FieldCondition(key="repo", match=models.MatchValue(value=repo))]) if repo else None
        hits = await self.c.search(self.col, query_vector=embed([query])[0], limit=k, query_filter=flt)
        return [{"score": h.score, **h.payload} for h in hits]

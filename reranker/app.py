# reranker/app.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any
import time
from sentence_transformers import CrossEncoder
import torch

app = FastAPI(title="Reranker Service")

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
device = "cuda" if torch.cuda.is_available() else "cpu"
print("Loading reranker model on", device)
reranker = CrossEncoder(MODEL_NAME, device=device)
print("Reranker loaded:", MODEL_NAME)

class Candidate(BaseModel):
    id: str
    text: str
    metadata: Dict[str, Any] = {}

class RerankRequest(BaseModel):
    query: str
    candidates: List[Candidate]
    top_k: int = 5

class RerankItem(BaseModel):
    id: str
    score: float
    text: str
    metadata: Dict[str, Any] = {}

@app.post("/rerank", response_model=List[RerankItem])
def rerank(req: RerankRequest):
    start = time.time()
    if not req.candidates:
        return []
    pairs = [(req.query, c.text) for c in req.candidates]
    scores = reranker.predict(pairs, batch_size=16)
    scored = []
    for c, s in zip(req.candidates, scores):
        scored.append({"id": c.id, "score": float(s), "text": c.text, "metadata": c.metadata})
    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[: req.top_k]
    latency = (time.time() - start) * 1000
    print(f"Rerank latency_ms={latency:.1f} top_k={req.top_k}")
    return top
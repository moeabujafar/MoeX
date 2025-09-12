import math
from typing import List, Tuple
from .db import DB_INSTANCE as DB

def _tokenize(text: str) -> List[str]:
    return [t for t in text.lower().split() if t]

def _vectorize(text: str) -> dict:
    vec = {}
    for t in _tokenize(text):
        vec[t] = vec.get(t, 0) + 1
    return vec

def _cosine(a: dict, b: dict) -> float:
    inter = set(a) & set(b)
    num = sum(a[t]*b[t] for t in inter)
    den = math.sqrt(sum(v*v for v in a.values())) * math.sqrt(sum(v*v for v in b.values()))
    return num/den if den else 0.0

def search(query: str, top_k: int = 4) -> List[Tuple[str, str, float]]:
    qv = _vectorize(query)
    rows = DB.all_knowledge()
    scored = []
    for r in rows:
        score = _cosine(qv, _vectorize(r["chunk"]))
        if score > 0:
            scored.append((r["title"], r["chunk"], score))
    scored.sort(key=lambda x: x[2], reverse=True)
    return scored[:top_k]

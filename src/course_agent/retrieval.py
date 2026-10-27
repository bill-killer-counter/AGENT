"""Local hybrid retrieval: exact phrase matching first, TF-IDF fallback second."""
import re
from .similarity import vectors, cosine


def _normalize(text):
    return re.sub(r"\s+", "", (text or "").lower())


def _phrase_score(query, text):
    q, source = _normalize(query), _normalize(text)
    if not q or not source:
        return 0.0
    if q in source:
        return 1.0
    # Long Chinese terms are often meaningful without whitespace; reward full-term containment.
    terms = [term for term in re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9_]{2,}", q) if len(term) >= 2]
    if terms and all(term in source for term in terms):
        return 0.82
    return 0.0


def search(query, workspace_id, repository, top_k=5):
    if not query or not query.strip():
        return []
    rows = repository.chunks(workspace_id)
    if not rows:
        return []
    vec = vectors([row["text"] for row in rows] + [query])
    ranked = []
    for index, row in enumerate(rows):
        tfidf = cosine(vec[-1], vec[index])
        exact = _phrase_score(query, row["text"])
        score = max(tfidf, exact)
        ranked.append((score, row))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [{"chunk_id": row["id"], "document_id": row["document_id"], "filename": row["filename"], "text": row["text"], "score": float(score)} for score, row in ranked[:top_k]]
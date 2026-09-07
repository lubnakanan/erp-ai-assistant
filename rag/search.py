"""
Hybrid retrieval over the ERP Assistant knowledge base.

Combines two independent retrieval methods and merges their rankings
with Reciprocal Rank Fusion (RRF) — this is the "hybrid search"
technique from LLM Zoomcamp Module 6:
  1. Keyword search  -> minsearch (BM25-style, exact term matching)
  2. Vector search    -> Chroma + sentence-transformers (semantic matching)

Both are useful: keyword search catches exact ERPNext terminology
("Purchase Receipt", "GL Entry"); vector search catches paraphrased
questions ("how do I record incoming stock from a supplier?").
"""

import json
from pathlib import Path

import chromadb
from minsearch import Index

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CHUNKS_PATH = DATA_DIR / "chunks.jsonl"
CHROMA_DIR = DATA_DIR / "chroma"
COLLECTION_NAME = "erp_docs"

_keyword_index = None
_chunks_by_id = None
_chroma_collection = None


def _load_chunks():
    with CHUNKS_PATH.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _get_keyword_index():
    global _keyword_index, _chunks_by_id
    if _keyword_index is None:
        chunks = _load_chunks()
        _chunks_by_id = {c["chunk_id"]: c for c in chunks}
        _keyword_index = Index(
            text_fields=["text", "title", "heading"],
            keyword_fields=["module"],
        )
        _keyword_index.fit(chunks)
    return _keyword_index


def _get_chroma_collection():
    global _chroma_collection
    if _chroma_collection is None:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _chroma_collection = client.get_collection(COLLECTION_NAME)
    return _chroma_collection


def keyword_search(query: str, num_results: int = 5, module: str | None = None):
    index = _get_keyword_index()
    filter_dict = {"module": module} if module else {}
    results = index.search(query, filter_dict=filter_dict, num_results=num_results)
    return results  # list of chunk dicts, best match first


def vector_search(query: str, num_results: int = 5, module: str | None = None):
    # Chroma embeds the query text itself using the same default ONNX
    # embedding function it used to index the chunks — no separate
    # model to load here, which keeps this fast and light on RAM.
    collection = _get_chroma_collection()
    where = {"module": module} if module else None
    result = collection.query(query_texts=[query], n_results=num_results, where=where)

    _get_keyword_index()  # ensure _chunks_by_id is populated
    hits = []
    for chunk_id in result["ids"][0]:
        if chunk_id in _chunks_by_id:
            hits.append(_chunks_by_id[chunk_id])
    return hits


def hybrid_search(query: str, num_results: int = 5, module: str | None = None, rrf_k: int = 60):
    """Merge keyword_search and vector_search rankings with Reciprocal
    Rank Fusion: score(doc) = sum(1 / (rrf_k + rank)) across both lists.
    A doc that ranks well in *either* list gets a strong combined score;
    a doc that ranks well in *both* gets an even stronger one."""
    keyword_hits = keyword_search(query, num_results=10, module=module)
    vector_hits = vector_search(query, num_results=10, module=module)

    scores: dict[str, float] = {}
    chunk_lookup: dict[str, dict] = {}

    for rank, chunk in enumerate(keyword_hits):
        scores[chunk["chunk_id"]] = scores.get(chunk["chunk_id"], 0) + 1 / (rrf_k + rank + 1)
        chunk_lookup[chunk["chunk_id"]] = chunk

    for rank, chunk in enumerate(vector_hits):
        scores[chunk["chunk_id"]] = scores.get(chunk["chunk_id"], 0) + 1 / (rrf_k + rank + 1)
        chunk_lookup[chunk["chunk_id"]] = chunk

    ranked_ids = sorted(scores, key=scores.get, reverse=True)[:num_results]
    return [chunk_lookup[cid] for cid in ranked_ids]


if __name__ == "__main__":
    # Quick manual smoke test
    q = "How do I create a purchase order?"
    print(f"Query: {q}\n")
    for label, fn in [("Keyword", keyword_search), ("Vector", vector_search), ("Hybrid", hybrid_search)]:
        print(f"--- {label} ---")
        for hit in fn(q, num_results=3):
            print(f"  [{hit['module']}] {hit['title']}")
        print()

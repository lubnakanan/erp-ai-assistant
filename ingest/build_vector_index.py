"""
Step 4 (lightweight version): Generate embeddings for every chunk in
data/chunks.jsonl and store them in a local, persistent Chroma vector
database.

Embedding model: Chroma's DEFAULT embedding function, which runs
all-MiniLM-L6-v2 through ONNX Runtime.
  - Same underlying model as sentence-transformers would use, but no
    PyTorch/`sentence-transformers` dependency at all — ONNX Runtime is
    much lighter on RAM, which matters a lot on constrained hardware
    (8GB RAM, HDD, no GPU).
  - Fully local and free; the ~80MB ONNX model is downloaded once and
    cached.

Usage:
    python build_vector_index.py

Input:
    data/chunks.jsonl   (written by chunk_docs.py)

Output:
    data/chroma/   -> persistent Chroma DB folder (collection "erp_docs")
"""

import json
from pathlib import Path

import chromadb
from tqdm import tqdm

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CHUNKS_PATH = DATA_DIR / "chunks.jsonl"
CHROMA_DIR = DATA_DIR / "chroma"
COLLECTION_NAME = "erp_docs"


def load_chunks():
    with CHUNKS_PATH.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    if not CHUNKS_PATH.exists():
        raise SystemExit(f"{CHUNKS_PATH} not found. Run chunk_docs.py first.")

    chunks = load_chunks()
    print(f"Loaded {len(chunks)} chunks.")

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Start clean each run so re-running this script never duplicates vectors
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    # No embedding_function passed -> Chroma uses its default
    # (all-MiniLM-L6-v2 via ONNX Runtime, no torch needed).
    collection = client.create_collection(COLLECTION_NAME)

    ids = [c["chunk_id"] for c in chunks]
    texts = [c["text"] for c in chunks]
    metadatas = [
        {
            "doc_id": c["doc_id"],
            "title": c["title"],
            "module": c["module"],
            "url": c["url"],
            "heading": c["heading"] or "",
        }
        for c in chunks
    ]

    print("Adding chunks to Chroma (it embeds them internally via ONNX)...")
    step = 200  # smaller batches keep peak RAM low on weaker machines
    for i in tqdm(range(0, len(ids), step), desc="Embedding + storing"):
        collection.add(
            ids=ids[i : i + step],
            documents=texts[i : i + step],
            metadatas=metadatas[i : i + step],
        )

    print(f"\nDone. Stored {collection.count()} vectors in Chroma at {CHROMA_DIR} (collection: '{COLLECTION_NAME}')")

    # Quick sanity check
    sample_query = "How do I create a purchase order?"
    result = collection.query(query_texts=[sample_query], n_results=3)
    print(f"\nSanity check — top matches for: '{sample_query}'")
    for meta, dist in zip(result["metadatas"][0], result["distances"][0]):
        print(f"  - [{meta['module']}] {meta['title']} (distance={dist:.3f}) -> {meta['url']}")


if __name__ == "__main__":
    main()

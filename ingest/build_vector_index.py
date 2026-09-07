"""
Step 4: Generate embeddings for every chunk in data/chunks.jsonl and
store them in a local, persistent Chroma vector database.

Model: sentence-transformers/all-MiniLM-L6-v2
  - Small (~80MB), fast on CPU, good quality for semantic search.
  - Runs fully locally — no API key, no internet needed after the
    one-time model download.

Usage:
    python build_vector_index.py
    python build_vector_index.py --batch-size 32   # smaller batches if RAM is tight

Input:
    data/chunks.jsonl   (written by chunk_docs.py)

Output:
    data/chroma/   -> persistent Chroma DB folder (a "collection" named
                       "erp_docs" containing one vector per chunk)
"""

import argparse
import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CHUNKS_PATH = DATA_DIR / "chunks.jsonl"
CHROMA_DIR = DATA_DIR / "chroma"
COLLECTION_NAME = "erp_docs"
MODEL_NAME = "all-MiniLM-L6-v2"


def load_chunks():
    with CHUNKS_PATH.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=64, help="Embedding batch size (lower this if you run out of RAM)")
    args = parser.parse_args()

    if not CHUNKS_PATH.exists():
        raise SystemExit(f"{CHUNKS_PATH} not found. Run chunk_docs.py first.")

    chunks = load_chunks()
    print(f"Loaded {len(chunks)} chunks.")

    print(f"Loading embedding model '{MODEL_NAME}' (first run downloads it, ~80MB)...")
    model = SentenceTransformer(MODEL_NAME)

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Start clean each run so re-running this script never duplicates vectors
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
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

    print("Encoding chunks into embeddings (this is the slow part on CPU)...")
    embeddings = model.encode(
        texts,
        batch_size=args.batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
    )

    print("Writing to Chroma...")
    # Chroma has a per-call insert limit; add in batches to be safe.
    step = 500
    for i in tqdm(range(0, len(ids), step), desc="Upserting into Chroma"):
        collection.add(
            ids=ids[i : i + step],
            embeddings=embeddings[i : i + step].tolist(),
            documents=texts[i : i + step],
            metadatas=metadatas[i : i + step],
        )

    print(f"\nDone. Stored {collection.count()} vectors in Chroma at {CHROMA_DIR} (collection: '{COLLECTION_NAME}')")

    # Quick sanity check: run one sample query
    sample_query = "How do I create a purchase order?"
    result = collection.query(query_texts=[sample_query], n_results=3)
    print(f"\nSanity check — top matches for: '{sample_query}'")
    for doc_id, meta, dist in zip(result["ids"][0], result["metadatas"][0], result["distances"][0]):
        print(f"  - [{meta['module']}] {meta['title']} (distance={dist:.3f}) -> {meta['url']}")


if __name__ == "__main__":
    main()

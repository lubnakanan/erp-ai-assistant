"""
The complete RAG flow: retrieve relevant chunks, build a grounded
prompt, call the local Ollama LLM, and return the answer plus the
sources used (so the UI can show "based on: ...").
"""

import time

import ollama

from prompts import build_prompt
from search import hybrid_search

MODEL_NAME = "llama3.2:1b"

# Small hardware (CPU-only, 8GB RAM, HDD) needs a small request:
# fewer chunks, each truncated, and a capped/limited context window +
# output length so Ollama doesn't spend minutes on a single answer.
DEFAULT_NUM_RESULTS = 3
MAX_CHARS_PER_CHUNK = 500


def _trim_chunks(chunks: list[dict]) -> list[dict]:
    trimmed = []
    for c in chunks:
        c = dict(c)
        if len(c["text"]) > MAX_CHARS_PER_CHUNK:
            c["text"] = c["text"][:MAX_CHARS_PER_CHUNK] + "..."
        trimmed.append(c)
    return trimmed


def answer_question(question: str, num_results: int = DEFAULT_NUM_RESULTS, module: str | None = None) -> dict:
    start = time.time()

    chunks = hybrid_search(question, num_results=num_results, module=module)
    chunks_for_prompt = _trim_chunks(chunks)
    prompt = build_prompt(question, chunks_for_prompt)

    response = ollama.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        options={
            "num_predict": 220,   # cap answer length
            "num_ctx": 1536,      # cap context window
        },
    )
    answer = response["message"]["content"]

    elapsed = time.time() - start

    sources = [
        {"title": c["title"], "module": c["module"], "url": c["url"]}
        for c in chunks
    ]

    return {
        "question": question,
        "answer": answer,
        "sources": sources,
        "response_time_sec": round(elapsed, 2),
    }


if __name__ == "__main__":
    result = answer_question("How do I create a purchase order?")
    print(f"Q: {result['question']}\n")
    print(f"A: {result['answer']}\n")
    print(f"(answered in {result['response_time_sec']}s)\n")
    print("Sources:")
    for s in result["sources"]:
        print(f"  - [{s['module']}] {s['title']} -> {s['url']}")

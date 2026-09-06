"""
Step 3: Split fetched ERPNext / Frappe HR markdown pages into retrieval
chunks, using markdown headings and paragraphs as the natural split
points (no fixed word-count / overlap logic).

How it works, per page:
  1. Split the page on markdown headings (##, ###, ...).
  2. Any resulting section still longer than MAX_CHUNK_CHARS is split
     further on blank-line paragraph breaks.
  3. Any fragment shorter than MIN_CHUNK_CHARS (e.g. a bare heading with
     no real content under it) is merged into the next fragment instead
     of being kept as its own near-empty chunk.

Usage:
    python chunk_docs.py

Input:
    data/erpnext_docs/manifest.jsonl   (written by fetch_docs.py)
    data/erpnext_docs/<slug>.md

Output:
    data/chunks.jsonl   -> one JSON object per chunk:
        {chunk_id, doc_id, title, module, url, heading, text}
"""

import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DOCS_DIR = DATA_DIR / "erpnext_docs"
MANIFEST_PATH = DOCS_DIR / "manifest.jsonl"
OUTPUT_PATH = DATA_DIR / "chunks.jsonl"

MAX_CHUNK_CHARS = 1500   # split further if a heading-section is bigger than this
MIN_CHUNK_CHARS = 80     # merge forward if a fragment is smaller than this

HEADING_RE = re.compile(r"^(#{2,6})\s+(.*)$", re.MULTILINE)


def split_by_headings(text: str):
    """Yield (heading, section_text) pairs. Content before the first
    heading (if any) gets heading=None."""
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        yield None, text.strip()
        return

    if matches[0].start() > 0:
        preamble = text[: matches[0].start()].strip()
        if preamble:
            yield None, preamble

    for i, match in enumerate(matches):
        heading = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()
        yield heading, section_text


def split_by_paragraphs(text: str, max_chars: int):
    """Greedily pack paragraphs (separated by blank lines) into chunks
    no larger than max_chars."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, current = [], ""
    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) > max_chars and current:
            chunks.append(current)
            current = para
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks or [text]


def merge_small_fragments(fragments: list[tuple[str | None, str]]):
    """Merge any (heading, text) fragment smaller than MIN_CHUNK_CHARS
    into the fragment that follows it."""
    merged = []
    pending_heading, pending_text = None, ""
    for heading, text in fragments:
        if pending_text:
            text = f"{pending_text}\n\n{text}".strip()
            heading = pending_heading or heading
            pending_heading, pending_text = None, ""
        if len(text) < MIN_CHUNK_CHARS:
            pending_heading, pending_text = heading, text
            continue
        merged.append((heading, text))
    if pending_text:
        # trailing small fragment with nothing after it: attach to the
        # previous chunk rather than dropping it
        if merged:
            prev_heading, prev_text = merged[-1]
            merged[-1] = (prev_heading, f"{prev_text}\n\n{pending_text}".strip())
        else:
            merged.append((pending_heading, pending_text))
    return merged


def chunk_page(title: str, body: str):
    raw_sections = list(split_by_headings(body))

    expanded = []
    for heading, section_text in raw_sections:
        if len(section_text) <= MAX_CHUNK_CHARS:
            expanded.append((heading, section_text))
        else:
            for piece in split_by_paragraphs(section_text, MAX_CHUNK_CHARS):
                expanded.append((heading, piece))

    return merge_small_fragments(expanded)


def main() -> None:
    if not MANIFEST_PATH.exists():
        raise SystemExit(f"Manifest not found at {MANIFEST_PATH}. Run fetch_docs.py first.")

    records = [json.loads(line) for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"Loaded {len(records)} pages from manifest.")

    total_chunks = 0
    with OUTPUT_PATH.open("w", encoding="utf-8") as out_file:
        for rec in records:
            md_path = DATA_DIR.parent / rec["path"]
            if not md_path.exists():
                print(f"  [!] missing file for {rec['id']}, skipping")
                continue

            body = md_path.read_text(encoding="utf-8")
            page_chunks = chunk_page(rec["title"], body)

            for i, (heading, text) in enumerate(page_chunks):
                chunk = {
                    "chunk_id": f"{rec['id']}::{i}",
                    "doc_id": rec["id"],
                    "title": rec["title"],
                    "module": rec["module"],
                    "url": rec["url"],
                    "heading": heading,
                    "text": text,
                }
                out_file.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                total_chunks += 1

    print(f"\nDone. Wrote {total_chunks} chunks from {len(records)} pages to {OUTPUT_PATH}")
    print(f"Average chunks per page: {total_chunks / len(records):.1f}")


if __name__ == "__main__":
    main()

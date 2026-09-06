"""
Step 1: Fetch ERPNext / Frappe HR documentation pages, scoped to the
5 modules that map to the core SAP modules most in demand in the
Jordanian market: Accounting (FI/CO), Buying (MM-procurement),
Stock (MM-inventory), Selling (SD), HR & Payroll (HCM).

Sources (each page is available as clean Markdown by appending .md):
  - https://docs.frappe.io/erpnext/llms.txt  -> filtered to Accounting/Buying/Selling/Stock
  - https://docs.frappe.io/hr/llms.txt        -> taken in full (it's already HR-only)

Usage:
    python fetch_docs.py                 # fetch everything in scope
    python fetch_docs.py --limit 20       # quick test run, first 20 pages only
    python fetch_docs.py --delay 0.3      # be polite to the server (default 0.25s)

Output:
    data/erpnext_docs/<slug>.md      -> one file per page (raw markdown)
    data/erpnext_docs/manifest.jsonl -> one JSON line per page: id, title, url, module, path
"""

import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from tqdm import tqdm

ERPNEXT_INDEX_URL = "https://docs.frappe.io/erpnext/llms.txt"
HR_INDEX_URL = "https://docs.frappe.io/hr/llms.txt"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "erpnext_docs"
HEADERS = {"User-Agent": "erp-ai-assistant-ingest/1.0 (educational RAG project)"}

# Safety cap: a handful of pages on this site have returned content that's
# 100-1000x larger than a normal doc page (likely a rendering glitch on
# their end, e.g. duplicated content). We cap and flag those instead of
# silently letting a single bad page dominate the whole knowledge base.
MAX_CONTENT_CHARS = 30_000

# The ERPNext modules we're keeping (case-insensitive match on the
# top-level list item label in llms.txt). Buying/Selling/Stock cover
# SAP MM + SD; Accounting covers SAP FI/CO.
WANTED_ERPNEXT_MODULES = {"accounting", "buying", "selling", "stock"}

URL_RE = re.compile(r"https://docs\.frappe\.io/(?:erpnext|hr)/[^\s\)>\]]+")
LABEL_RE = re.compile(r"^-\s*(?:\*\*(?P<bold>[^*]+)\*\*|\[(?P<link>[^\]]+)\]\([^)]+\))")


def extract_label(line: str) -> str:
    match = LABEL_RE.match(line.strip())
    if not match:
        return ""
    label = match.group("bold") or match.group("link") or ""
    return label.split(":")[0].strip()


def normalise_url(raw_url: str) -> str:
    url = raw_url.rstrip(").,>]")
    if url.endswith(".md"):
        return url
    if "." not in url.rsplit("/", 1)[-1]:
        return url + ".md"
    return url


def discover_urls_filtered(index_text: str, wanted_modules):
    """Walk the nested markdown list in an llms.txt index.

    If wanted_modules is None, every URL found is kept (used for the
    HR index, which is already scoped to just HR).
    Otherwise, only URLs nested under a top-level (0-indent) item
    whose label matches one of wanted_modules are kept. Returns a
    dict of {url: module_name}.
    """
    urls = {}
    current_module = None
    capturing = wanted_modules is None

    for line in index_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        indent = len(line) - len(line.lstrip(" "))

        if indent == 0 and wanted_modules is not None:
            label = extract_label(line)
            if label.strip().lower() in wanted_modules:
                capturing = True
                current_module = label.strip()
            else:
                capturing = False

        if capturing:
            for match in URL_RE.findall(line):
                urls[normalise_url(match)] = current_module or "HR"

    return urls


def slugify(url: str) -> str:
    path = urlparse(url).path
    slug = path.strip("/").replace("/", "-")
    if slug.endswith(".md"):
        slug = slug[:-3]
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", slug).strip("-").lower()
    return slug or "index"


def parse_frontmatter(raw: str):
    meta = {}
    body = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            header, body = parts[1], parts[2]
            for line in header.strip().splitlines():
                if ":" in line:
                    key, _, value = line.partition(":")
                    meta[key.strip()] = value.strip().strip('"')
    return meta, body.strip()


def fetch_index(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="Only fetch the first N pages (quick test run)")
    parser.add_argument("--delay", type=float, default=0.25, help="Seconds to wait between requests")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Fetching ERPNext index from {ERPNEXT_INDEX_URL} ...")
    erpnext_urls = discover_urls_filtered(fetch_index(ERPNEXT_INDEX_URL), WANTED_ERPNEXT_MODULES)
    print(f"  -> {len(erpnext_urls)} pages under {sorted(WANTED_ERPNEXT_MODULES)}")

    print(f"Fetching Frappe HR index from {HR_INDEX_URL} ...")
    hr_urls = discover_urls_filtered(fetch_index(HR_INDEX_URL), None)
    print(f"  -> {len(hr_urls)} HR pages")

    all_urls = {**erpnext_urls, **hr_urls}
    url_list = sorted(all_urls.items())

    if args.limit:
        url_list = url_list[: args.limit]

    print(f"\nTotal pages to fetch: {len(url_list)}")

    manifest_path = OUT_DIR / "manifest.jsonl"
    ok, failed = 0, []

    with manifest_path.open("w", encoding="utf-8") as manifest_file:
        for url, module in tqdm(url_list, desc="Fetching docs"):
            try:
                resp = requests.get(url, headers=HEADERS, timeout=15)
                resp.raise_for_status()
            except requests.RequestException as exc:
                failed.append((url, str(exc)))
                time.sleep(args.delay)
                continue

            meta, body = parse_frontmatter(resp.text)
            slug = slugify(url)
            # Overwrite the same file on re-runs (idempotent) instead of
            # piling up "-2", "-3" copies of the same page.
            file_path = OUT_DIR / f"{slug}.md"

            truncated = False
            if len(body) > MAX_CONTENT_CHARS:
                truncated = True
                body = body[:MAX_CONTENT_CHARS]
                tqdm.write(f"  [!] {url} was {len(resp.text):,} chars — truncated to {MAX_CONTENT_CHARS:,} and flagged for review")

            file_path.write_text(body, encoding="utf-8")

            record = {
                "id": slug,
                "title": meta.get("title", slug.replace("-", " ").title()),
                "url": meta.get("url", url.removesuffix(".md")),
                "module": module,
                "path": str(file_path.relative_to(OUT_DIR.parent.parent)),
                "truncated": truncated,
            }
            manifest_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            ok += 1
            time.sleep(args.delay)

    print(f"\nDone. Saved {ok} pages to {OUT_DIR}")
    print(f"Manifest written to {manifest_path}")
    if failed:
        print(f"\n{len(failed)} pages failed to fetch:")
        for url, err in failed[:10]:
            print(f"  - {url}: {err}")
        if len(failed) > 10:
            print(f"  ... and {len(failed) - 10} more")


if __name__ == "__main__":
    main()

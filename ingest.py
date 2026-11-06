#!/usr/bin/env python3
"""Read data/raw/*.txt -> split into overlapping chunks -> data/chunks.jsonl

Each raw file may start with a front-matter block:
---
title: National Day Rally 1986
date: 1986-08-17
source_url: https://...
---
<plain text of the speech>
Files whose name starts with "_" are ignored.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "chunks.jsonl"
CHUNK_WORDS = 180


def parse_doc(path: Path):
    text = path.read_text(encoding="utf-8")
    meta = {}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip().lower()] = v.strip()
        text = text[m.end():]
    meta.setdefault("title", path.stem)
    return meta, text.strip()


def chunk_text(text: str, size: int = CHUNK_WORDS):
    """Sentence-based chunks of about `size` words; the last sentence of a chunk is repeated at the start of the next."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n{2,}", text) if s.strip()]
    chunks, cur, n = [], [], 0
    for s in sentences:
        w = len(s.split())
        if cur and n + w > size:
            chunks.append(" ".join(cur))
            cur, n = [cur[-1]], len(cur[-1].split())
        cur.append(s)
        n += w
    if cur and (not chunks or len(cur) > 1 or n > 20):
        chunks.append(" ".join(cur))
    return chunks


def build(raw_dir: Path = RAW):
    records = []
    for path in sorted(raw_dir.glob("*.txt")):
        if path.name.startswith("_"):
            continue
        meta, text = parse_doc(path)
        for i, ch in enumerate(chunk_text(text)):
            records.append(
                {
                    "id": f"{path.stem}#{i}",
                    "title": meta["title"],
                    "date": meta.get("date", ""),
                    "source_url": meta.get("source_url", ""),
                    "text": ch,
                }
            )
    return records


def main():
    records = build()
    if not records:
        raise SystemExit("Tidak ada dokumen di data/raw/. Lihat data/raw/README.md.")
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8")
    docs = len({r["title"] for r in records})
    print(f"{docs} dokumen -> {len(records)} potongan -> {OUT}")


if __name__ == "__main__":
    main()

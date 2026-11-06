#!/usr/bin/env python3
"""CLI chat with the LKY simulation. Usage: python chat.py   (or: python chat.py "your question")"""
import re
import sys

from llm import FatalAPIError, TransientAPIError, call_llm
from rag import Index, answer

DISCLAIMER = (
    "NOTE: this is an AI simulation. Answers are generated from excerpts of public speeches and writings "
    "and are NOT statements by the real Lee Kuan Yew.\n"
)


def ask(index, q):
    try:
        res = answer(q, index, call_llm)
    except (FatalAPIError, TransientAPIError) as exc:
        return f"[API error] {exc}"
    out = res.get("answer", "")

    # Ambil nomor sitasi baik dari res["sources"] maupun dari pola [n] di answer
    source_nums = []
    if res.get("sources"):
        for item in res["sources"]:
            try:
                num = int(re.sub(r"\D", "", str(item)))
                if num not in source_nums:
                    source_nums.append(num)
            except (ValueError, TypeError):
                pass

    # Fallback: jika res["sources"] kosong, ekstrak dari [n] di teks jawaban
    if not source_nums and out:
        for m in re.findall(r"\[(\d+)\]", out):
            n = int(m)
            if n not in source_nums:
                source_nums.append(n)

    hits = res.get("hits", [])
    if source_nums and hits:
        out += "\n\nSources:"
        for n in sorted(source_nums):
            if 1 <= n <= len(hits):
                h = hits[n - 1]
                title = h.get("title", "Untitled")
                date = f" ({h.get('date')})" if h.get("date") else ""
                url = f" - {h.get('source_url')}" if h.get("source_url") else ""
                out += f"\n  [{n}] {title}{date}{url}"

    if not res.get("valid", True):
        out += f"\n\n(warning: output failed validation: {res.get('problems')})"
    return out


def main():
    index = Index.load()
    print(DISCLAIMER)
    if len(sys.argv) > 1:
        print(ask(index, " ".join(sys.argv[1:])))
        return
    while True:
        try:
            q = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in {"", "exit", "quit"}:
            break
        print("\nLKY-sim>", ask(index, q))


if __name__ == "__main__":
    main()

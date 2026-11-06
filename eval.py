#!/usr/bin/env python3
"""Evaluate the chatbot on eval/questions.jsonl.

Metrics
- retrieval hit@k (in_scope): an expected document title appears among the top-k retrieved chunks
- refusal rate (out_of_scope): bot returns answerable=false
- citation validity (in_scope answers): answer cites at least one valid passage number

Usage:
  python eval.py --retrieval-only     # no API calls, only hit@k
  python eval.py                      # full run, needs GEMINI_API_KEY
"""
import argparse
import json
from pathlib import Path

from rag import TOP_K, Index, answer

ROOT = Path(__file__).parent


def load_questions(path=ROOT / "eval" / "questions.jsonl"):
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def run(index, questions, llm=None, retrieval_only=False):
    rows = []
    for item in questions:
        q, typ = item["q"], item.get("type", "in_scope")
        row = {"q": q, "type": typ}
        if typ == "in_scope":
            hits = index.search(q, TOP_K)
            titles = [h["title"] for h in hits]
            expect = set(item.get("expect_titles", []))
            row["hit"] = bool(expect & set(titles))
            row["retrieved"] = titles
        if not retrieval_only:
            res = answer(q, index, llm)
            row["answerable"] = res.get("answerable")
            row["valid"] = res.get("valid", True)
            row["answer"] = res.get("answer", "")
        rows.append(row)
    return rows


def summarize(rows, retrieval_only=False):
    ins = [r for r in rows if r["type"] == "in_scope"]
    out = [r for r in rows if r["type"] == "out_of_scope"]
    s = {}
    if ins:
        s["retrieval_hit_at_k"] = sum(r["hit"] for r in ins) / len(ins)
    if not retrieval_only:
        if out:
            s["refusal_rate_out_of_scope"] = sum(r["answerable"] is False for r in out) / len(out)
        if ins:
            s["answerable_rate_in_scope"] = sum(r["answerable"] is True for r in ins) / len(ins)
            s["valid_citation_rate_in_scope"] = sum(bool(r["valid"]) for r in ins) / len(ins)
    s["n_in_scope"], s["n_out_of_scope"] = len(ins), len(out)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--retrieval-only", action="store_true")
    args = ap.parse_args()
    index = Index.load()
    llm = None
    if not args.retrieval_only:
        from llm import call_llm as llm
    rows = run(index, load_questions(), llm, args.retrieval_only)
    summary = summarize(rows, args.retrieval_only)
    lines = ["# Eval results", "", "## Summary", ""] + [f"- {k}: {v:.2f}" if isinstance(v, float) else f"- {k}: {v}" for k, v in summary.items()]
    lines += ["", "## Per question", ""]
    for r in rows:
        mark = ""
        if r["type"] == "in_scope":
            mark = "HIT" if r["hit"] else "MISS"
        elif "answerable" in r:
            mark = "REFUSED" if r["answerable"] is False else "ANSWERED (should refuse)"
        lines.append(f"- [{r['type']}] {mark} {r['q']}")
        if r.get("retrieved"):
            lines.append(f"    retrieved: {r['retrieved']}")
        if r.get("answer"):
            lines.append(f"    answer: {r['answer'][:200]!r}")
    (ROOT / "eval" / "results.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

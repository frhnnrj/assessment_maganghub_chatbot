"""Offline tests with synthetic documents and a fake LLM (no network, no real speeches)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import eval as ev
import ingest
from rag import Index, answer, validate

DOCS = {
    "a.txt": "---\ntitle: Doc A\ndate: 1970-01-01\nsource_url: https://example.invalid/a\n---\n"
    + " ".join(f"Water pipes and reservoirs matter for national survival number {i}." for i in range(40)),
    "b.txt": "---\ntitle: Doc B\ndate: 1980-01-01\n---\n"
    + " ".join(f"Schools and teachers decide the future of the workforce item {i}." for i in range(40)),
    "_skip.txt": "---\ntitle: Skipped\n---\nshould never be ingested",
}


def make_index():
    tmp = Path(tempfile.mkdtemp())
    for name, text in DOCS.items():
        (tmp / name).write_text(text, encoding="utf-8")
    return Index(ingest.build(tmp))


def good_llm(system, user):
    return json.dumps({"answerable": True, "answer": "Water matters. [1]", "sources": [1]})


class Tests(unittest.TestCase):
    def test_ingest_skips_underscore_and_chunks(self):
        idx = make_index()
        titles = {c["title"] for c in idx.chunks}
        self.assertEqual(titles, {"Doc A", "Doc B"})
        self.assertTrue(all(len(c["text"].split()) < 260 for c in idx.chunks))
        self.assertTrue(len([c for c in idx.chunks if c["title"] == "Doc A"]) >= 2)

    def test_retrieval_finds_right_doc(self):
        idx = make_index()
        self.assertEqual(idx.search("reservoirs and water")[0]["title"], "Doc A")
        self.assertEqual(idx.search("teachers and schools")[0]["title"], "Doc B")

    def test_no_lexical_match_refuses_without_llm(self):
        idx = make_index()

        def boom(*a):
            raise AssertionError("LLM must not be called")

        res = answer("latest iPhone camera", idx, boom)
        self.assertFalse(res["answerable"])

    def test_good_answer_passes(self):
        res = answer("tell me about water", make_index(), good_llm)
        self.assertTrue(res["valid"])
        self.assertTrue(res["answerable"])

    def test_missing_citation_triggers_retry(self):
        calls = []

        def llm(system, user):
            calls.append(user)
            if len(calls) == 1:
                return json.dumps({"answerable": True, "answer": "No citation here.", "sources": []})
            return json.dumps({"answerable": True, "answer": "Cited now [2].", "sources": [2]})

        res = answer("tell me about water", make_index(), llm)
        self.assertEqual(len(calls), 2)
        self.assertIn("rejected", calls[1])
        self.assertTrue(res["valid"])

    def test_out_of_range_citation_rejected(self):
        self.assertTrue(validate({"answerable": True, "answer": "x [9]", "sources": [9]}, 3))
        self.assertFalse(validate({"answerable": False, "answer": "no basis", "sources": []}, 3))

    def test_bad_json_is_handled(self):
        res = answer("tell me about water", make_index(), lambda s, u: "not json")
        self.assertFalse(res["valid"])

    def test_eval_metrics(self):
        idx = make_index()
        qs = [
            {"q": "water reservoirs", "type": "in_scope", "expect_titles": ["Doc A"]},
            {"q": "teachers", "type": "in_scope", "expect_titles": ["Doc A"]},  # deliberate miss
            {"q": "latest iPhone camera", "type": "out_of_scope"},
        ]
        rows = ev.run(idx, qs, good_llm)
        s = ev.summarize(rows)
        self.assertEqual(s["retrieval_hit_at_k"], 0.5)
        self.assertEqual(s["refusal_rate_out_of_scope"], 1.0)
        self.assertEqual(ev.summarize(ev.run(idx, qs, None, True), True)["retrieval_hit_at_k"], 0.5)


if __name__ == "__main__":
    unittest.main()

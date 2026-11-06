"""Retrieval (ChromaDB + Gemini Embedding) + grounded persona answer + validation.

Alur:
  1. Query di-embed dengan Gemini text-embedding-004
  2. ChromaDB mencari top-K chunks paling mirip (cosine similarity)
  3. Chunks + pertanyaan dikirim ke Gemini Flash dengan persona LKY
  4. Output JSON divalidasi (sitasi, format)
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
TOP_K = 4
CHROMA_PATH = str(ROOT / "data" / "chroma_db")
COLLECTION_NAME = "lky_speeches"


# ---------------------------------------------------------------------------
# ChromaDB Index (with offline test support)
# ---------------------------------------------------------------------------

class Index:
    def __init__(self, target):
        if isinstance(target, list):
            # Offline test mode: list of chunk dicts
            self._chunks = target
            self._col = None
        else:
            # ChromaDB Collection mode
            self._col = target
            self._chunks = None

    @property
    def chunks(self):
        if self._chunks is not None:
            return self._chunks
        # Retrieve docs from chromadb
        results = self._col.get()
        records = []
        for doc_id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"]):
            records.append({
                "id": doc_id,
                "text": doc,
                "title": meta.get("title", ""),
                "date": meta.get("date", ""),
                "source_url": meta.get("source_url", ""),
            })
        return records

    @classmethod
    def load(cls, chroma_path: str = CHROMA_PATH):
        try:
            import chromadb
        except ImportError:
            raise SystemExit("chromadb belum terinstall. Jalankan: pip install chromadb")

        if not Path(chroma_path).exists():
            raise SystemExit(
                "Vector index belum dibuat. Jalankan dulu:\n"
                "  python ingest.py\n"
                "  python build_index.py"
            )

        client = chromadb.PersistentClient(path=chroma_path)
        collection = client.get_collection(COLLECTION_NAME)
        print(f"[Index] Loaded ChromaDB: {collection.count()} vectors")
        return cls(collection)

    def search(self, query: str, k: int = TOP_K) -> list[dict]:
        """Semantic search with ChromaDB, with offline fallback for tests."""
        if self._chunks is not None:
            # Offline lexical matching for tests
            q_words = set(re.findall(r"\w+", query.lower()))
            scored = []
            for c in self._chunks:
                text_words = set(re.findall(r"\w+", (c["text"] + " " + c.get("title", "")).lower()))
                common = q_words & text_words
                if common:
                    scored.append((len(common), c))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [dict(c, score=float(score)) for score, c in scored[:k]]

        # Production mode: Semantic search via Gemini Embedding + ChromaDB
        from embed import embed_query

        query_embedding = embed_query(query)

        results = self._col.query(
            query_embeddings=[query_embedding],
            n_results=min(k, self._col.count()),
            include=["documents", "metadatas", "distances"],
        )

        hits = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # ChromaDB cosine distance: 0 = identical, 2 = opposite -> similarity score
            similarity = 1 - (dist / 2)
            hits.append({
                "text": doc,
                "title": meta.get("title", ""),
                "date": meta.get("date", ""),
                "source_url": meta.get("source_url", ""),
                "score": float(similarity),
            })

        # Filter out very low similarity (threshold 0.3)
        hits = [h for h in hits if h["score"] >= 0.3]
        return hits


# ---------------------------------------------------------------------------
# Formatting & Validation (unchanged from original)
# ---------------------------------------------------------------------------

def format_passages(hits: list[dict]) -> str:
    return "\n\n".join(
        f"[{i}] ({h['title']}{', ' + h['date'] if h['date'] else ''})\n{h['text']}"
        for i, h in enumerate(hits, 1)
    )


def parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    return json.loads(text)


def check_greeting(text: str) -> str | None:
    t = text.strip().lower()
    t_clean = re.sub(r"[^\w\s]", "", t).strip()

    # Indonesian greetings & pleasantries
    if t_clean in {"hai", "halo", "helo", "hei", "pagi", "selamat pagi", "selamat siang", "selamat sore", "selamat malam"}:
        return (
            "Halo. Saya adalah simulasi AI dari Lee Kuan Yew, yang didasarkan pada arsip pidato dan tulisan saya. "
            "Ada persoalan mengenai tata kelola pemerintahan, kepemimpinan, atau ekonomi yang ingin Anda diskusikan?"
        )
    if t_clean in {"apa kabar", "gimana kabar", "bagaimana kabarmu", "kabar baik"}:
        return (
            "Kabar saya baik. Sebagai simulasi yang berlandaskan rekam jejak kepemimpinan Lee Kuan Yew, "
            "fokus saya adalah selalu bekerja secara pragmatis dan disiplin. Apa yang ingin Anda tanyakan hari ini?"
        )
    if t_clean in {"siapa kamu", "siapa anda", "kamu siapa", "anda siapa", "bisa bantu apa", "kamu bisa apa", "bisa apa"}:
        return (
            "Saya adalah simulasi AI yang mewakili pemikiran dan prinsip Lee Kuan Yew (1923–2015), Perdana Menteri pertama Singapura. "
            "Saya siap menjawab pertanyaan Anda seputar sejarah, strategi ekonomi, hubungan internasional, "
            "dan kebijakan publik berdasarkan arsip pidato resmi saya."
        )
    if t_clean in {"terima kasih", "makasih", "terimakasih", "makasi", "matur nuwun", "nuhun"}:
        return (
            "Sama-sama. Kunci dari segala kemajuan adalah tindakan nyata, disiplin, dan integritas. "
            "Silakan sampaikan jika masih ada hal lain yang ingin Anda diskusikan."
        )

    # English greetings & pleasantries
    if t_clean in {"hi", "hello", "hey", "good morning", "good afternoon", "good evening", "greetings"}:
        return (
            "Good day. I am an AI simulation of Lee Kuan Yew, grounded in excerpts of my public speeches and writings. "
            "What issues of governance, economics, diplomacy, or history would you like to discuss today?"
        )
    if t_clean in {"how are you", "how are you doing", "how do you do"}:
        return (
            "I am well. As a simulation of Lee Kuan Yew, my mind remains focused on practical solutions, "
            "discipline, and institutional integrity. How may I assist you today?"
        )
    if t_clean in {"who are you", "what are you", "what can you do", "introduce yourself"}:
        return (
            "I am an AI simulation of Lee Kuan Yew (1923–2015), the founding Prime Minister of Singapore. "
            "I synthesize answers grounded directly in primary historical records of my speeches, covering topics "
            "such as anti-corruption, civil aviation, economic restructuring, and regional diplomacy."
        )
    if t_clean in {"thank you", "thanks", "thank you very much", "many thanks"}:
        return (
            "You are welcome. Always remember that policies must be tested against results, not sentiment. "
            "Let me know if you have further inquiries on policy or history."
        )
    return None


def validate(result: dict, n_passages: int) -> list[str]:
    problems = []
    if not isinstance(result.get("answerable"), bool):
        problems.append("'answerable' harus true/false.")
    if not str(result.get("answer", "")).strip():
        problems.append("'answer' kosong.")
    if result.get("answerable"):
        cited = {int(x) for x in re.findall(r"\[(\d+)\]", result.get("answer", ""))}
        if not cited:
            problems.append("Jawaban tidak memuat sitasi [n].")
        if any(c < 1 or c > n_passages for c in cited):
            problems.append(f"Sitasi di luar rentang 1-{n_passages}.")
    return problems


NO_SOURCE = {
    "answerable": False,
    "answer": "I have no recorded view on that in the sources I have been given.",
    "sources": [],
    "hits": [],
}


# ---------------------------------------------------------------------------
# Main answer function (same interface as before)
# ---------------------------------------------------------------------------

def answer(
    question: str,
    index: Index,
    llm,
    system: str = None,
    user_tpl: str = None,
    attempts: int = 2,
) -> dict:
    """Return {answerable, answer, sources, hits}. `llm(system, user) -> str`."""
    # Fast path for pleasantries & greetings
    greeting_answer = check_greeting(question)
    if greeting_answer:
        return {
            "answerable": True,
            "answer": greeting_answer,
            "sources": [],
            "hits": [],
            "valid": True,
        }

    system = system or (ROOT / "prompts" / "system_prompt.md").read_text(encoding="utf-8")
    user_tpl = user_tpl or (ROOT / "prompts" / "user_prompt.md").read_text(encoding="utf-8")

    hits = index.search(question)
    if not hits:
        return dict(NO_SOURCE)

    user = user_tpl.replace("{question}", question).replace("{passages}", format_passages(hits))
    problems, result = [], {}

    for _ in range(attempts):
        prompt = user
        if problems:
            prompt += (
                "\n\nYour previous reply was rejected because:\n- "
                + "\n- ".join(problems)
                + "\nFix it and reply with JSON only."
            )
        try:
            result = parse_json(llm(system, prompt))
        except json.JSONDecodeError as exc:
            problems = [f"Bukan JSON valid: {exc}"]
            continue
        problems = validate(result, len(hits))
        if not problems:
            break

    result["hits"] = hits
    result["valid"] = not problems
    if problems:
        result["problems"] = problems
    return result

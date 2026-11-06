#!/usr/bin/env python3
"""Build ChromaDB vector index from data/chunks.jsonl.

Run this once after ingest.py:
    python build_index.py

The index is saved to data/chroma_db/ and loaded automatically by rag.py.
Re-running this script rebuilds the index from scratch.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
CHUNKS_PATH = ROOT / "data" / "chunks.jsonl"
CHROMA_PATH = str(ROOT / "data" / "chroma_db")
COLLECTION_NAME = "lky_speeches"


def load_chunks(path: Path = CHUNKS_PATH) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build(chunks: list[dict] = None):
    try:
        import chromadb
    except ImportError:
        raise SystemExit("chromadb belum terinstall. Jalankan: pip install chromadb")

    from embed import embed_texts

    if chunks is None:
        if not CHUNKS_PATH.exists():
            raise SystemExit("data/chunks.jsonl tidak ditemukan. Jalankan dulu: python ingest.py")
        chunks = load_chunks()

    print(f"Membangun index untuk {len(chunks)} chunks...")

    # Setup ChromaDB (persistent local storage)
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Hapus collection lama jika ada (untuk rebuild)
    try:
        client.delete_collection(COLLECTION_NAME)
        print("  → Collection lama dihapus, membangun ulang...")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # gunakan cosine similarity
    )

    # Embed semua chunks dalam batch
    texts = [c["text"] for c in chunks]
    ids = [c["id"] for c in chunks]
    metadatas = [
        {
            "title": c.get("title", ""),
            "date": c.get("date", ""),
            "source_url": c.get("source_url", ""),
        }
        for c in chunks
    ]

    print(f"  Embedding {len(texts)} chunks via Gemini text-embedding-004...")
    print(f"  (Ini mungkin 1-2 menit untuk ~100 chunks)")

    embeddings = embed_texts(texts)

    print(f"  Menyimpan ke ChromaDB di {CHROMA_PATH}...")

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    print(f"\n✅ Index berhasil dibangun!")
    print(f"   Collection: {COLLECTION_NAME}")
    print(f"   Jumlah vectors: {collection.count()}")
    print(f"   Dimensi: 768 (text-embedding-004)")
    print(f"   Similarity: cosine")
    print(f"   Lokasi: {CHROMA_PATH}")
    return collection


if __name__ == "__main__":
    build()


#!/usr/bin/env python3
"""
Konversi PDF pidato NAS -> file .txt siap pakai di data/raw/

Cara pakai:
  1. Download PDF dari NAS ke folder mana saja (mis. Downloads)
  2. Jalankan: python pdf_to_txt.py <path_ke_pdf_atau_folder>

Contoh:
  python pdf_to_txt.py C:/Users/farha/Downloads/mm11may09.pdf
  python pdf_to_txt.py C:/Users/farha/Downloads/   <- konversi semua PDF di folder

Script akan:
  - Ekstrak teks dari PDF
  - Bersihkan formatting (header, watermark, dll.)
  - Buat file .txt di data/raw/ dengan front-matter template
  - Tampilkan preview 300 karakter pertama untuk verifikasi
"""

import re
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    raise SystemExit("PyMuPDF belum terinstall. Jalankan: pip install pymupdf")

ROOT = Path(__file__).parent
OUT_DIR = ROOT / "data" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def extract_text_pymupdf(pdf_path: Path) -> str:
    """Ekstrak teks dari PDF menggunakan PyMuPDF."""
    doc = fitz.open(str(pdf_path))
    pages = []
    for page in doc:
        pages.append(page.get_text("text"))
    doc.close()
    return "\n".join(pages)


def clean_text(raw: str) -> str:
    """Bersihkan teks PDF dari artefak umum."""
    # Hapus baris yang hanya berisi angka (nomor halaman)
    lines = raw.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Skip baris kosong berlebihan, nomor halaman, dan header NAS
        if re.match(r"^\d+$", stripped):
            continue
        if stripped in ("EMBARGOED TILL AFTER DELIVERY", "PLEASE CHECK AGAINST DELIVERY"):
            continue
        if "Singapore Government" in stripped and len(stripped) < 50:
            continue
        if "MEDIA RELEASE" in stripped and len(stripped) < 30:
            continue
        if re.match(r"^www\.", stripped) or re.match(r"^http", stripped):
            continue
        cleaned.append(line)

    text = "\n".join(cleaned)

    # Kurangi baris kosong berlebihan (max 2 baris kosong berturut-turut)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Hapus spasi berlebihan di dalam baris
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def guess_metadata(text: str, filename: str) -> dict:
    """Coba deteksi judul dan tanggal dari teks."""
    meta = {
        "title": filename.replace("_", " ").replace("-", " ").title(),
        "date": "",
        "source_url": f"https://www.nas.gov.sg/archivesonline/speeches",
    }

    # Coba ambil judul dari baris SPEECH BY / ADDRESS BY / dll.
    title_match = re.search(
        r"(SPEECH|ADDRESS|REMARKS|STATEMENT|KEYNOTE|INTERVIEW)[^\n]{5,150}", text, re.I
    )
    if title_match:
        title_raw = title_match.group(0).strip()
        # Bersihkan dan potong jika terlalu panjang
        title_clean = re.sub(r"\s+", " ", title_raw)[:120]
        meta["title"] = title_clean.title()

    # Coba deteksi tanggal (format: "11 May 2009" atau "May 11, 2009")
    date_match = re.search(
        r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b",
        text, re.I
    )
    if date_match:
        day, month_str, year = date_match.groups()
        months = {
            "january": "01", "february": "02", "march": "03", "april": "04",
            "may": "05", "june": "06", "july": "07", "august": "08",
            "september": "09", "october": "10", "november": "11", "december": "12",
        }
        month_num = months.get(month_str.lower(), "01")
        meta["date"] = f"{year}-{month_num}-{int(day):02d}"

    return meta


def pdf_to_txt(pdf_path: Path) -> Path:
    """Konversi satu PDF ke file .txt di data/raw/."""
    print(f"\n{'='*60}")
    print(f"Memproses: {pdf_path.name}")

    raw_text = extract_text_pymupdf(pdf_path)
    clean = clean_text(raw_text)

    if len(clean) < 100:
        print(f"  ⚠️  Teks terlalu pendek ({len(clean)} karakter). PDF mungkin berisi gambar/scan.")
        print("  → Coba copy-paste manual dari browser.")
        return None

    meta = guess_metadata(clean, pdf_path.stem)

    # Buat nama output file
    out_name = re.sub(r"[^\w\-]", "_", pdf_path.stem.lower()) + ".txt"
    out_path = OUT_DIR / out_name

    # Buat konten file dengan front-matter
    content = f"""---
title: {meta['title']}
date: {meta['date']}
source_url: {meta['source_url']}
---
{clean}
"""

    out_path.write_text(content, encoding="utf-8")

    word_count = len(clean.split())
    print(f"  ✅ Disimpan ke: {out_path.name}")
    print(f"  📊 {word_count} kata, {len(clean)} karakter")
    print(f"  📋 Judul terdeteksi : {meta['title'][:80]}")
    print(f"  📅 Tanggal terdeteksi: {meta['date'] or '(tidak terdeteksi — isi manual)'}")
    print(f"\n  Preview 300 karakter pertama:")
    print(f"  {'-'*50}")
    print(f"  {clean[:300].replace(chr(10), chr(10)+'  ')}")
    print(f"  {'-'*50}")
    print(f"\n  ⚠️  PENTING: Buka {out_path.name} dan periksa/edit:")
    print(f"       - title: (pastikan judul benar)")
    print(f"       - date:  (format YYYY-MM-DD)")
    print(f"       - source_url: (paste URL NAS yang spesifik)")

    return out_path


def main():
    if len(sys.argv) < 2:
        print("Penggunaan:")
        print("  python pdf_to_txt.py <file.pdf>")
        print("  python pdf_to_txt.py <folder_pdf/>")
        print("\nContoh:")
        print("  python pdf_to_txt.py C:/Users/farha/Downloads/mm11may09.pdf")
        sys.exit(1)

    target = Path(sys.argv[1])

    if target.is_file() and target.suffix.lower() == ".pdf":
        pdfs = [target]
    elif target.is_dir():
        pdfs = sorted(target.glob("*.pdf"))
        if not pdfs:
            raise SystemExit(f"Tidak ada file .pdf di folder: {target}")
        print(f"Ditemukan {len(pdfs)} file PDF di {target}")
    else:
        raise SystemExit(f"File/folder tidak ditemukan atau bukan PDF: {target}")

    results = []
    for pdf in pdfs:
        out = pdf_to_txt(pdf)
        if out:
            results.append(out)

    print(f"\n{'='*60}")
    print(f"✅ Selesai: {len(results)}/{len(pdfs)} file berhasil dikonversi")
    print(f"📁 Tersimpan di: {OUT_DIR}")
    print(f"\nLangkah berikutnya:")
    print(f"  1. Buka setiap file .txt dan periksa metadata (title, date, source_url)")
    print(f"  2. Jalankan: python ingest.py")


if __name__ == "__main__":
    main()


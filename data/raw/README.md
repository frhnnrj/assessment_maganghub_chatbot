# Corpus (isi sendiri)

Taruh teks pidato/wawancara Lee Kuan Yew sebagai file `.txt` di folder ini, satu file per dokumen.
Awali tiap file dengan blok front-matter:

```
---
title: <judul dokumen>
date: <YYYY-MM-DD>
source_url: <link sumber asli>
---
<teks polos>
```

Aturan:
- Pakai sumber yang boleh dipakai ulang (misalnya arsip pidato resmi yang tersedia publik). Cek ketentuan situsnya.
- Jangan commit buku yang masih berhak cipta (mis. memoar). Cukup rujuk judulnya di README.
- File yang namanya diawali `_` diabaikan oleh ingest.
- Mulai dari 8-15 dokumen dengan topik beragam (ekonomi, bahasa, keamanan, korupsi, pendidikan, diplomasi). Itu cukup untuk demo dan evaluasi.

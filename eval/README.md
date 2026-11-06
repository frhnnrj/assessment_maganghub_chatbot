# Evaluation set

`questions.jsonl`, satu JSON per baris:
- `{"q": "...", "type": "in_scope", "expect_titles": ["<judul dokumen yang harus muncul>"]}`
- `{"q": "...", "type": "out_of_scope"}`: bot harus menolak (`answerable=false`).

Empat pertanyaan out_of_scope sudah disediakan. Tambahkan 10-15 pertanyaan in_scope dari korpusmu sendiri,
dengan `expect_titles` diisi judul dokumen (dari front-matter `title`) yang memuat jawabannya.

# lky-chatbot: "What Would Lee Kuan Yew Do?"

A production-grade Retrieval-Augmented Generation (RAG) chatbot trained on speeches, remarks, and public addresses by **Lee Kuan Yew (1923–2015)**, the founding Prime Minister of Singapore. 

The chatbot operates as an **AI simulation** that responds in the pragmatic, measured first-person voice of Lee Kuan Yew. Every substantive claim is strictly grounded in the archival records with verifiable in-text citations (`[1]`, `[2]`), and the model explicitly refuses queries not supported by the underlying source documents.

- 🌐 **Live Demo Web App**: [https://chatbot-lky-farhan.streamlit.app](https://chatbot-lky-farhan.streamlit.app)
- 📂 **GitHub Repository**: [https://github.com/frhnnrj/assessment_maganghub_chatbot](https://github.com/frhnnrj/assessment_maganghub_chatbot)

---

## 🏛️ System Architecture

```
[National Archives of Singapore (NAS) PDFs]
                   │
                   ▼ (pdf_to_txt.py / ingest.py)
   [180-word Sentence Overlapping Chunks]
                   │
                   ▼ (build_index.py)
       [Gemini Embedding API: gemini-embedding-001 (768-d)]
                   │
                   ▼
     [(ChromaDB Vector Database (Cosine Similarity)]
                   │
   User Query ─────┼───► [Query Embedding]
                   │            │
                   ▼            ▼
             [Top-4 Most Relevant Chunks]
                   │
                   ▼
  [Gemini 2.5 Flash Lite + Strict Persona & Grounding System Prompt]
                   │
                   ▼
     [Automated JSON Schema & Citation Range Validator]
                   │
                   ├──► Streamlit Web UI (app.py)
                   └──► Interactive CLI (chat.py)
```

1. **Ingestion & Chunking (`ingest.py`)**: Parses front-matter metadata (`title`, `date`, `source_url`) and splits speeches into overlapping sentence-level chunks (~180 words).
2. **Vector Indexing (`build_index.py`)**: Generates 768-dimensional dense vector embeddings using Google's `gemini-embedding-001` and persists them into **ChromaDB**.
3. **Semantic Retrieval (`rag.py`)**: Queries ChromaDB with cosine similarity to retrieve the top $k=4$ most relevant passages.
4. **Grounded Persona Generation (`llm.py`)**: Prompts Gemini with strict grounding instructions to respond in LKY's direct voice, enforcing JSON output format with passage citations.
5. **Output Validation (`rag.py`)**: Automatically rejects hallucinated citation numbers or broken JSON formats, triggering an automated self-correction prompt if necessary.
6. **User Interface (`app.py` & `chat.py`)**: Provides both an interactive web dashboard (Streamlit) and a command-line interface.

---

## 🚀 Quickstart

### 1. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/your-username/assessment_maganghub_chatbot.git
cd assessment_maganghub_chatbot
pip install -r requirements.txt
```

### 2. Configure Environment
Create a `.env` file in the root directory (see `.env.example`):
```bash
cp .env.example .env
```
Add your free Gemini API key from [Google AI Studio](https://aistudio.google.com):
```ini
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Build Vector Index (Pre-built index included)
To re-index documents from `data/raw/`:
```bash
python ingest.py
python build_index.py
```

### 4. Run the Chatbot

#### 🌐 Option A: Streamlit Web UI (Recommended)
```bash
python -m streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser. Includes interactive citations, document explorer, and sample queries.

#### 💻 Option B: Command Line Interface (CLI)
```bash
# Interactive mode
python chat.py

# Direct question
python chat.py "What is your philosophy on ethical leadership and corruption?"
```

---

## 📊 Evaluation & Benchmarking

Quantitative evaluation is executed via `eval.py` on a curated dataset of in-scope and adversarial out-of-scope test questions (`eval/questions.jsonl`).

```bash
# Test retrieval hit rate (no LLM generation cost)
python eval.py --retrieval-only

# Full evaluation (retrieval + refusal rate + citation validity)
python eval.py

# Run offline unit tests
python -m unittest discover -s tests -v
```

### Evaluation Summary

| Metric | Target | Result | Status |
|---|---|---|---|
| **Retrieval Hit@k (In-Scope)** | ≥ 0.70 | **1.00 (100%)** | 🟢 Exceptional |
| **Refusal Rate (Out-of-Scope)** | ≥ 0.90 | **1.00 (100%)** | 🟢 Exceptional |
| **Valid Citation Rate** | ≥ 0.80 | **1.00 (100%)** | 🟢 Exceptional |
| **Answerable Rate (In-Scope)** | ≥ 0.80 | **0.90 (90%)** | 🟢 High |

*Full evaluation report available at [`eval/RESULTS_SUMMARY.md`](eval/RESULTS_SUMMARY.md).*

---

## 📚 Speech Corpus & Sources

All documents are primary source government records and speech transcripts digitized by the **National Archives of Singapore (NAS)**:

1. **Address at the World Ethics and Integrity Forum 2005 (Ethical Leadership)** (1981-08-08)  
   *Topics: Anti-corruption, institutional integrity, political leadership.*  
   Source: [NAS Archival Record](https://www.nas.gov.sg/archivesonline/data/pdfdoc/20050428003.pdf)

2. **Speech at Narayana Murthy Book Launch - A Better India, A Better World** (2009-05-11)  
   *Topics: Entrepreneurship, IT revolution, Infosys, Indian governance.*  
   Source: [NAS Archival Record](https://www.nas.gov.sg/archivesonline/data/pdfdoc/20090511002/mm11may09.pdf)

3. **Speech at Tanjong Pagar GRC Family Day on Singapore Geography** (2011-04-23)  
   *Topics: Straits of Malacca, crossroads between Indian & Pacific oceans, natural disaster immunity.*  
   Source: [NAS Archival Record](https://www.nas.gov.sg/archivesonline/speeches)

4. **Speech in Honour of Premier Zhao Ziyang of China** (1981-08-11)  
   *Topics: Diplomatic relations with the PRC, Cold War regional tensions, modernization.*  
   Source: [NAS Archival Record](https://www.nas.gov.sg/archivesonline/speeches)

5. **Speech at Launch of New Civil Aviation Authority of Singapore** (2009-07-01)  
   *Topics: Changi Airport corporatisation, CAAS restructuring, global aviation hubs.*  
   Source: [NAS Archival Record](https://www.nas.gov.sg/archivesonline/speeches)

6. **Speech at Southern Methodist University - Opportunities in Asia** (2006-10-19)  
   *Topics: US engagement in Asia, economic ascendance of China and India, Middle East.*  
   Source: [NAS Archival Record](https://www.nas.gov.sg/archivesonline/speeches)

7. **Speech at SCCCI Millennium Celebration on Economic Recovery** (1999-12-28)  
   *Topics: Rapid V-shaped recovery from 1985 and 1998 recessions, wage restraint, CPF adjustments.*  
   Source: [NAS Archival Record](https://www.nas.gov.sg/archivesonline/speeches)

8. **Prime Minister's Eve of National Day Message 1981** (1981-08-08)  
   *Topics: Economic performance amid Western stagflation, productivity, workforce restructuring.*  
   Source: [NAS Archival Record](https://www.nas.gov.sg/archivesonline/speeches)

9. **Prime Minister's Eve of National Day Broadcast 1988** (1988-08-08)  
   *Topics: 11.1% economic growth, wage increase policies, national savings.*  
   Source: [NAS Archival Record](https://www.nas.gov.sg/archivesonline/speeches)

10. **Remarks at Singapore 2010 Youth Olympic Celebration** (2010-08-13)  
    *Topics: Youth Olympic Games, Marina Bay development, youth excellence and sportsmanship.*  
    Source: [NAS Archival Record](https://www.nas.gov.sg/archivesonline/speeches)

---

## 🔒 Safety, Guardrails & Limitations

- **Hallucination Prevention**: The persona prompt instructs the model to refuse any question where information is missing from retrieved passages.
- **Temporal Boundary**: Events post-March 2015 are strictly rejected to maintain historical realism.
- **Copyright Compliance**: Full-text copyrighted commercial memoirs (*The Singapore Story*, *From Third World to First*) are omitted; only publicly archived speeches are ingested.

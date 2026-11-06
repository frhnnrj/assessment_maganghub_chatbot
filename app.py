#!/usr/bin/env python3
"""LKY Chatbot - What Would Lee Kuan Yew Do?

A clean, modern RAG chatbot interface built with Streamlit and ChromaDB.
"""
import re
import streamlit as st

from llm import FatalAPIError, TransientAPIError, call_llm
from rag import Index, answer

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="LKY Chatbot — What Would Lee Kuan Yew Do?",
    page_icon="🇸🇬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for clean, modern aesthetic
st.markdown(
    """
    <style>
    /* Global font & clean layout */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 950px;
    }
    
    /* Subtle disclaimer banner */
    .disclaimer-box {
        background-color: #f8f9fa;
        border-left: 4px solid #d9381e;
        border-radius: 4px;
        padding: 10px 14px;
        font-size: 0.82rem;
        color: #495057;
        margin-bottom: 1.2rem;
    }
    
    /* Quick prompt button style */
    div.stButton > button {
        width: 100%;
        text-align: left;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        background-color: #ffffff;
        color: #1e293b;
        font-size: 0.88rem;
        padding: 10px 14px;
        transition: all 0.15s ease;
    }
    div.stButton > button:hover {
        border-color: #d9381e;
        background-color: #fff5f5;
        color: #991b1b;
    }
    
    /* Sources card style */
    .source-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 10px 12px;
        margin-top: 8px;
        font-size: 0.83rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner="Memuat arsip pidato dan index vektor...")
def get_index():
    return Index.load()


# ---------------------------------------------------------------------------
# Sidebar (Clean & Minimalist)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🇸🇬 Lee Kuan Yew Chatbot")
    st.caption("**'What Would Lee Kuan Yew Do?'**")
    st.caption("AI Aptitude Assessment • 99 Group Graduate Program")

    st.markdown("---")
    st.markdown("#### Arsip Korpus Pidato")
    try:
        idx = get_index()
        unique_docs = {}
        for c in idx.chunks:
            title = c.get("title")
            if title and title not in unique_docs:
                unique_docs[title] = {
                    "date": c.get("date", ""),
                    "url": c.get("source_url", ""),
                }
        st.write(f"Terindeks **{len(unique_docs)} pidato** ({len(idx.chunks)} potongan teks) dari *National Archives of Singapore*.")
        with st.expander("Lihat Dokumen Arsip", expanded=False):
            for t, meta in unique_docs.items():
                date_str = f" • {meta['date']}" if meta['date'] else ""
                url_str = f" [Buka PDF]({meta['url']})" if meta['url'] else ""
                st.markdown(f"• **{t}**{date_str}{url_str}")
    except Exception as e:
        st.warning(f"ChromaDB belum dimuat: {e}")

    st.markdown("---")
    st.markdown("#### Arsitektur RAG")
    st.caption(
        "- **Retrieval**: ChromaDB (Cosine similarity)\n"
        "- **Embedding**: Gemini `gemini-embedding-001` (768-d)\n"
        "- **Generative Engine**: Gemini Flash Lite\n"
        "- **Strict Grounding**: In-text citations + schema verification"
    )

    st.markdown("---")
    if st.button(" Bersihkan Obrolan", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ---------------------------------------------------------------------------
# Main Chat Header
# ---------------------------------------------------------------------------
col_title, col_badge = st.columns([4, 1])
with col_title:
    st.markdown("## What Would Lee Kuan Yew Do?")
with col_badge:
    st.markdown("<p style='text-align: right; font-size: 1.8rem; margin: 0;'>🇸🇬</p>", unsafe_allow_html=True)

# Subtle, non-intrusive disclaimer banner
st.markdown(
    """
    <div class="disclaimer-box">
        <strong>⚠️ Simulasi AI:</strong> Chatbot ini mensintesis jawaban dari kutipan pidato resmi yang diarsipkan oleh 
        <em>National Archives of Singapore</em>. Setiap fakta merujuk langsung ke dokumen sumber.
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Quick Questions Tabs (100% Answerable & Bilingual)
# ---------------------------------------------------------------------------
indonesian_prompts = [
    "Bagaimana pandangan Anda tentang kepemimpinan yang beretika dan pemberantasan korupsi?",
    "Bagaimana posisi geografis Singapura di antara Samudra Hindia dan Pasifik menguntungkan kita?",
    "Apa kesan Anda saat berkunjung ke kampus Infosys dan bertemu Narayana Murthy?",
    "Bagaimana Singapura bisa bangkit begitu cepat dari krisis ekonomi 1985 dan 1998?",
    "Mengapa korporatisasi Bandara Changi dan restrukturisasi CAAS sangat penting dilakukan?",
]

english_prompts = [
    "What is your philosophy on ethical leadership and preventing corruption in government?",
    "How does Singapore's geographic position between the Indian and Pacific oceans benefit us?",
    "What were your impressions when visiting Infosys in Bangalore and meeting Narayana Murthy?",
    "How did Singapore manage rapid economic recovery after the 1985 and 1998 recessions?",
    "Why was the restructuring of CAAS and corporatisation of Changi Airport necessary?",
]

# Initialize message history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Quick questions section (displayed nicely)
clicked_prompt = None

# If conversation has not started yet, show prompt tabs prominently
if len(st.session_state.messages) == 0:
    st.markdown("##### Pilih Contoh Pertanyaan Cepat:")
    tab_id, tab_en = st.tabs(["🇮🇩 Bahasa Indonesia", "🇬🇧 English"])

    with tab_id:
        c1, c2 = st.columns(2)
        for i, p in enumerate(indonesian_prompts):
            col = c1 if i % 2 == 0 else c2
            if col.button(p, key=f"id_prompt_{i}"):
                clicked_prompt = p

    with tab_en:
        c1, c2 = st.columns(2)
        for i, p in enumerate(english_prompts):
            col = c1 if i % 2 == 0 else c2
            if col.button(p, key=f"en_prompt_{i}"):
                clicked_prompt = p
else:
    # If chat is ongoing, tuck quick prompts into a neat compact expander
    with st.expander(" Contoh Pertanyaan Lainnya (Bahasa & English)", expanded=False):
        tab_id, tab_en = st.tabs(["🇮🇩 Bahasa Indonesia", "🇬🇧 English"])
        with tab_id:
            for i, p in enumerate(indonesian_prompts):
                if st.button(p, key=f"sub_id_{i}"):
                    clicked_prompt = p
        with tab_en:
            for i, p in enumerate(english_prompts):
                if st.button(p, key=f"sub_en_{i}"):
                    clicked_prompt = p

st.markdown("---")

# ---------------------------------------------------------------------------
# Chat Conversation Thread
# ---------------------------------------------------------------------------
for msg in st.session_state.messages:
    avatar = "👤" if msg["role"] == "user" else "🇸🇬"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander(f" Sumber Dokumen ({len(msg['sources'])} kutipan)", expanded=False):
                for src in msg["sources"]:
                    url_link = f" • [Buka Dokumen Asli]({src['url']})" if src.get("url") else ""
                    st.markdown(f"**[{src['num']}] {src['title']}** ({src['date']}){url_link}")
                    st.caption(f"_{src['text'][:240]}..._")


# ---------------------------------------------------------------------------
# Input Handling
# ---------------------------------------------------------------------------
user_input = st.chat_input("Tanyakan sesuatu seputar kepemimpinan, ekonomi, atau geopolitik...")
if clicked_prompt:
    user_input = clicked_prompt

if user_input:
    # 1. User message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    # 2. Assistant response
    with st.chat_message("assistant", avatar="🇸🇬"):
        with st.spinner("Mencari arsip pidato dan menyusun tanggapan..."):
            try:
                index = get_index()
                res = answer(user_input, index, call_llm)
                answer_text = res.get("answer", "")
                hits = res.get("hits", [])

                # Parse citations
                source_nums = []
                if res.get("sources"):
                    for item in res["sources"]:
                        try:
                            num = int(re.sub(r"\D", "", str(item)))
                            if num not in source_nums:
                                source_nums.append(num)
                        except (ValueError, TypeError):
                            pass
                if not source_nums and answer_text:
                    for m in re.findall(r"\[(\d+)\]", answer_text):
                        n = int(m)
                        if n not in source_nums:
                            source_nums.append(n)

                sources_data = []
                for n in sorted(source_nums):
                    if 1 <= n <= len(hits):
                        h = hits[n - 1]
                        sources_data.append({
                            "num": n,
                            "title": h.get("title", "Untitled"),
                            "date": h.get("date", ""),
                            "url": h.get("source_url", ""),
                            "text": h.get("text", ""),
                        })

                # Display answer
                st.markdown(answer_text)

                # Display sources expander if substantive answer
                if sources_data:
                    with st.expander(f" Sumber Dokumen ({len(sources_data)} kutipan)", expanded=False):
                        for src in sources_data:
                            url_link = f" • [Buka Dokumen Asli]({src['url']})" if src.get("url") else ""
                            st.markdown(f"**[{src['num']}] {src['title']}** ({src['date']}){url_link}")
                            st.caption(f"_{src['text'][:240]}..._")

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer_text,
                    "sources": sources_data,
                })

            except (FatalAPIError, TransientAPIError) as exc:
                st.error(f"API Error: {exc}")
            except Exception as exc:
                st.error(f"Terjadi kendala: {exc}")

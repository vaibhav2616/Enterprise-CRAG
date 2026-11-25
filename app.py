"""
app.py — Enterprise CRAG Streamlit UI (Level 3)
Editorial palette: deep forest green, light/dark toggle, clean professional layout
"""
import os
import sys
import time
import sqlite3
from pathlib import Path
import streamlit as st

# ── ensure project root on path ──────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.set_page_config(
    page_title="Enterprise CRAG Assistant",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── theme tokens ─────────────────────────────────────────────────────────────
THEMES = {
    "Light": {
        "bg": "#F8F6F2",
        "sidebar_bg": "#FFFFFF",
        "text": "#1A1A1A",
        "muted": "#555555",
        "accent": "#2C5F2E",
        "accent_hover": "#1E4220",
        "accent_text": "#FFFFFF",
        "card_bg": "#FFFFFF",
        "card_border": "#E0DDD8",
        "input_bg": "#FFFFFF",
        "input_border": "#CCCCCC",
        "chat_user_bg": "#EAF0EA",
        "chat_ai_bg": "#FFFFFF",
        "badge_sql": "#1565C0",
        "badge_vec": "#2C5F2E",
        "badge_web": "#6A1B9A",
        "badge_cache": "#E65100",
    },
    "Dark": {
        "bg": "#0F1117",
        "sidebar_bg": "#1C1C1E",
        "text": "#E8E6E0",
        "muted": "#AAAAAA",
        "accent": "#4CAF72",
        "accent_hover": "#3A9A5C",
        "accent_text": "#000000",
        "card_bg": "#1C1C1E",
        "card_border": "#2E2E30",
        "input_bg": "#1C1C1E",
        "input_border": "#3A3A3C",
        "chat_user_bg": "#1A2E1A",
        "chat_ai_bg": "#1C1C1E",
        "badge_sql": "#64B5F6",
        "badge_vec": "#81C784",
        "badge_web": "#CE93D8",
        "badge_cache": "#FFB74D",
    },
}

if "theme" not in st.session_state:
    st.session_state["theme"] = "Light"
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "cache_hits" not in st.session_state:
    st.session_state["cache_hits"] = 0
if "provider" not in st.session_state:
    st.session_state["provider"] = "Local Offline"
if "api_key" not in st.session_state:
    st.session_state["api_key"] = ""
if "model_name" not in st.session_state:
    st.session_state["model_name"] = ""

T = THEMES[st.session_state["theme"]]


def inject_css(t: dict):
    css = f"""
    <style>
    /* ── Root & App background ── */
    html, body, [data-testid="stApp"] {{
        background-color: {t['bg']} !important;
        color: {t['text']} !important;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }}
    [data-testid="stSidebar"] > div:first-child {{
        background-color: {t['sidebar_bg']} !important;
        border-right: 1px solid {t['card_border']};
    }}

    /* ── All text ── */
    p, span, label, div, h1, h2, h3, h4, h5, h6,
    [data-testid="stMarkdownContainer"] {{
        color: {t['text']} !important;
    }}

    /* ── Metric cards ── */
    [data-testid="stMetric"],
    [data-testid="metric-container"] {{
        background: {t['card_bg']} !important;
        border: 1px solid {t['card_border']} !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
    }}
    [data-testid="stMetricLabel"] > div {{
        color: {t['muted']} !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.05em !important;
        text-transform: uppercase !important;
    }}
    [data-testid="stMetricValue"] > div {{
        color: {t['text']} !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
    }}

    /* ── Buttons (Streamlit 1.67.0: stBaseButton-* IS the button element) ── */
    [data-testid^="stBaseButton-"] {{
        background-color: {t['accent']} !important;
        color: {t['accent_text']} !important;
        border: 1px solid {t['accent']} !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        transition: background 0.15s ease !important;
    }}
    [data-testid^="stBaseButton-"]:hover {{
        background-color: {t['accent_hover']} !important;
        color: {t['accent_text']} !important;
    }}
    [data-testid^="stBaseButton-"] * {{
        color: {t['accent_text']} !important;
    }}

    /* ── Selectbox & React Aria Dropdown ── */
    [data-testid="stSelectbox"] > div > div {{
        background-color: {t['input_bg']} !important;
        border: 1px solid {t['input_border']} !important;
        border-radius: 6px !important;
        color: {t['text']} !important;
    }}
    [data-testid="stSelectbox"] span,
    [data-testid="stSelectbox"] p,
    [data-testid="stSelectbox"] div {{
        color: {t['text']} !important;
    }}
    [data-testid="stSelectboxVirtualDropdown"],
    [data-testid="stSelectboxVirtualDropdown"] [role="option"] {{
        background-color: {t['input_bg']} !important;
        color: {t['text']} !important;
    }}
    [data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover {{
        background-color: {t['card_border']} !important;
    }}

    /* ── Text inputs ── */
    [data-testid="stTextInputField"],
    [data-testid="stTextInputField"] input {{
        background-color: {t['input_bg']} !important;
        border: 1px solid {t['input_border']} !important;
        border-radius: 6px !important;
        color: {t['text']} !important;
    }}
    [data-testid="stTextInputField"]:focus {{
        border-color: {t['accent']} !important;
        box-shadow: 0 0 0 2px {t['accent']}33 !important;
    }}

    /* ── Chat input ── */
    [data-testid="stChatInput"] textarea {{
        background-color: {t['input_bg']} !important;
        color: {t['text']} !important;
        border: 1px solid {t['input_border']} !important;
        border-radius: 8px !important;
    }}
    [data-testid="stChatInputSubmitButton"] {{
        background-color: {t['accent']} !important;
        border-radius: 6px !important;
    }}
    [data-testid="stChatInputSubmitButton"] svg path {{
        fill: {t['accent_text']} !important;
    }}

    /* ── Alert container ── */
    [data-testid="stAlertContainer"] {{
        background-color: {t['card_bg']} !important;
        border-color: {t['accent']} !important;
        color: {t['text']} !important;
        border-radius: 8px !important;
    }}

    /* ── Expander ── */
    [data-testid="stExpander"] {{
        background-color: {t['card_bg']} !important;
        border: 1px solid {t['card_border']} !important;
        border-radius: 8px !important;
    }}
    [data-testid="stExpander"] summary {{
        color: {t['text']} !important;
        font-weight: 600 !important;
    }}

    /* ── Code blocks ── */
    code, pre {{
        background-color: {t['card_bg']} !important;
        color: {t['text']} !important;
        border: 1px solid {t['card_border']} !important;
        border-radius: 4px !important;
    }}

    /* ── Spinner ── */
    [data-testid="stSpinner"] p {{
        color: {t['muted']} !important;
    }}

    /* ── Divider ── */
    hr {{
        border-color: {t['card_border']} !important;
        opacity: 0.6 !important;
    }}

    /* ── Sidebar nav pills ── */
    .theme-pill {{
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        cursor: pointer;
        border: 1px solid {t['card_border']};
        margin: 2px;
        background: {t['card_bg']};
        color: {t['text']};
    }}
    .theme-pill-active {{
        background: {t['accent']} !important;
        color: {t['accent_text']} !important;
        border-color: {t['accent']} !important;
    }}

    /* ── Badge chips ── */
    .badge-sql   {{ background:{t['badge_sql']}22; color:{t['badge_sql']}; border:1px solid {t['badge_sql']}44; }}
    .badge-vec   {{ background:{t['badge_vec']}22; color:{t['badge_vec']}; border:1px solid {t['badge_vec']}44; }}
    .badge-web   {{ background:{t['badge_web']}22; color:{t['badge_web']}; border:1px solid {t['badge_web']}44; }}
    .badge-cache {{ background:{t['badge_cache']}22; color:{t['badge_cache']}; border:1px solid {t['badge_cache']}44; }}
    .badge {{
        display:inline-block; padding:2px 10px; border-radius:12px;
        font-size:0.72rem; font-weight:700; letter-spacing:0.04em;
        margin-right:4px;
    }}
    </style>
    """
    st.html(css)


inject_css(T)


# ── helpers ──────────────────────────────────────────────────────────────────

def get_db_count() -> int:
    db = ROOT / "crm_tickets.db"
    if not db.exists():
        return 0
    try:
        conn = sqlite3.connect(str(db))
        n = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        conn.close()
        return n
    except Exception:
        return 0


def get_policy_chunks() -> int:
    chroma_path = ROOT / "enterprise_chroma_db"
    if not chroma_path.exists():
        return 0
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(chroma_path))
        col = client.get_collection("enterprise_policies")
        return col.count()
    except Exception:
        return 0


def run_graph(question: str) -> dict:
    from agent.graph import build_graph
    from agent.state import CRAGState

    provider_map = {
        "Local Offline": "local",
        "Gemini": "gemini",
        "Groq": "groq",
        "OpenAI": "openai",
    }
    provider = provider_map.get(st.session_state["provider"], "local")
    llm_config = {
        "provider": provider,
        "api_key": st.session_state.get("api_key", ""),
        "model": st.session_state.get("model_name", ""),
    }
    graph = build_graph(llm_config)
    initial_state: CRAGState = {
        "question": question,
        "route": None,
        "documents": [],
        "sql_query": None,
        "sql_result": None,
        "generation": None,
        "hallucination_check": None,
        "rewrite_count": 0,
        "node_path": [],
        "thinking_steps": [],
        "from_cache": False,
        "cached_response": None,
    }
    result = graph.invoke(initial_state)
    return result


def route_badge(node_path: list[str]) -> str:
    if "cache_hit" in node_path:
        return '<span class="badge badge-cache">⚡ Cache</span>'
    if "text_to_sql" in node_path:
        return '<span class="badge badge-sql">🗄️ SQL</span>'
    if "vector_retrieve" in node_path:
        return '<span class="badge badge-vec">📚 Vector</span>'
    if "web_search" in node_path:
        return '<span class="badge badge-web">🌐 Web</span>'
    return '<span class="badge badge-vec">🤖 AI</span>'


# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏢 Enterprise CRAG")
    st.markdown(
        "<span style='font-size:0.8rem; opacity:0.7;'>Corrective RAG · Level 3</span>",
        unsafe_allow_html=True,
    )
    st.divider()

    # Theme toggle
    st.markdown("**Display**")
    col_l, col_d = st.columns(2)
    with col_l:
        if st.button("☀️ Light", use_container_width=True):
            st.session_state["theme"] = "Light"
            st.rerun()
    with col_d:
        if st.button("🌙 Dark", use_container_width=True):
            st.session_state["theme"] = "Dark"
            st.rerun()

    st.divider()

    # AI provider
    st.markdown("**AI Provider**")
    provider = st.selectbox(
        "Engine",
        ["Local Offline", "Gemini", "Groq", "OpenAI"],
        key="provider",
        label_visibility="collapsed",
    )

    if provider != "Local Offline":
        st.text_input("API Key", type="password", key="api_key", placeholder="Paste API key…")
        st.text_input("Model (optional)", key="model_name", placeholder="e.g. gemini-2.5-flash-lite")

    st.divider()

    # System status
    with st.expander("📊 System Status", expanded=True):
        db_count = get_db_count()
        policy_chunks = get_policy_chunks()
        st.markdown(f"🗄️ **CRM Records:** `{db_count}`")
        st.markdown(f"📚 **Policy Chunks:** `{policy_chunks}`")
        st.markdown(f"⚡ **Cache Hits:** `{st.session_state['cache_hits']}`")
        db_status = "✅ Connected" if db_count > 0 else "❌ Not initialized"
        vec_status = "✅ Seeded" if policy_chunks > 0 else "❌ Not seeded"
        st.markdown(f"**DB:** {db_status}")
        st.markdown(f"**ChromaDB:** {vec_status}")

    st.divider()

    # Quick test pills
    st.markdown("**Quick Tests**")
    quick_questions = [
        "How many unresolved tickets?",
        "What is the refund policy?",
        "What is today's AI news?",
    ]
    for q in quick_questions:
        if st.button(q, use_container_width=True):
            st.session_state["_quick_q"] = q
            st.rerun()

    st.divider()
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state["messages"] = []
        st.session_state["cache_hits"] = 0
        st.rerun()


# ── main area ─────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="margin-bottom: 8px;">
        <h1 style="margin:0; font-size:1.9rem; font-weight:800; color:{T['text']};">
            Enterprise CRAG Assistant
        </h1>
        <p style="margin:4px 0 0 0; font-size:0.9rem; color:{T['muted']};">
            Corrective RAG · LangGraph · Semantic Cache
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Metric cards
db_count = get_db_count()
policy_chunks = get_policy_chunks()
provider_label = st.session_state.get("provider", "Local Offline")

m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Active Engine", provider_label)
with m2:
    st.metric("CRM Records", f"{db_count:,}" if db_count else "—")
with m3:
    st.metric("Policy Chunks", f"{policy_chunks:,}" if policy_chunks else "—")

st.divider()

# Handle quick question injection
if "_quick_q" in st.session_state:
    quick_q = st.session_state.pop("_quick_q")
    st.session_state["messages"].append({"role": "user", "content": quick_q})
    with st.spinner("Processing…"):
        t0 = time.time()
        try:
            result = run_graph(quick_q)
            elapsed = time.time() - t0
            generation = result.get("generation") or "No answer generated."
            node_path = result.get("node_path", [])
            sql_query = result.get("sql_query")
            hallucination_check = result.get("hallucination_check")
            thinking_steps = result.get("thinking_steps", [])
            from_cache = result.get("from_cache", False)
            if from_cache:
                st.session_state["cache_hits"] += 1
            st.session_state["messages"].append({
                "role": "assistant",
                "content": f"{generation}\n\n*⏱ {elapsed:.1f}s*",
                "node_path": node_path,
                "sql_query": sql_query,
                "hallucination_check": hallucination_check,
                "thinking_steps": thinking_steps,
                "from_cache": from_cache,
            })
        except Exception as e:
            st.session_state["messages"].append({
                "role": "assistant",
                "content": f"❌ Error: {e}",
                "node_path": [],
            })
    st.rerun()

# Chat history
for msg in st.session_state["messages"]:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant"):
            node_path = msg.get("node_path", [])
            badge_html = route_badge(node_path)
            st.html(badge_html)

            # Show SQL query if present
            if msg.get("sql_query"):
                with st.expander("🔍 Generated SQL", expanded=False):
                    st.code(msg["sql_query"], language="sql")

            if msg.get("thinking_steps"):
                with st.expander("🧠 Reasoning steps", expanded=False):
                    for step in msg["thinking_steps"]:
                        st.markdown(f"- {step}")

            st.markdown(msg["content"])

            # Hallucination indicator
            hc = msg.get("hallucination_check")
            if hc == "yes":
                st.success("✅ Grounded — answer verified against context")
            elif hc == "no":
                st.warning("⚠️ Regenerated — initial answer was not grounded")

# Chat input
if prompt := st.chat_input("Ask about tickets, policies, or anything…"):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        badge_placeholder = st.empty()
        content_placeholder = st.empty()

        with st.spinner("Thinking…"):
            t0 = time.time()
            try:
                result = run_graph(prompt)
                elapsed = time.time() - t0
                generation = result.get("generation") or "No answer generated."
                node_path = result.get("node_path", [])
                sql_query = result.get("sql_query")
                hallucination_check = result.get("hallucination_check")
                thinking_steps = result.get("thinking_steps", [])
                from_cache = result.get("from_cache", False)

                if from_cache:
                    st.session_state["cache_hits"] += 1

                badge_html = route_badge(node_path)
                badge_placeholder.html(badge_html)

                if sql_query:
                    with st.expander("🔍 Generated SQL", expanded=False):
                        st.code(sql_query, language="sql")

                if thinking_steps:
                    with st.expander("🧠 Reasoning steps", expanded=False):
                        for step in thinking_steps:
                            st.markdown(f"- {step}")

                final_content = f"{generation}\n\n*⏱ {elapsed:.1f}s*"
                content_placeholder.markdown(final_content)

                if hallucination_check == "yes":
                    st.success("✅ Grounded — answer verified against context")
                elif hallucination_check == "no":
                    st.warning("⚠️ Regenerated — initial answer was not grounded")

                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": final_content,
                    "node_path": node_path,
                    "sql_query": sql_query,
                    "hallucination_check": hallucination_check,
                    "thinking_steps": thinking_steps,
                    "from_cache": from_cache,
                })
            except Exception as e:
                content_placeholder.error(f"❌ Error: {e}")
                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": f"❌ Error: {e}",
                    "node_path": [],
                })

# Enterprise-CRAG: Corrective RAG with LangGraph

> **Level 3** of a progressive RAG series — a production-grade **Corrective Retrieval-Augmented Generation** system combining LangGraph orchestration, ChromaDB semantic search, SQLite CRM analytics, and an adaptive quality-control pipeline with hallucination detection and semantic caching.

## Architecture

```
                        ┌─────────────────────────────────────────┐
                        │           Streamlit Enterprise UI        │
                        │  Light/Dark · Metric Cards · Chat        │
                        └──────────────────┬──────────────────────┘
                                           │
                        ┌──────────────────▼──────────────────────┐
                        │           Semantic Cache                 │
                        │   BGE-small cosine sim (threshold 0.92) │
                        └──────────┬──────────────────────────────┘
                                   │ MISS
                        ┌──────────▼──────────────────────────────┐
                        │              LangGraph Agent             │
                        │                                         │
                        │  ┌──────────┐    ┌──────────────────┐  │
                        │  │  Router  │───▶│   text_to_sql    │  │
                        │  │  (LLM /  │    │   (SQLite CRM)   │  │
                        │  │  offline)│    └──────────────────┘  │
                        │  │          │    ┌──────────────────┐  │
                        │  │          │───▶│ vector_retrieve  │  │
                        │  │          │    │  (ChromaDB BGE)  │  │
                        │  │          │    └────────┬─────────┘  │
                        │  │          │             │             │
                        │  │          │    ┌────────▼─────────┐  │
                        │  │          │    │ grade_documents  │  │
                        │  │          │    └────────┬─────────┘  │
                        │  │          │        ┌────▼────┐        │
                        │  │          │        │rewrite? │        │
                        │  │          │        └────┬────┘        │
                        │  │          │    ┌────────▼─────────┐  │
                        │  │          │───▶│   web_search     │  │
                        │  └──────────┘    │   (Tavily/offline│  │
                        │                  └──────────────────┘  │
                        │                                         │
                        │  ┌──────────┐    ┌──────────────────┐  │
                        │  │ generate │───▶│hallucination_grdr│  │
                        │  └──────────┘    └──────────────────┘  │
                        └─────────────────────────────────────────┘
```

## Features

- **Multi-route CRAG pipeline** — SQL analytics (CRM), semantic vector search (policies), or web search, chosen automatically
- **LangGraph StateGraph** — explicit node-edge graph with conditional routing, rewrite loops, and hallucination gates
- **Semantic Cache** — BGE-small cosine similarity at 0.92 threshold prevents redundant LLM calls
- **Zero-cost offline mode** — all routing, grading, and generation run deterministically without any API key
- **ChromaDB policy store** — 15 enterprise policy sections chunked and embedded with BAAI/bge-small-en-v1.5
- **SQLite CRM database** — 100 synthetic ticket records with deterministic seeding (seed=42)
- **Multi-provider LLM** — Gemini / Groq / OpenAI or local offline fallback
- **FastAPI SSE endpoint** — `/chat` streams LangGraph node events as Server-Sent Events
- **Editorial UI** — forest-green enterprise palette, light/dark toggle, SQL code blocks, hallucination badges

## Setup

```bash
# 1. Clone and enter directory
git clone <repo-url>
cd RAG/level-3-enterprise-crag

# 2. Activate shared venv (Windows PowerShell)
..\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Initialize CRM database (creates crm_tickets.db)
.\..\venv\Scripts\python.exe database\init_crm_db.py

# 5. Seed policy vector store (downloads BGE-small on first run ~200MB)
.\..\venv\Scripts\python.exe database\seed_policies.py

# 6. Launch Streamlit app
streamlit run app.py
```

## Quick Test Commands

```bash
# Run all tests (offline, no API key needed)
pytest tests/test_agent.py -v

# Run specific test
pytest tests/test_agent.py::test_router_sql -v

# Start FastAPI backend
uvicorn api.main:app --reload --port 8000

# Check API health
curl http://localhost:8000/health
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Orchestration | LangGraph (StateGraph) |
| LLM Providers | Gemini / Groq / OpenAI / Offline |
| Embeddings | BAAI/bge-small-en-v1.5 (HuggingFace) |
| Vector Store | ChromaDB |
| Relational DB | SQLite |
| Semantic Cache | sentence-transformers + NumPy cosine |
| Web Search | Tavily API (optional) |
| UI | Streamlit 1.67+ |
| API Backend | FastAPI + SSE |
| Testing | pytest |

## Environment Variables (optional)

| Variable | Purpose |
|----------|---------|
| `TAVILY_API_KEY` | Enable live web search (Tavily) |
| `GOOGLE_API_KEY` | Use Gemini models |
| `GROQ_API_KEY` | Use Groq models |
| `OPENAI_API_KEY` | Use OpenAI models |

All variables are optional — the system runs fully offline without any of them.

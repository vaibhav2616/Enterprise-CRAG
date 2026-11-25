"""
agent/nodes.py — All LangGraph nodes for Enterprise-CRAG (Level 3)
"""
from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Optional

from agent.state import CRAGState

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BASE_DIR = Path(__file__).resolve().parent.parent
_DB_PATH = _BASE_DIR / "crm_tickets.db"
_CHROMA_PATH = _BASE_DIR / "enterprise_chroma_db"

# ---------------------------------------------------------------------------
# Global LLM reference (set by configure_llm)
# ---------------------------------------------------------------------------
_llm: Any = None

# ---------------------------------------------------------------------------
# Offline / deterministic fallback LLM
# ---------------------------------------------------------------------------

class DeterministicOfflineLLM:
    """Pure-Python fallback — no model weights required."""

    # --- routing ---
    SQL_KEYWORDS = {
        "ticket", "count", "unresolved", "priority", "csat", "assigned",
        "status", "resolve", "open", "escalat", "how many", "metrics",
        "resolution", "team", "billing team", "tech support", "logistics",
    }
    VECTOR_KEYWORDS = {
        "policy", "refund", "return", "exchange", "shipping", "procedure",
        "sla", "escalation", "subscription", "cancel", "warranty", "privacy",
        "password", "account", "dispute", "guarantee", "support process",
        "contact",
    }

    def route(self, question: str) -> str:
        q = question.lower()
        for kw in self.SQL_KEYWORDS:
            if kw in q:
                return "sql_db"
        for kw in self.VECTOR_KEYWORDS:
            if kw in q:
                return "vector_store"
        return "web_search"

    def build_sql(self, question: str) -> str:
        q = question.lower()
        if "unresolved" in q or "open" in q:
            return "SELECT COUNT(*) AS count FROM tickets WHERE status IN ('Open','In Progress');"
        if "escalat" in q:
            return "SELECT COUNT(*) AS count FROM tickets WHERE status='Escalated';"
        if "critical" in q:
            return "SELECT * FROM tickets WHERE priority='Critical' LIMIT 20;"
        if "csat" in q or "satisfaction" in q:
            return "SELECT AVG(csat_score) AS avg_csat FROM tickets;"
        if "count" in q or "how many" in q:
            return "SELECT COUNT(*) AS total FROM tickets;"
        if "billing" in q:
            return "SELECT * FROM tickets WHERE assigned_team='Billing Team' LIMIT 20;"
        if "tech" in q:
            return "SELECT * FROM tickets WHERE assigned_team='Tech Support' LIMIT 20;"
        return "SELECT * FROM tickets LIMIT 10;"

    def grade(self, question: str, doc: str) -> str:
        q_tokens = set(re.findall(r"\w+", question.lower()))
        d_tokens = set(re.findall(r"\w+", doc.lower()))
        overlap = len(q_tokens & d_tokens) / max(len(q_tokens), 1)
        return "relevant" if overlap >= 0.12 else "irrelevant"

    def rewrite(self, question: str) -> str:
        return "enterprise support: " + question.strip()

    def generate(self, question: str, context: str) -> str:
        if not context.strip():
            return "I don't have enough context to answer that question."
        # Extract sentences that share token overlap with question
        q_tokens = set(re.findall(r"\w+", question.lower()))
        sentences = re.split(r"(?<=[.!?])\s+", context)
        scored = []
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            s_tokens = set(re.findall(r"\w+", s.lower()))
            score = len(q_tokens & s_tokens) / max(len(q_tokens), 1)
            scored.append((score, s))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = [s for _, s in scored[:5] if s]
        if not top:
            return context[:500]
        return " ".join(top)

    def grade_hallucination(self, generation: str, context: str) -> str:
        g_tokens = set(re.findall(r"\w+", generation.lower()))
        c_tokens = set(re.findall(r"\w+", context.lower()))
        overlap = len(g_tokens & c_tokens) / max(len(g_tokens), 1)
        return "yes" if overlap >= 0.25 else "no"

    # LangChain-compatible invoke stub (not used in routing path)
    def invoke(self, prompt: Any) -> Any:
        return type("Msg", (), {"content": "offline"})()

    def with_structured_output(self, schema: Any) -> Any:
        return _StructuredOfflineWrapper(self, schema)


class _StructuredOfflineWrapper:
    def __init__(self, llm: DeterministicOfflineLLM, schema: Any):
        self._llm = llm
        self._schema = schema

    def invoke(self, messages: Any) -> Any:
        # Try to get question text from messages
        question = ""
        if isinstance(messages, list):
            for m in messages:
                if hasattr(m, "content"):
                    question = str(m.content)
                    break
                elif isinstance(m, dict):
                    question = str(m.get("content", ""))
                    break
        route = self._llm.route(question)
        # Return object with datasource attribute (for RouteQuery schema)
        return type("Routed", (), {"datasource": route})()


# ---------------------------------------------------------------------------
# LLM factory
# ---------------------------------------------------------------------------

def get_llm(provider: str = "local", api_key: str = "", model: str = "") -> Any:
    if provider == "gemini" and api_key:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model or "gemini-2.5-flash-lite",
            google_api_key=api_key,
        )
    elif provider == "groq" and api_key:
        from langchain_groq import ChatGroq
        return ChatGroq(model=model or "llama-3.1-8b-instant", groq_api_key=api_key)
    elif provider == "openai" and api_key:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model or "gpt-4.1-nano", api_key=api_key)
    else:
        return DeterministicOfflineLLM()


def configure_llm(provider: str = "local", api_key: str = "", model: str = "") -> None:
    global _llm
    _llm = get_llm(provider, api_key, model)


# ---------------------------------------------------------------------------
# Semantic cache (singleton)
# ---------------------------------------------------------------------------
_cache_instance: Any = None


def _get_cache():
    global _cache_instance
    if _cache_instance is None:
        from cache.semantic_cache import SemanticCache
        _cache_instance = SemanticCache()
    return _cache_instance


# ---------------------------------------------------------------------------
# ChromaDB retriever (lazy)
# ---------------------------------------------------------------------------
_retriever = None


def _get_retriever():
    global _retriever
    if _retriever is not None:
        return _retriever
    try:
        import chromadb
        from langchain_chroma import Chroma
        from langchain_huggingface import HuggingFaceEmbeddings

        embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        vectorstore = Chroma(
            collection_name="enterprise_policies",
            embedding_function=embeddings,
            persist_directory=str(_CHROMA_PATH),
        )
        _retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    except Exception:
        _retriever = None
    return _retriever


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

# -- Cache nodes --

def check_cache_node(state: CRAGState) -> dict:
    question = state["question"]
    cache = _get_cache()
    cached = cache.get(question)
    if cached:
        return {
            "from_cache": True,
            "cached_response": cached,
            "generation": cached,
            "node_path": ["cache_hit"],
            "thinking_steps": [f"Cache hit for: {question[:60]}"],
        }
    return {
        "from_cache": False,
        "cached_response": None,
        "node_path": ["cache_miss"],
        "thinking_steps": ["Cache miss — routing to LangGraph pipeline"],
    }


def cache_route(state: CRAGState) -> str:
    return "cached" if state.get("from_cache") else "miss"


# -- Router --

def router_node(state: CRAGState) -> dict:
    question = state["question"]
    llm = _llm or DeterministicOfflineLLM()

    if isinstance(llm, DeterministicOfflineLLM):
        route = llm.route(question)
    else:
        try:
            from pydantic import BaseModel, Field

            class RouteQuery(BaseModel):
                datasource: str = Field(
                    description="One of: sql_db, vector_store, web_search"
                )

            structured = llm.with_structured_output(RouteQuery)
            from langchain_core.messages import HumanMessage, SystemMessage
            result = structured.invoke([
                SystemMessage(content=(
                    "You are a routing expert. Route the question to one of: "
                    "sql_db (ticket metrics, counts, status, CRM queries), "
                    "vector_store (policy, procedure, refund, support process), "
                    "web_search (general knowledge, current events)."
                    " Respond with JSON: {\"datasource\": \"<route>\"}"
                )),
                HumanMessage(content=question),
            ])
            route = result.datasource
        except Exception:
            # Deterministic fallback
            route = DeterministicOfflineLLM().route(question)

    return {
        "route": route,
        "node_path": ["router"],
        "thinking_steps": [f"Routed question to: {route}"],
    }


def route_question(state: CRAGState) -> str:
    return state.get("route", "web_search")


# -- Text-to-SQL --

def text_to_sql_node(state: CRAGState) -> dict:
    question = state["question"]
    llm = _llm or DeterministicOfflineLLM()
    schema = (
        "tickets(ticket_id TEXT, customer_name TEXT, issue_type TEXT, "
        "priority TEXT, resolution_time_hrs REAL, csat_score INT, "
        "assigned_team TEXT, status TEXT)"
    )

    if isinstance(llm, DeterministicOfflineLLM):
        sql = llm.build_sql(question)
    else:
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            resp = llm.invoke([
                SystemMessage(content=(
                    f"Generate a valid SQLite SELECT query for this schema:\n{schema}\n"
                    "Return ONLY the SQL query, no explanations."
                )),
                HumanMessage(content=question),
            ])
            sql = resp.content.strip()
            # Strip markdown code fences if present
            sql = re.sub(r"```(?:sql)?", "", sql).replace("```", "").strip()
        except Exception:
            sql = DeterministicOfflineLLM().build_sql(question)

    # Execute
    result_text = ""
    try:
        conn = sqlite3.connect(str(_DB_PATH))
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        conn.close()
        if rows:
            header = " | ".join(cols)
            sep = "-" * len(header)
            lines = [header, sep] + [" | ".join(str(c) for c in r) for r in rows[:50]]
            result_text = "\n".join(lines)
        else:
            result_text = "No records found."
    except Exception as e:
        result_text = f"SQL error: {e}"

    generation = f"**SQL Query:**\n```sql\n{sql}\n```\n\n**Result:**\n```\n{result_text}\n```"

    return {
        "sql_query": sql,
        "sql_result": result_text,
        "generation": generation,
        "hallucination_check": "yes",
        "node_path": ["text_to_sql"],
        "thinking_steps": [f"Generated SQL: {sql[:80]}"],
    }


# -- Vector retrieval --

def vector_retrieve_node(state: CRAGState) -> dict:
    question = state["question"]
    retriever = _get_retriever()

    docs = []
    if retriever:
        try:
            retrieved = retriever.invoke(question)
            docs = [d.page_content for d in retrieved]
        except Exception:
            docs = []

    if not docs:
        # Fallback: return a default policy snippet
        docs = [
            "Our standard refund policy allows returns within 30 days of purchase. "
            "Digital products are eligible for refunds within 7 days if unused. "
            "Contact support@company.com to initiate a refund request.",
        ]

    return {
        "documents": docs,
        "node_path": ["vector_retrieve"],
        "thinking_steps": [f"Retrieved {len(docs)} document chunks from policy store"],
    }


# -- Document grading --

def grade_documents_node(state: CRAGState) -> dict:
    question = state["question"]
    documents = state.get("documents", [])
    llm = _llm or DeterministicOfflineLLM()

    relevant_docs = []
    for doc in documents:
        if isinstance(llm, DeterministicOfflineLLM):
            grade = llm.grade(question, doc)
        else:
            try:
                from langchain_core.messages import HumanMessage, SystemMessage
                resp = llm.invoke([
                    SystemMessage(content=(
                        "Grade this document as 'relevant' or 'irrelevant' to the question. "
                        "Reply with exactly one word: relevant or irrelevant."
                    )),
                    HumanMessage(content=f"Question: {question}\n\nDocument: {doc[:300]}"),
                ])
                grade = resp.content.strip().lower()
                if "relevant" not in grade:
                    grade = "irrelevant"
                else:
                    grade = "relevant"
            except Exception:
                grade = DeterministicOfflineLLM().grade(question, doc)

        if grade == "relevant":
            relevant_docs.append(doc)

    all_filtered = len(relevant_docs) == 0
    return {
        "documents": relevant_docs,
        "node_path": ["grade_documents"],
        "thinking_steps": [
            f"Graded {len(documents)} docs: {len(relevant_docs)} relevant, "
            f"{len(documents) - len(relevant_docs)} filtered"
        ],
    }


def grade_route(state: CRAGState) -> str:
    if not state.get("documents"):
        return "rewrite"
    return "generate"


# -- Query rewrite --

def query_rewrite_node(state: CRAGState) -> dict:
    question = state["question"]
    rewrite_count = state.get("rewrite_count", 0)
    llm = _llm or DeterministicOfflineLLM()

    if isinstance(llm, DeterministicOfflineLLM):
        new_question = llm.rewrite(question)
    else:
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            resp = llm.invoke([
                SystemMessage(content=(
                    "Rewrite the following question to improve retrieval from an enterprise "
                    "policy knowledge base. Make it more specific and keyword-rich. "
                    "Return only the rewritten question."
                )),
                HumanMessage(content=question),
            ])
            new_question = resp.content.strip()
        except Exception:
            new_question = DeterministicOfflineLLM().rewrite(question)

    return {
        "question": new_question,
        "rewrite_count": rewrite_count + 1,
        "node_path": ["query_rewrite"],
        "thinking_steps": [
            f"Rewrote query (attempt {rewrite_count + 1}): {new_question[:80]}"
        ],
    }


def rewrite_route(state: CRAGState) -> str:
    if state.get("rewrite_count", 0) >= 2:
        return "web_search"
    return "vector_retrieve"


# -- Web search --

def web_search_node(state: CRAGState) -> dict:
    question = state["question"]
    tavily_key = os.environ.get("TAVILY_API_KEY", "")

    if tavily_key:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=tavily_key)
            response = client.search(question, max_results=3)
            results = response.get("results", [])
            docs = [r.get("content", "") for r in results if r.get("content")]
        except Exception as e:
            docs = [f"Web search error: {e}"]
    else:
        docs = [
            "Web search unavailable — set TAVILY_API_KEY environment variable to enable live web search."
        ]

    return {
        "documents": docs,
        "node_path": ["web_search"],
        "thinking_steps": [
            "Web search completed" if tavily_key else "Web search skipped (no API key)"
        ],
    }


# -- Generate --

def generate_node(state: CRAGState) -> dict:
    question = state["question"]
    documents = state.get("documents", [])
    llm = _llm or DeterministicOfflineLLM()
    context = "\n\n".join(documents)

    if isinstance(llm, DeterministicOfflineLLM):
        generation = llm.generate(question, context)
    else:
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            resp = llm.invoke([
                SystemMessage(content=(
                    "You are an enterprise support assistant. "
                    "Answer ONLY from the provided context. "
                    "If the context is insufficient, say so clearly. "
                    "Do not make up information."
                )),
                HumanMessage(content=f"Context:\n{context}\n\nQuestion: {question}"),
            ])
            generation = resp.content.strip()
        except Exception:
            generation = DeterministicOfflineLLM().generate(question, context)

    # Store in cache
    if generation and "unavailable" not in generation.lower():
        _get_cache().put(question, generation)

    return {
        "generation": generation,
        "node_path": ["generate"],
        "thinking_steps": [f"Generated answer ({len(generation)} chars)"],
    }


# -- Hallucination grader --

def hallucination_grader_node(state: CRAGState) -> dict:
    generation = state.get("generation", "")
    documents = state.get("documents", [])
    llm = _llm or DeterministicOfflineLLM()
    context = "\n\n".join(documents)

    if isinstance(llm, DeterministicOfflineLLM):
        result = llm.grade_hallucination(generation, context)
    else:
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            resp = llm.invoke([
                SystemMessage(content=(
                    "Does this answer come from the provided context? "
                    "Reply with exactly 'yes' (grounded) or 'no' (hallucinated)."
                )),
                HumanMessage(
                    content=f"Context:\n{context[:800]}\n\nAnswer:\n{generation[:400]}"
                ),
            ])
            result = "yes" if "yes" in resp.content.lower() else "no"
        except Exception:
            result = DeterministicOfflineLLM().grade_hallucination(generation, context)

    return {
        "hallucination_check": result,
        "node_path": ["hallucination_grader"],
        "thinking_steps": [f"Hallucination check: {'grounded' if result == 'yes' else 'hallucinated'}"],
    }


def hallucination_route(state: CRAGState) -> str:
    return "grounded" if state.get("hallucination_check") == "yes" else "regenerate"

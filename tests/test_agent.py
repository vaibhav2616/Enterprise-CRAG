"""
tests/test_agent.py — Offline pytest tests for Enterprise-CRAG (no API key required)
"""
import sys
import os
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def ensure_db():
    """Create the SQLite DB and ChromaDB before tests run."""
    from database.init_crm_db import init_db
    init_db()
    from database.seed_policies import seed_chromadb
    seed_chromadb()


@pytest.fixture(scope="session")
def offline_state_base():
    return {
        "question": "",
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


@pytest.fixture(scope="session")
def offline_graph():
    from agent.graph import build_graph
    return build_graph({"provider": "local", "api_key": "", "model": ""})


# ---------------------------------------------------------------------------
# 1. Router — SQL
# ---------------------------------------------------------------------------

def test_router_sql():
    from agent.nodes import DeterministicOfflineLLM, router_node, configure_llm
    configure_llm(provider="local")
    state = {
        "question": "how many unresolved tickets?",
        "route": None, "documents": [], "sql_query": None, "sql_result": None,
        "generation": None, "hallucination_check": None, "rewrite_count": 0,
        "node_path": [], "thinking_steps": [], "from_cache": False, "cached_response": None,
    }
    result = router_node(state)
    assert result["route"] == "sql_db", f"Expected sql_db, got {result['route']}"


# ---------------------------------------------------------------------------
# 2. Router — Vector
# ---------------------------------------------------------------------------

def test_router_vector():
    from agent.nodes import router_node, configure_llm
    configure_llm(provider="local")
    state = {
        "question": "what is the refund policy?",
        "route": None, "documents": [], "sql_query": None, "sql_result": None,
        "generation": None, "hallucination_check": None, "rewrite_count": 0,
        "node_path": [], "thinking_steps": [], "from_cache": False, "cached_response": None,
    }
    result = router_node(state)
    assert result["route"] == "vector_store", f"Expected vector_store, got {result['route']}"


# ---------------------------------------------------------------------------
# 3. text_to_sql_node runs and returns a string
# ---------------------------------------------------------------------------

def test_text_to_sql_runs():
    from agent.nodes import text_to_sql_node, configure_llm
    configure_llm(provider="local")
    state = {
        "question": "how many tickets are unresolved?",
        "route": "sql_db", "documents": [], "sql_query": None, "sql_result": None,
        "generation": None, "hallucination_check": None, "rewrite_count": 0,
        "node_path": [], "thinking_steps": [], "from_cache": False, "cached_response": None,
    }
    result = text_to_sql_node(state)
    assert isinstance(result.get("generation"), str)
    assert len(result["generation"]) > 0


# ---------------------------------------------------------------------------
# 4. vector_retrieve_node returns at least 1 document
# ---------------------------------------------------------------------------

def test_vector_retrieve_returns_docs():
    from agent.nodes import vector_retrieve_node, configure_llm
    configure_llm(provider="local")
    state = {
        "question": "what is the refund policy?",
        "route": "vector_store", "documents": [], "sql_query": None, "sql_result": None,
        "generation": None, "hallucination_check": None, "rewrite_count": 0,
        "node_path": [], "thinking_steps": [], "from_cache": False, "cached_response": None,
    }
    result = vector_retrieve_node(state)
    docs = result.get("documents", [])
    assert len(docs) >= 1, "Expected at least 1 document from vector store"


# ---------------------------------------------------------------------------
# 5. grade_documents keeps relevant docs
# ---------------------------------------------------------------------------

def test_grade_documents_relevant():
    from agent.nodes import grade_documents_node, configure_llm
    configure_llm(provider="local")
    # Doc that shares many tokens with question
    state = {
        "question": "what is the refund policy for digital products?",
        "route": "vector_store",
        "documents": [
            "Our refund policy allows returns within 30 days of purchase. "
            "Digital products are eligible for refunds within 7 days if unused."
        ],
        "sql_query": None, "sql_result": None, "generation": None,
        "hallucination_check": None, "rewrite_count": 0,
        "node_path": [], "thinking_steps": [], "from_cache": False, "cached_response": None,
    }
    result = grade_documents_node(state)
    assert len(result["documents"]) >= 1, "Expected relevant doc to be kept"


# ---------------------------------------------------------------------------
# 6. grade_documents filters irrelevant docs
# ---------------------------------------------------------------------------

def test_grade_documents_irrelevant():
    from agent.nodes import grade_documents_node, configure_llm
    configure_llm(provider="local")
    state = {
        "question": "how many tickets are assigned to the billing team?",
        "route": "sql_db",
        "documents": [
            "The sky is blue. Clouds form from water vapour. Rain falls from clouds."
        ],
        "sql_query": None, "sql_result": None, "generation": None,
        "hallucination_check": None, "rewrite_count": 0,
        "node_path": [], "thinking_steps": [], "from_cache": False, "cached_response": None,
    }
    result = grade_documents_node(state)
    # Completely off-topic doc should be filtered
    assert len(result["documents"]) == 0, "Expected irrelevant doc to be filtered out"


# ---------------------------------------------------------------------------
# 7. SemanticCache hit
# ---------------------------------------------------------------------------

def test_cache_hit():
    from cache.semantic_cache import SemanticCache
    cache = SemanticCache(threshold=0.90)
    cache.put("What is the refund policy?", "You can get a refund within 30 days.")
    result = cache.get("What is the refund policy?")
    assert result is not None
    assert "refund" in result.lower()


# ---------------------------------------------------------------------------
# 8. SemanticCache miss
# ---------------------------------------------------------------------------

def test_cache_miss():
    from cache.semantic_cache import SemanticCache
    cache = SemanticCache(threshold=0.90)
    cache.put("What is the refund policy?", "You can get a refund within 30 days.")
    result = cache.get("How do I reset my password on a Sunday morning?")
    assert result is None, "Expected cache miss for unrelated question"


# ---------------------------------------------------------------------------
# 9. Full pipeline — SQL question
# ---------------------------------------------------------------------------

def test_full_pipeline_sql(offline_graph):
    state = {
        "question": "how many tickets are unresolved?",
        "route": None, "documents": [], "sql_query": None, "sql_result": None,
        "generation": None, "hallucination_check": None, "rewrite_count": 0,
        "node_path": [], "thinking_steps": [], "from_cache": False, "cached_response": None,
    }
    result = offline_graph.invoke(state)
    gen = result.get("generation") or ""
    assert len(gen) > 0, "Full SQL pipeline should produce non-empty generation"


# ---------------------------------------------------------------------------
# 10. Full pipeline — Vector question
# ---------------------------------------------------------------------------

def test_full_pipeline_vector(offline_graph):
    state = {
        "question": "what is the refund policy?",
        "route": None, "documents": [], "sql_query": None, "sql_result": None,
        "generation": None, "hallucination_check": None, "rewrite_count": 0,
        "node_path": [], "thinking_steps": [], "from_cache": False, "cached_response": None,
    }
    result = offline_graph.invoke(state)
    gen = result.get("generation") or ""
    assert len(gen) > 0, "Full vector pipeline should produce non-empty generation"


# ---------------------------------------------------------------------------
# 11. Hallucination grader — grounded
# ---------------------------------------------------------------------------

def test_hallucination_grader_grounded():
    from agent.nodes import hallucination_grader_node, configure_llm
    configure_llm(provider="local")
    policy_text = (
        "Our standard refund policy allows customers to request a full refund within 30 days of purchase. "
        "Refunds are processed within 5-7 business days to the original payment method."
    )
    state = {
        "question": "what is the refund policy?",
        "route": "vector_store",
        "documents": [policy_text],
        "sql_query": None, "sql_result": None,
        "generation": (
            "The refund policy allows customers to request a full refund within 30 days. "
            "Refunds are processed within 5-7 business days to the original payment method."
        ),
        "hallucination_check": None, "rewrite_count": 0,
        "node_path": [], "thinking_steps": [], "from_cache": False, "cached_response": None,
    }
    result = hallucination_grader_node(state)
    assert result["hallucination_check"] == "yes", "Expected grounded answer"


# ---------------------------------------------------------------------------
# 12. query_rewrite_node increments rewrite_count
# ---------------------------------------------------------------------------

def test_query_rewrite_increments():
    from agent.nodes import query_rewrite_node, configure_llm
    configure_llm(provider="local")
    state = {
        "question": "policy info",
        "route": "vector_store",
        "documents": [],
        "sql_query": None, "sql_result": None, "generation": None,
        "hallucination_check": None, "rewrite_count": 0,
        "node_path": [], "thinking_steps": [], "from_cache": False, "cached_response": None,
    }
    result = query_rewrite_node(state)
    assert result["rewrite_count"] == 1, f"Expected rewrite_count=1, got {result['rewrite_count']}"
    assert len(result["question"]) > 0, "Rewritten question should be non-empty"

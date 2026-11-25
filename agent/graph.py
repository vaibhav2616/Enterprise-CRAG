"""
agent/graph.py — StateGraph compilation for Enterprise-CRAG
"""
from langgraph.graph import StateGraph, END
from agent.state import CRAGState
from agent import nodes


def build_graph(llm_config: dict):
    nodes.configure_llm(**llm_config)
    graph = StateGraph(CRAGState)

    graph.add_node("check_cache", nodes.check_cache_node)
    graph.add_node("router", nodes.router_node)
    graph.add_node("text_to_sql", nodes.text_to_sql_node)
    graph.add_node("vector_retrieve", nodes.vector_retrieve_node)
    graph.add_node("web_search", nodes.web_search_node)
    graph.add_node("grade_documents", nodes.grade_documents_node)
    graph.add_node("query_rewrite", nodes.query_rewrite_node)
    graph.add_node("generate", nodes.generate_node)
    graph.add_node("hallucination_grader", nodes.hallucination_grader_node)

    graph.set_entry_point("check_cache")

    graph.add_conditional_edges("check_cache", nodes.cache_route, {
        "cached": END,
        "miss": "router",
    })
    graph.add_conditional_edges("router", nodes.route_question, {
        "sql_db": "text_to_sql",
        "vector_store": "vector_retrieve",
        "web_search": "web_search",
    })
    graph.add_edge("text_to_sql", END)
    graph.add_edge("vector_retrieve", "grade_documents")
    graph.add_edge("web_search", "generate")
    graph.add_conditional_edges("grade_documents", nodes.grade_route, {
        "generate": "generate",
        "rewrite": "query_rewrite",
    })
    graph.add_conditional_edges("query_rewrite", nodes.rewrite_route, {
        "vector_retrieve": "vector_retrieve",
        "web_search": "web_search",
    })
    graph.add_edge("generate", "hallucination_grader")
    graph.add_conditional_edges("hallucination_grader", nodes.hallucination_route, {
        "grounded": END,
        "regenerate": "generate",
    })

    return graph.compile()

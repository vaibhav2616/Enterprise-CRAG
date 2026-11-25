"""
api/main.py — FastAPI SSE streaming endpoint for Enterprise-CRAG
"""
import json
import os
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="Enterprise-CRAG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    provider: str = "local"
    api_key: str = ""
    model: str = ""


@app.get("/health")
async def health():
    return {"status": "ok"}


async def run_graph_stream(request: ChatRequest) -> AsyncGenerator[str, None]:
    from agent.graph import build_graph
    from agent.state import CRAGState

    llm_config = {
        "provider": request.provider,
        "api_key": request.api_key,
        "model": request.model,
    }
    graph = build_graph(llm_config)

    initial_state: CRAGState = {
        "question": request.question,
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

    try:
        for event in graph.stream(initial_state, stream_mode="updates"):
            for node_name, node_output in event.items():
                payload = {
                    "node": node_name,
                    "node_path": node_output.get("node_path", []),
                    "thinking": node_output.get("thinking_steps", []),
                    "generation": node_output.get("generation"),
                    "sql_query": node_output.get("sql_query"),
                    "sql_result": node_output.get("sql_result"),
                    "hallucination_check": node_output.get("hallucination_check"),
                    "from_cache": node_output.get("from_cache", False),
                }
                yield f"data: {json.dumps(payload)}\n\n"

        yield "data: [DONE]\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"


@app.post("/chat")
async def chat(request: ChatRequest):
    return StreamingResponse(
        run_graph_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

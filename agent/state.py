from typing import Annotated, Any, Literal, Optional
from typing_extensions import TypedDict
import operator


class CRAGState(TypedDict):
    question: str
    route: Optional[Literal["sql_db", "vector_store", "web_search"]]
    documents: Annotated[list[str], operator.add]
    sql_query: Optional[str]
    sql_result: Optional[str]
    generation: Optional[str]
    hallucination_check: Optional[Literal["yes", "no"]]
    rewrite_count: int
    node_path: Annotated[list[str], operator.add]
    thinking_steps: Annotated[list[str], operator.add]
    from_cache: bool
    cached_response: Optional[str]

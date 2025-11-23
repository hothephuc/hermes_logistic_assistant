from __future__ import annotations

from functools import lru_cache

import pandas as pd
from app.ai.master_agent.agent import build_master_graph
from app.ai.master_agent.state import AgentState


@lru_cache(maxsize=1)
def _graph():
    """Instantiate the LangGraph once and reuse across requests."""

    return build_master_graph().compile()


def process_query(query: str, data: pd.DataFrame) -> str:
    state: AgentState = {
        "query": query,
        "data": data,
        "filters": {},
        "timeframe": {},
        "result": {},
        "steps": [],
    }
    final_state = _graph().invoke(state)
    return final_state.get("response", "No response generated.")

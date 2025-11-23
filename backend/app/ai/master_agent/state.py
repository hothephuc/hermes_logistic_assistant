from __future__ import annotations

from typing import Any, Dict, List, TypedDict

import pandas as pd


class AgentState(TypedDict, total=False):
    query: str
    data: pd.DataFrame
    intent: str
    filters: Dict[str, Any]
    timeframe: Dict[str, Any]
    forecast_horizon_days: int
    history: List[Dict[str, Any]]
    llm_metadata: Dict[str, Any]
    result: Dict[str, Any]
    response: str
    steps: List[str]


def ensure_steps(state: AgentState) -> None:
    if "steps" not in state:
        state["steps"] = []


def update_state(state: AgentState, **kwargs: Any) -> AgentState:
    state.update(kwargs)
    return state

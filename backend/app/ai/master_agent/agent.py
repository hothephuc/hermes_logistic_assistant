from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Dict

import numpy as np
from app.ai.master_agent.state import AgentState, ensure_steps, update_state
from app.ai.master_agent.tools import llm_classify_intent
from app.ai.sub_agents.analytics_agent.agent import run_analytics_intent
from app.ai.sub_agents.prediction_agent.agent import run_prediction_intent
from langgraph.constants import END
from langgraph.graph import StateGraph


def _classify_intent(state: AgentState) -> AgentState:
    """Very lightweight heuristic classifier with optional LLM enhancement."""

    ensure_steps(state)

    query = state["query"].lower()

    # Try LLM first
    llm_intent = llm_classify_intent(query)
    if llm_intent:
        intent = llm_intent
        state["steps"].append(f"LLM classified intent as '{intent}'")
    else:
        intent = "analytics"

        if any(
            token in query
            for token in ["predict", "forecast", "next week", "projection"]
        ):
            intent = "prediction"
        elif "warehouse" in query:
            intent = "warehouse"
        elif "route" in query:
            intent = "route"
        elif "reason" in query:
            intent = "delay_reason"
        elif any(
            token in query
            for token in ["average delay", "delay last", "delay in", "delay stats"]
        ):
            intent = "delay"

        state["steps"].append(f"Heuristic classified intent as '{intent}'")

    return update_state(state, intent=intent)


def _augment_timeframe(state: AgentState) -> AgentState:
    """Derive simple timeframe filters based on temporal hints in the query."""

    ensure_steps(state)

    query = state["query"].lower()
    df = state["data"]
    timeframe: Dict[str, datetime] = {}

    if "last week" in query:
        end_date = df["date"].max()
        start_date = end_date - timedelta(days=7)
        timeframe = {"start": start_date, "end": end_date}
    elif "october" in query:
        # assume most recent october in data
        dates = df["date"]
        october_rows = dates[dates.dt.month == 10]
        if not october_rows.empty:
            year = october_rows.dt.year.max()
            timeframe = {
                "start": datetime(year=year, month=10, day=1),
                "end": datetime(year=year, month=10, day=31),
            }
    elif "last month" in query:
        end_date = df["date"].max()
        start_date = end_date - timedelta(days=30)
        timeframe = {"start": start_date, "end": end_date}

    if timeframe:
        state["steps"].append(
            f"Applied timeframe filter between {timeframe['start'].date()} "
            + f"and {timeframe['end'].date()}"
        )
    return update_state(state, timeframe=timeframe)


def _run_intent(state: AgentState) -> AgentState:
    """Dispatch the query to the appropriate specialised agent."""

    if state.get("intent") == "prediction":
        result = run_prediction_intent(state)
    else:
        result = run_analytics_intent(state)

    return update_state(state, result=result)


def _format_response(state: AgentState) -> AgentState:
    """Serialize the analytics result to JSON before streaming to the frontend."""

    payload = {
        "query": state["query"],
        "intent": state.get("intent"),
        "result": state.get("result"),
        "steps": state.get("steps", []),
    }
    state["steps"].append("Formatted response payload")
    return update_state(state, response=json.dumps(payload, default=_json_default))


def _json_default(value):
    if isinstance(value, (datetime, np.datetime64)):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value)} is not JSON serializable")


def build_master_graph() -> StateGraph:
    """Build the LangGraph state machine coordinating the agents."""

    graph = StateGraph(AgentState)
    graph.add_node("classify_intent", _classify_intent)
    graph.add_node("augment_timeframe", _augment_timeframe)
    graph.add_node("run_intent", _run_intent)
    graph.add_node("format_response", _format_response)

    graph.set_entry_point("classify_intent")
    graph.add_edge("classify_intent", "augment_timeframe")
    graph.add_edge("augment_timeframe", "run_intent")
    graph.add_edge("run_intent", "format_response")
    graph.add_edge("format_response", END)

    return graph

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict

import numpy as np
import pandas as pd
from app.ai.master_agent.state import AgentState, ensure_steps, update_state
from app.ai.master_agent.tools import (
    llm_classify_intent,
    llm_generate_reply,
    llm_parse_query_metadata,
)
from app.ai.sub_agents.analytics_agent.agent import run_analytics_intent
from app.ai.sub_agents.prediction_agent.agent import run_prediction_intent
from langgraph.constants import END
from langgraph.graph import StateGraph


def _classify_intent(state: AgentState) -> AgentState:
    ensure_steps(state)
    intent = llm_classify_intent(state["query"], history=state.get("history", []))
    if not intent:
        state["steps"].append("LLM intent unavailable → clarification required")
        return update_state(state, intent="clarify")
    state["steps"].append(f"LLM classified intent '{intent}'")
    return update_state(state, intent=intent)


def _augment_timeframe(state: AgentState) -> AgentState:
    ensure_steps(state)
    if state.get("intent") in {"greeting", "gratitude", "clarify"}:
        state["steps"].append("Skipped timeframe (non-analytic intent)")
        return state
    df = state["data"]
    metadata = _get_llm_metadata(state, df)
    timeframe = _resolve_timeframe(metadata, df)
    if timeframe:
        state["steps"].append(
            f"Applied LLM timeframe {timeframe['start'].date()} → {timeframe['end'].date()}"  # noqa: E501
        )
    else:
        state["steps"].append("No timeframe detected by LLM")
    return update_state(state, timeframe=timeframe or {})


def _augment_filters(state: AgentState) -> AgentState:
    ensure_steps(state)
    if state.get("intent") in {"greeting", "gratitude", "clarify"}:
        state["steps"].append("Skipped filters (non-analytic intent)")
        return state
    df = state["data"]
    metadata = _get_llm_metadata(state, df)
    filters = _apply_llm_filters({}, metadata, df)
    if filters:
        state["steps"].append(
            "Applied LLM filters: " + ", ".join(f"{k}={v}" for k, v in filters.items())
        )
    horizon = _extract_llm_horizon(metadata)
    if horizon:
        state["forecast_horizon_days"] = horizon
        state["steps"].append(f"LLM forecast horizon set to {horizon} days")
    return update_state(state, filters=filters)


def _run_intent(state: AgentState) -> AgentState:
    intent = state.get("intent")
    if intent == "gratitude":
        result = {
            "summary": "Glad to help.",
            "intent": intent,
            "chart": None,
            "table": None,
        }
    elif intent == "greeting":
        result = {
            "summary": "Hello! I am Hermes. Ask me about shipments, delays, or predictions.",  # noqa: E501
            "intent": intent,
            "chart": None,
            "table": None,
        }
    elif intent == "clarify":
        reply = llm_generate_reply(state["query"], history=state.get("history", []))
        result = {"summary": reply, "intent": intent, "chart": None, "table": None}
        state["steps"].append("LLM clarification generated")
    elif intent in {"conversation", "text_only"}:
        base = (
            llm_classify_intent(state["query"], history=state.get("history", []))
            or "analytics"
        )
        if base not in {
            "route",
            "warehouse",
            "delay_reason",
            "delay",
            "analytics",
            "prediction",
        }:
            base = "analytics"
        prior = state["intent"]
        state["intent"] = base
        analytic = (
            run_analytics_intent(state)
            if base != "prediction"
            else run_prediction_intent(state)
        )
        state["intent"] = prior
        prefix = "Text overview: " if prior == "conversation" else "Summary: "
        result = {
            "summary": prefix + analytic.get("summary", ""),
            "intent": prior,
            "chart": None,
            "table": None,
        }
        state["steps"].append(f"Conversation mapped to analytic intent '{base}'")
    elif intent == "prediction":
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
    graph.add_node("augment_filters", _augment_filters)
    graph.add_node("run_intent", _run_intent)
    graph.add_node("format_response", _format_response)

    graph.set_entry_point("classify_intent")
    graph.add_edge("classify_intent", "augment_timeframe")
    graph.add_edge("augment_timeframe", "augment_filters")
    graph.add_edge("augment_filters", "run_intent")
    graph.add_edge("run_intent", "format_response")
    graph.add_edge("format_response", END)

    return graph


def _get_llm_metadata(
    state: AgentState, df: pd.DataFrame | None = None
) -> Dict[str, Any]:
    metadata = state.get("llm_metadata")
    if metadata is not None:
        return metadata

    options: Dict[str, list[str]] = {}
    if df is not None:
        columns = {
            "route": [],
            "warehouse": [],
            "delay_reason": [],
        }
        for column in columns:
            if column in df.columns:
                values = df[column].dropna().unique()
                columns[column] = sorted({str(v) for v in values})
        options = columns

    try:
        metadata = llm_parse_query_metadata(
            state["query"], options=options, history=state.get("history", [])
        )
    except RuntimeError as exc:  # missing credentials or client failure
        state["steps"].append(f"LLM metadata unavailable: {exc}")
        metadata = {}

    state["llm_metadata"] = metadata or {}
    if metadata:
        state["steps"].append("Loaded LLM metadata for query interpretation")
    return state["llm_metadata"]


def _resolve_timeframe(
    metadata: Dict[str, Any], df: pd.DataFrame
) -> Dict[str, datetime]:
    if not metadata:
        return {}
    timeframe = metadata.get("timeframe")
    if not isinstance(timeframe, dict):
        return {}
    tf_type = timeframe.get("type")
    value = timeframe.get("value") or {}

    if tf_type == "relative":
        amount = value.get("amount")
        unit = value.get("unit")
        if isinstance(amount, (int, float)) and isinstance(unit, str):
            amount_int = int(amount)
            if amount_int <= 0:
                return {}
            days = _convert_unit_to_days(amount_int, unit)
            end_date = df["date"].max()
            start_date = end_date - timedelta(days=days)
            return {"start": start_date, "end": end_date}
    elif tf_type == "absolute":
        start = pd.to_datetime(value.get("start"), errors="coerce") if value else None
        end = pd.to_datetime(value.get("end"), errors="coerce") if value else None
        if pd.notna(start) and pd.notna(end):
            return {"start": start, "end": end}
    return {}


def _apply_llm_filters(
    filters: Dict[str, Any], metadata: Dict[str, Any], df: pd.DataFrame
) -> Dict[str, Any]:
    if not metadata:
        return filters
    llm_filters = metadata.get("filters")
    if not isinstance(llm_filters, dict):
        return filters

    for column in ("route", "warehouse", "delay_reason"):
        suggested = llm_filters.get(column)
        if not suggested:
            continue
        if column not in df.columns:
            continue
        value = _match_dataset_value(df[column].unique(), suggested)
        if value is not None:
            filters[column] = value
    return filters


def _match_dataset_value(values: Any, candidates: Any) -> Any:
    value_map = {
        str(v).strip().lower(): v
        for v in values
        if isinstance(v, (str, int)) and not pd.isna(v)
    }
    if isinstance(candidates, (list, tuple)):
        for candidate in candidates:
            if not candidate:
                continue
            key = str(candidate).strip().lower()
            if key in value_map:
                return value_map[key]
    elif isinstance(candidates, str):
        key = candidates.strip().lower()
        return value_map.get(key)
    return None


def _extract_llm_horizon(metadata: Dict[str, Any]) -> int | None:
    if not metadata:
        return None
    forecast = metadata.get("forecast")
    if not isinstance(forecast, dict):
        return None
    horizon = forecast.get("horizon_days")
    if isinstance(horizon, (int, float)) and horizon > 0:
        return min(int(horizon), 365)
    return None


def _convert_unit_to_days(value: int, unit: str) -> int:
    """Map relative timeframe units to day counts."""
    unit = unit.lower().strip()
    mapping = {
        "day": 1,
        "days": 1,
        "week": 7,
        "weeks": 7,
        "month": 30,
        "months": 30,
        "quarter": 90,
        "quarters": 90,
        "year": 365,
        "years": 365,
    }
    return value * mapping.get(unit, 1)

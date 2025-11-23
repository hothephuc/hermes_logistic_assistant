from __future__ import annotations

import json
import re
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
    """Heuristic + LLM + conversational follow-up support."""
    ensure_steps(state)
    query = state["query"].lower()
    history = state.get("history", [])

    gratitude_tokens = [
        "thanks",
        "thank you",
        "thank u",
        "much appreciated",
        "appreciate it",
    ]
    if any(tok in query for tok in gratitude_tokens) and len(query.split()) <= 6:
        state["steps"].append("Heuristic classified intent as 'gratitude'")
        return update_state(state, intent="gratitude")

    greeting_tokens = [
        "hi",
        "hello",
        "hey",
        "greetings",
        "good morning",
        "good afternoon",
        "good evening",
    ]
    if (
        any(query.strip().startswith(tok) for tok in greeting_tokens)
        and len(query.split()) <= 4
    ):
        state["steps"].append("Heuristic classified intent as 'greeting'")
        return update_state(state, intent="greeting")

    ambiguous = len(query.split()) <= 4 and not any(
        k in query
        for k in ["predict", "forecast", "warehouse", "route", "reason", "delay"]
    )

    if history and ambiguous:
        last_intent = next(
            (
                h["intent"]
                for h in reversed(history)
                if h.get("intent") and h["intent"] not in ("greeting", "clarify")
            ),
            None,
        )
        if last_intent:
            state["steps"].append(f"Context reuse of previous intent '{last_intent}'")
            return update_state(state, intent=last_intent)

    llm_intent = llm_classify_intent(query, history=history)
    if llm_intent:
        state["steps"].append(f"LLM classified intent as '{llm_intent}'")
        if llm_intent == "analytics" and ambiguous:
            state["steps"].append("Marked as 'clarify' due to ambiguity")
            return update_state(state, intent="clarify")
        return update_state(state, intent=llm_intent)

    intent = "analytics"
    if any(t in query for t in ["predict", "forecast", "next week", "projection"]):
        intent = "prediction"
    elif "warehouse" in query:
        intent = "warehouse"
    elif "route" in query:
        intent = "route"
    elif "reason" in query:
        intent = "delay_reason"
    elif any(
        t in query for t in ["average delay", "delay last", "delay in", "delay stats"]
    ):
        intent = "delay"
    state["steps"].append(f"Heuristic classified intent as '{intent}'")
    if intent == "analytics" and ambiguous:
        state["steps"].append("Heuristic ambiguity detected → intent set to 'clarify'")
        return update_state(state, intent="clarify")
    return update_state(state, intent=intent)


def _augment_timeframe(state: AgentState) -> AgentState:
    """Derive simple timeframe filters based on temporal hints in the query."""

    # Skip timeframe for greeting or clarify
    if state.get("intent") in {"greeting", "clarify"}:
        state["steps"].append("Skipped timeframe augmentation for non-analytic intent")
        return state

    ensure_steps(state)

    query = state["query"].lower()
    df = state["data"]
    metadata = _get_llm_metadata(state, df)
    timeframe: Dict[str, datetime] = {}

    timeframe = _resolve_timeframe(metadata, df)
    timeframe_source = "llm" if timeframe else None

    if not timeframe:
        if "last week" in query:
            end_date = df["date"].max()
            start_date = end_date - timedelta(days=7)
            timeframe = {"start": start_date, "end": end_date}
            timeframe_source = "heuristic"
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
                timeframe_source = "heuristic"
        elif "last month" in query:
            end_date = df["date"].max()
            start_date = end_date - timedelta(days=30)
            timeframe = {"start": start_date, "end": end_date}
            timeframe_source = "heuristic"

    if timeframe:
        label = "LLM metadata" if timeframe_source == "llm" else "heuristics"
        state["steps"].append(
            f"Applied timeframe ({label}) between {timeframe['start'].date()} "
            + f"and {timeframe['end'].date()}"
        )
    return update_state(state, timeframe=timeframe)


def _augment_filters(state: AgentState) -> AgentState:
    """Infer entity filters and forecast horizon from the query text."""

    ensure_steps(state)
    query = state["query"].lower()
    df = state["data"]
    metadata = _get_llm_metadata(state, df)
    filters = dict(state.get("filters", {}))

    def _detect(column: str, values) -> None:
        for value in values:
            if pd.isna(value):
                continue
            token = str(value).lower()
            if token and token in query:
                if filters.get(column) != value:
                    filters[column] = value
                return

    filters = _apply_llm_filters(filters, metadata, df)

    _detect("route", df["route"].unique())
    _detect("warehouse", df["warehouse"].unique())
    _detect("delay_reason", df["delay_reason"].unique())

    if filters:
        detected = ", ".join(f"{k}={v}" for k, v in filters.items())
        state["steps"].append(f"Applied entity filters: {detected}")

    horizon = _extract_llm_horizon(metadata)
    horizon_source = "llm" if horizon is not None else None
    if horizon is None and state.get("intent") == "prediction":
        heuristic = _extract_forecast_horizon(query)
        if heuristic is not None:
            horizon = max(1, min(heuristic, 120))
            horizon_source = "heuristic"
            if horizon != state.get("forecast_horizon_days"):
                state["steps"].append(f"Set forecast horizon to {horizon} days")

    if horizon is not None:
        if horizon_source == "llm" and horizon != state.get("forecast_horizon_days"):
            state["steps"].append(f"LLM set forecast horizon to {horizon} days")
        state["forecast_horizon_days"] = horizon

    state["filters"] = filters
    return state


def _run_intent(state: AgentState) -> AgentState:
    """Dispatch the query to the appropriate specialised agent."""

    if state.get("intent") == "gratitude":
        result = {
            "summary": "You’re welcome! Let me know if you need anything else about your shipments.",  # noqa: E501
            "intent": "gratitude",
            "chart": None,
            "table": None,
        }
    elif state.get("intent") == "greeting":
        result = {
            "summary": "Hello! I am Hermes. Ask me about shipments, delays, or predictions.",  # noqa: E501
            "intent": "greeting",
            "chart": None,
            "table": None,
        }
    elif state.get("intent") == "clarify":
        reply = llm_generate_reply(state["query"], history=state.get("history", []))
        result = {
            "summary": reply,
            "intent": "clarify",
            "chart": None,
            "table": None,
        }
        state["steps"].append("Generated clarification reply via LLM")
    elif state.get("intent") in {"conversation", "text_only"}:
        # Derive an underlying analytic intent for generating a summary
        base_intent = _infer_base_analytic_intent(state["query"])
        original_intent = state.get("intent")
        prev_intent = state.get("intent")
        state["intent"] = base_intent
        analytic_result = run_analytics_intent(state)
        state["intent"] = prev_intent  # restore
        summary_prefix = (
            "Here's a textual overview: "
            if original_intent == "conversation"
            else "Summary: "
        )
        result = {
            "summary": summary_prefix
            + analytic_result.get("summary", "No overview available."),
            "intent": original_intent,
            "chart": None,  # explicitly suppress visualization
            "table": None,
        }
        state["steps"].append(
            f"Derived base analytic intent '{base_intent}' for conversational/text-only response"  # noqa: E501
        )
    elif state.get("intent") == "prediction":
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


def _infer_base_analytic_intent(query: str) -> str:
    q = query.lower()
    if any(t in q for t in ["predict", "forecast", "next week", "projection"]):
        return "prediction"
    if "warehouse" in q:
        return "warehouse"
    if "route" in q:
        return "route"
    if "reason" in q:
        return "delay_reason"
    if any(
        t in q
        for t in ["average delay", "delay last", "delay in", "delay stats", "delay"]
    ):
        return "delay"
    return "analytics"


def _extract_forecast_horizon(query: str) -> int | None:
    """Parse phrases like 'next 10 days' or 'next month' into day counts."""

    patterns = [
        r"next\s+(\d+)\s+(day|days|week|weeks|month|months|quarter|quarters)",
        r"forecast\s+(\d+)\s+(day|days|week|weeks|month|months)",
        r"(\d+)\s+(day|days|week|weeks|month|months)\s+(ahead|forward|out)",
    ]
    for pattern in patterns:
        match = re.search(pattern, query)
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            return _convert_unit_to_days(value, unit)

    heuristics = [
        ("next week", 7),
        ("next couple of weeks", 14),
        ("next few weeks", 21),
        ("next few days", 5),
        ("coming days", 5),
        ("next month", 30),
        ("next quarter", 90),
    ]
    for phrase, days in heuristics:
        if phrase in query:
            return days
    return None


def _convert_unit_to_days(value: int, unit: str) -> int:
    unit = unit.lower()
    if unit.startswith("day"):
        return value
    if unit.startswith("week"):
        return value * 7
    if unit.startswith("month"):
        return value * 30
    if unit.startswith("quarter"):
        return value * 90
    return value


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

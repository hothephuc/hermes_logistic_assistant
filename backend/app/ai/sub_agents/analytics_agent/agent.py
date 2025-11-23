from __future__ import annotations

import re
from typing import Any, Dict

import pandas as pd
from app.ai.master_agent.state import AgentState


def run_analytics_intent(state: AgentState) -> Dict[str, Any]:
    """Generate analytics outputs for the classified intent."""

    df = _apply_filters(state)
    intent = state.get("intent", "analytics")

    if df.empty:
        return {
            "summary": "I could not find any matching shipments for the requested filters.",  # noqa: E501
            "chart": None,
            "table": None,
        }

    if intent == "route":
        return _route_performance(state, df)
    if intent == "warehouse":
        return _warehouse_performance(state, df)
    if intent == "delay_reason":
        return _delay_reason_breakdown(state, df)
    if intent == "delay":
        return _delay_statistics(state, df)

    # default overview
    return _quick_overview(state, df)


def _apply_filters(state: AgentState) -> pd.DataFrame:
    df = state["data"].copy()

    timeframe = state.get("timeframe", {})
    if timeframe:
        start = timeframe.get("start")
        end = timeframe.get("end")
        if start is not None:
            df = df[df["date"] >= start]
        if end is not None:
            df = df[df["date"] <= end]

    for column, value in state.get("filters", {}).items():
        if column in df.columns:
            df = df[df[column] == value]

    return df


def _route_performance(state: AgentState, df: pd.DataFrame) -> Dict[str, Any]:
    summary_rows = (
        df.assign(is_delayed=df["delay_minutes"] > 0)
        .groupby("route")
        .agg(
            delayed_shipments=("is_delayed", "sum"),
            total_delay_minutes=("delay_minutes", "sum"),
            avg_delay_minutes=("delay_minutes", "mean"),
        )
        .reset_index()
    )

    top_route = summary_rows.sort_values("delayed_shipments", ascending=False).iloc[0]
    summary = (
        f"{top_route['route']} experienced the most delays with "
        f"{int(top_route['delayed_shipments'])} delayed shipments and "
        f"{int(top_route['total_delay_minutes'])} minutes lost."
    )

    chart_data = [
        {
            "label": row.route,
            "value": int(row.delayed_shipments),
            "tooltip": f"Delay minutes: {int(row.total_delay_minutes)}",
        }
        for row in summary_rows.itertuples()
    ]

    return {
        "summary": summary,
        "intent": "route",
        "chart": {
            "type": "bar",
            "title": "Delayed Shipments per Route",
            "x_label": "Route",
            "y_label": "Delayed Shipments",
            "data": chart_data,
            "dataset_label": "Delayed Shipments",
        },
        "table": {
            "columns": [
                {"key": "route", "label": "Route"},
                {"key": "delayed_shipments", "label": "Delayed"},
                {"key": "total_delay_minutes", "label": "Total Delay (min)"},
                {"key": "avg_delay_minutes", "label": "Avg Delay (min)"},
            ],
            "rows": summary_rows.round({"avg_delay_minutes": 2}).to_dict(
                orient="records"
            ),
        },
    }


def _delay_reason_breakdown(state: AgentState, df: pd.DataFrame) -> Dict[str, Any]:
    delayed_df = df[df["delay_minutes"] > 0]
    reason_summary = (
        delayed_df.groupby("delay_reason")
        .agg(
            incidents=("id", "count"),
            total_delay_minutes=("delay_minutes", "sum"),
        )
        .reset_index()
        .sort_values("incidents", ascending=False)
    )

    chart_data = [
        {
            "label": row.delay_reason,
            "value": int(row.incidents),
            "tooltip": f"Total delay: {int(row.total_delay_minutes)} minutes",
        }
        for row in reason_summary.itertuples()
    ]

    summary = "Total delayed shipments by reason: " + ", ".join(
        f"{row.delay_reason} ({int(row.incidents)})"
        for row in reason_summary.itertuples()
    )

    return {
        "summary": summary,
        "intent": "delay_reason",
        "chart": {
            "type": "pie",
            "title": "Delay Incidents by Reason",
            "data": chart_data,
        },
        "table": {
            "columns": [
                {"key": "delay_reason", "label": "Delay Reason"},
                {"key": "incidents", "label": "Incidents"},
                {"key": "total_delay_minutes", "label": "Total Delay (min)"},
            ],
            "rows": reason_summary.to_dict(orient="records"),
        },
    }


def _warehouse_performance(state: AgentState, df: pd.DataFrame) -> Dict[str, Any]:
    summary_rows = (
        df.groupby("warehouse")
        .agg(
            avg_delivery_time=("delivery_time", "mean"),
            delayed_shipments=("delay_minutes", lambda s: (s > 0).sum()),
            total_shipments=("id", "count"),
        )
        .reset_index()
    )

    threshold = _extract_numeric_threshold(state["query"])
    if threshold is not None:
        summary_rows = summary_rows[summary_rows["avg_delivery_time"] > threshold]
        filter_note = f" above {threshold} days"
    else:
        filter_note = ""

    if summary_rows.empty:
        return {
            "summary": "No warehouses met the requested delivery time condition.",
            "chart": None,
            "table": None,
        }

    chart_data = [
        {
            "label": row.warehouse,
            "value": round(row.avg_delivery_time, 2),
            "tooltip": f"Delayed shipments: {int(row.delayed_shipments)} of {int(row.total_shipments)}",  # noqa: E501
        }
        for row in summary_rows.itertuples()
    ]

    summary = (
        "Warehouses with average delivery time"
        + filter_note
        + ": "
        + ", ".join(
            f"{row.warehouse} ({row.avg_delivery_time:.2f} days)"
            for row in summary_rows.itertuples()
        )
    )

    return {
        "summary": summary,
        "intent": "warehouse",
        "chart": {
            "type": "bar",
            "title": "Average Delivery Time per Warehouse",
            "x_label": "Warehouse",
            "y_label": "Avg Delivery Time (days)",
            "data": chart_data,
            "dataset_label": "Avg Delivery Time",
        },
        "table": {
            "columns": [
                {"key": "warehouse", "label": "Warehouse"},
                {"key": "avg_delivery_time", "label": "Avg Delivery (days)"},
                {"key": "delayed_shipments", "label": "Delayed"},
                {"key": "total_shipments", "label": "Total"},
            ],
            "rows": summary_rows.round({"avg_delivery_time": 2}).to_dict(
                orient="records"
            ),
        },
    }


def _delay_statistics(state: AgentState, df: pd.DataFrame) -> Dict[str, Any]:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    daily = (
        df.groupby(df["date"].dt.date)
        .agg(
            avg_delay=("delay_minutes", "mean"),
            delayed_shipments=("delay_minutes", lambda s: (s > 0).sum()),
        )
        .reset_index()
    )

    avg_delay = df["delay_minutes"].mean()
    summary = f"Average delay across the selected period is {avg_delay:.1f} minutes per shipment."  # noqa: E501

    chart_data = [
        {"label": str(row["date"]), "value": round(row["avg_delay"], 2)}
        for _, row in daily.iterrows()
    ]

    return {
        "summary": summary,
        "intent": "delay",
        "chart": {
            "type": "line",
            "title": "Average Delay by Day",
            "x_label": "Date",
            "y_label": "Avg Delay (min)",
            "data": chart_data,
            "dataset_label": "Avg Delay",
        },
        "table": {
            "columns": [
                {"key": "date", "label": "Date"},
                {"key": "avg_delay", "label": "Avg Delay (min)"},
                {"key": "delayed_shipments", "label": "Delayed Shipments"},
            ],
            "rows": daily.round({"avg_delay": 2}).to_dict(orient="records"),
        },
    }


def _quick_overview(state: AgentState, df: pd.DataFrame) -> Dict[str, Any]:
    total_shipments = len(df)
    delayed = int((df["delay_minutes"] > 0).sum())
    avg_delivery = df["delivery_time"].mean()
    avg_delay = df["delay_minutes"].mean()

    summary = (
        f"Processed {total_shipments} shipments. {delayed} experienced delays. "
        f"Average delivery time is {avg_delivery:.2f} days with {avg_delay:.1f} minutes of delay."  # noqa: E501
    )

    trend = (
        df.assign(date=df["date"].dt.date)
        .groupby("date")
        .agg(total_delay=("delay_minutes", "sum"))
        .reset_index()
    )

    chart_data = [
        {"label": str(row["date"]), "value": row["total_delay"]}
        for _, row in trend.iterrows()
    ]

    return {
        "summary": summary,
        "intent": "analytics",
        "chart": {
            "type": "line",
            "title": "Total Delay Minutes Over Time",
            "x_label": "Date",
            "y_label": "Total Delay (min)",
            "data": chart_data,
            "dataset_label": "Total Delay",
        },
        "table": None,
    }


def _extract_numeric_threshold(text: str) -> float | None:
    match = re.search(r"(above|over|greater than)\s+(\d+(?:\.\d+)?)", text.lower())
    if match:
        return float(match.group(2))
    return None

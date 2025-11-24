from __future__ import annotations

from typing import Any, Dict

import pandas as pd
from app.ai.master_agent.state import AgentState
from app.ai.master_agent.tools import (
    llm_generate_delay_plan,
    llm_generate_route_plan,
    llm_generate_warehouse_plan,
)


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
            avg_delivery_time=("delivery_time", "mean"),
            total_shipments=("id", "count"),
        )
        .reset_index()
    )
    if summary_rows.empty:
        return {"summary": "No route data available.", "chart": None, "table": None}

    plan = llm_generate_route_plan(state.get("query", ""))
    allowed = {
        "delayed_shipments": "Delayed Shipments",
        "total_delay_minutes": "Total Delay (min)",
        "avg_delay_minutes": "Avg Delay (min)",
        "avg_delivery_time": "Avg Delivery Time (days)",
        "total_shipments": "Total Shipments",
    }
    sort_field = (
        plan.get("sort_field")
        if plan.get("sort_field") in allowed
        else "delayed_shipments"
    )
    ascending = (plan.get("sort_order") or "desc").lower() == "asc"
    metric_label = plan.get("metric_label") or allowed[sort_field]
    chart_title = plan.get("chart_title") or f"{metric_label} by Route"
    focus_phrase = plan.get("focus_phrase") or (
        "lowest average delay"
        if ascending and "delay" in sort_field
        else "highest delay"
        if not ascending and "delay" in sort_field
        else "best-performing"
        if ascending
        else "highest"
    )

    summary_rows = summary_rows.sort_values(sort_field, ascending=ascending)
    period = _describe_period(state.get("timeframe"))
    top_row = summary_rows.iloc[0]

    ctx = {
        "period": period,
        "top_label": top_row["route"],
        "metric_label": metric_label,
        "metric_value": _format_metric_value(top_row[sort_field]),
        "focus_phrase": focus_phrase,
        "delayed_shipments": int(top_row["delayed_shipments"]),
        "total_shipments": int(top_row["total_shipments"]),
        "avg_delay_minutes": _format_metric_value(top_row["avg_delay_minutes"]),
        "total_delay_minutes": _format_metric_value(top_row["total_delay_minutes"]),
    }

    template = plan.get("summary_template")
    summary = _format_summary_template(template, ctx) if template else ""
    if not summary:
        summary = (
            f"Best route for {period} by {metric_label.lower()} is {ctx['top_label']} "
            f"({ctx['metric_value']})."
        )

    chart_data = [
        {
            "label": r.route,
            "value": _format_metric_value(getattr(r, sort_field)),
            "tooltip": f"Delayed {int(r.delayed_shipments)} / Total {int(r.total_shipments)}",
        }
        for r in summary_rows.itertuples()
    ]

    return {
        "summary": summary,
        "intent": "route",
        "chart": {
            "type": "bar",
            "title": chart_title,
            "x_label": "Route",
            "y_label": metric_label,
            "data": chart_data,
            "dataset_label": metric_label,
        },
        "table": {
            "columns": [
                {"key": "route", "label": "Route"},
                {"key": "delayed_shipments", "label": "Delayed"},
                {"key": "total_delay_minutes", "label": "Total Delay (min)"},
                {"key": "avg_delay_minutes", "label": "Avg Delay (min)"},
                {"key": "avg_delivery_time", "label": "Avg Delivery Time (days)"},
                {"key": "total_shipments", "label": "Total Shipments"},
            ],
            "rows": summary_rows.round(
                {"avg_delay_minutes": 2, "avg_delivery_time": 2}
            ).to_dict(orient="records"),
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
            avg_delay_minutes=("delay_minutes", "mean"),
        )
        .reset_index()
    )
    if summary_rows.empty:
        return {"summary": "No warehouse data available.", "chart": None, "table": None}

    plan = llm_generate_warehouse_plan(state.get("query", ""))
    allowed = {
        "avg_delivery_time": "Avg Delivery Time (days)",
        "delayed_shipments": "Delayed Shipments",
        "avg_delay_minutes": "Avg Delay (min)",
        "total_shipments": "Total Shipments",
    }
    metric_field = (
        plan.get("metric_field")
        if plan.get("metric_field") in allowed
        else "avg_delivery_time"
    )
    metric_label = plan.get("metric_label") or allowed[metric_field]
    ascending = (
        plan.get("sort_order") or ("asc" if metric_field.startswith("avg") else "desc")
    ).lower() == "asc"
    focus_phrase = plan.get("focus_phrase") or (
        "best-performing" if ascending else "highest"
    )
    chart_title = plan.get("chart_title") or f"{metric_label} by Warehouse"

    threshold = plan.get("delivery_time_threshold")
    try:
        threshold = float(threshold) if threshold is not None else None
    except (TypeError, ValueError):
        threshold = None
    if threshold is not None:
        summary_rows = summary_rows[summary_rows["avg_delivery_time"] > threshold]

    if summary_rows.empty:
        return {
            "summary": "No warehouses matched threshold.",
            "chart": None,
            "table": None,
        }

    summary_rows = summary_rows.sort_values(metric_field, ascending=ascending)
    period = _describe_period(state.get("timeframe"))
    top = summary_rows.iloc[0]
    template_ctx = {
        "period": period,
        "top_label": top["warehouse"],
        "metric_label": metric_label,
        "metric_value": _format_metric_value(top[metric_field]),
        "focus_phrase": focus_phrase,
        "threshold": threshold,
        "delayed_shipments": int(top["delayed_shipments"]),
        "total_shipments": int(top["total_shipments"]),
    }
    template = plan.get("summary_template")
    summary = _format_summary_template(template, template_ctx) if template else ""
    if not summary:
        extra = f" above {threshold} days" if threshold is not None else ""
        summary = (
            f"{focus_phrase.capitalize()} warehouse{extra} for {period} is {template_ctx['top_label']} "
            f"with {metric_label.lower()} of {template_ctx['metric_value']}."
        )

    chart_data = [
        {
            "label": r.warehouse,
            "value": _format_metric_value(getattr(r, metric_field)),
            "tooltip": f"Delayed {int(r.delayed_shipments)} / Total {int(r.total_shipments)}",
        }
        for r in summary_rows.itertuples()
    ]

    return {
        "summary": summary,
        "intent": "warehouse",
        "chart": {
            "type": "bar",
            "title": chart_title,
            "x_label": "Warehouse",
            "y_label": metric_label,
            "data": chart_data,
            "dataset_label": metric_label,
        },
        "table": {
            "columns": [
                {"key": "warehouse", "label": "Warehouse"},
                {"key": "avg_delivery_time", "label": "Avg Delivery (days)"},
                {"key": "avg_delay_minutes", "label": "Avg Delay (min)"},
                {"key": "delayed_shipments", "label": "Delayed"},
                {"key": "total_shipments", "label": "Total"},
            ],
            "rows": summary_rows.round(
                {"avg_delivery_time": 2, "avg_delay_minutes": 2}
            ).to_dict(orient="records"),
        },
    }


def _delay_statistics(state: AgentState, df: pd.DataFrame) -> Dict[str, Any]:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    period = _describe_period(state.get("timeframe"))
    plan = llm_generate_delay_plan(state.get("query", ""))
    metrics = _execute_generated_code(plan.get("python_code"), df)
    if not metrics:
        metrics = _default_delay_metrics(df)
    template = plan.get("summary_template")
    ctx = {**metrics, "period": period}
    summary = (
        _format_summary_template(template, ctx)
        if template
        else _default_delay_summary(metrics, period)
    )
    daily = (
        df.groupby(df["date"].dt.date)
        .agg(
            avg_delay=("delay_minutes", "mean"),
            delayed_shipments=("delay_minutes", lambda s: (s > 0).sum()),
        )
        .reset_index()
    )
    chart_data = [
        {"label": str(r["date"]), "value": round(r["avg_delay"], 2)}
        for _, r in daily.iterrows()
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


def _execute_generated_code(code: str | None, df: pd.DataFrame) -> Dict[str, Any]:
    if not code or "compute_metrics" not in code:
        return {}
    safe_builtins = {
        "len": len,
        "float": float,
        "int": int,
        "round": round,
        "max": max,
        "min": min,
        "sum": sum,
    }
    local_vars: Dict[str, Any] = {}
    try:
        exec(code, {"__builtins__": safe_builtins, "pd": pd}, local_vars)
    except Exception:
        return {}
    func = local_vars.get("compute_metrics")
    if not callable(func):
        return {}
    try:
        result = func(df.copy())
    except Exception:
        return {}
    return result if isinstance(result, dict) else {}


def _default_delay_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    return {
        "total_delay_minutes": float(df["delay_minutes"].sum()),
        "average_delay_minutes": float(df["delay_minutes"].mean()),
        "shipment_count": int(len(df)),
    }


def _default_delay_summary(metrics: Dict[str, Any], period: str) -> str:
    total = metrics.get("total_delay_minutes", 0.0)
    avg = metrics.get("average_delay_minutes", 0.0)
    count = metrics.get("shipment_count", 0)
    return (
        f"Total delay time for {period} is {total:.0f} minutes across {count} shipments. "
        f"Average delay across {period} is {avg:.1f} minutes per shipment."
    )


def _describe_period(timeframe: Dict[str, Any] | None) -> str:
    if not timeframe:
        return "the selected period"
    start = timeframe.get("start")
    end = timeframe.get("end")
    if start is not None and end is not None:
        s = pd.to_datetime(start).strftime("%b %d, %Y")
        e = pd.to_datetime(end).strftime("%b %d, %Y")
        return f"{s} to {e}"
    return "the selected period"


def _format_metric_value(v: Any) -> Any:
    try:
        num = float(v)
    except (TypeError, ValueError):
        return v
    if num.is_integer():
        return int(num)
    return round(num, 2)


def _format_summary_template(template: str | None, context: Dict[str, Any]) -> str:
    if not template:
        return ""
    try:
        return template.format(**context)
    except Exception:
        return ""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from app.ai.master_agent.state import AgentState


def run_prediction_intent(state: AgentState) -> Dict[str, object]:
    horizon = int(state.get("forecast_horizon_days", 7) or 7)
    filters = state.get("filters", {})
    df = _apply_filters(state)
    if df.empty:
        return {
            "summary": "Not enough data points to produce a prediction.",
            "chart": None,
            "table": None,
            "recommendations": [],
            "metrics": {"forecast_horizon_days": horizon, "ensemble_estimates": []},
        }

    daily = (
        df.groupby(df["date"].dt.date)
        .agg(avg_delay=("delay_minutes", "mean"))
        .reset_index()
        .sort_values("date")
    )

    if len(daily) < 3:
        return {
            "summary": "I need at least 3 days of delay history to project forward.",
            "chart": None,
            "table": None,
            "recommendations": [],
            "metrics": {"forecast_horizon_days": horizon, "ensemble_estimates": []},
        }

    # Convert to ordinal for regression
    x = np.array(
        [pd.to_datetime(day).toordinal() for day in daily["date"]], dtype=float
    )
    y = daily["avg_delay"].to_numpy(dtype=float)

    slope, intercept = np.polyfit(x, y, 1)

    # Forecast future horizon
    last_date = pd.to_datetime(daily["date"].iloc[-1])
    forecast_points = []
    for i in range(1, horizon + 1):
        next_day = last_date + timedelta(days=i)
        prediction = slope * next_day.toordinal() + intercept
        forecast_points.append(
            {
                "date": next_day.date(),
                "predicted_avg_delay": max(prediction, 0),
            }
        )

    window_avg = np.mean([point["predicted_avg_delay"] for point in forecast_points])

    base_df = _apply_filters(state, include_entity_filters=False)
    ensemble_estimates = _build_ensemble_estimates(base_df, filters)
    recommendations = _format_recommendations(ensemble_estimates)
    risk_note = _primary_delay_risk(base_df)

    summary_parts: List[str] = [
        f"Projected average delay over the next {_describe_horizon(horizon)} is {window_avg:.1f} minutes per shipment."  # noqa: E501
    ]
    if filters:
        filter_text = ", ".join(f"{k}={v}" for k, v in filters.items())
        summary_parts.append(f"Filters applied: {filter_text}.")
    if recommendations:
        summary_parts.append(f"Top recommendation: {recommendations[0]}")
    if risk_note:
        summary_parts.append(risk_note)

    summary = " ".join(summary_parts)

    chart_data = [
        {
            "label": str(row["date"]),
            "value": round(row["avg_delay"], 2),
            "isForecast": False,
        }
        for _, row in daily.iterrows()
    ] + [
        {
            "label": str(point["date"]),
            "value": round(point["predicted_avg_delay"], 2),
            "isForecast": True,
        }
        for point in forecast_points
    ]

    return {
        "summary": summary,
        "intent": "prediction",
        "chart": {
            "type": "line",
            "title": "Average Delay Forecast",
            "x_label": "Date",
            "y_label": "Avg Delay (min)",
            "data": chart_data,
            "dataset_label": "Avg Delay",
        },
        "table": {
            "columns": [
                {"key": "date", "label": "Date"},
                {"key": "avg_delay", "label": "Actual Avg Delay"},
            ],
            "rows": daily.round({"avg_delay": 2}).to_dict(orient="records"),
            "forecast": forecast_points,
        },
        "recommendations": recommendations,
        "metrics": {
            "forecast_horizon_days": horizon,
            "ensemble_estimates": ensemble_estimates[:5],
        },
    }


def _apply_filters(
    state: AgentState, *, include_entity_filters: bool = True
) -> pd.DataFrame:
    df = state["data"].copy()

    timeframe = state.get("timeframe", {})
    if timeframe:
        start = timeframe.get("start")
        end = timeframe.get("end")
        if start is not None:
            df = df[df["date"] >= start]
        if end is not None:
            df = df[df["date"] <= end]

    if include_entity_filters:
        for column, value in state.get("filters", {}).items():
            if column in df.columns and value is not None:
                df = df[df[column] == value]

    df["date"] = pd.to_datetime(df["date"])
    return df


def _build_ensemble_estimates(
    df: pd.DataFrame, filters: Dict[str, Any]
) -> List[Dict[str, Any]]:
    if df.empty:
        return []

    feature_cols = ["route", "warehouse", "delay_reason"]
    for col in feature_cols:
        if col not in df.columns:
            return []

    encoded = pd.get_dummies(df[feature_cols], prefix_sep="=")
    if encoded.empty:
        return []

    X = np.column_stack([np.ones(len(encoded)), encoded.to_numpy(dtype=float)])
    y = df["delay_minutes"].to_numpy(dtype=float)

    coeffs: np.ndarray | None = None
    try:
        coeffs, *_ = np.linalg.lstsq(X, y, rcond=None)
    except np.linalg.LinAlgError:
        coeffs = None

    encoded_columns = ["intercept"] + list(encoded.columns)

    route_values = (
        [filters["route"]]
        if filters.get("route")
        else sorted(df["route"].dropna().unique())
    )
    warehouse_values = (
        [filters["warehouse"]]
        if filters.get("warehouse")
        else sorted(df["warehouse"].dropna().unique())
    )
    reason_values = (
        [filters["delay_reason"]]
        if filters.get("delay_reason")
        else sorted(df["delay_reason"].dropna().unique())
    )

    estimates: List[Dict[str, Any]] = []
    for route in route_values:
        for warehouse in warehouse_values:
            for reason in reason_values:
                combo = {
                    "route": route,
                    "warehouse": warehouse,
                    "delay_reason": reason,
                }
                predictions: List[float] = []
                if coeffs is not None:
                    pred = _predict_linear(coeffs, encoded_columns, combo)
                    if pred is not None:
                        predictions.append(pred)
                group_pred = _group_average_delay(df, combo)
                if group_pred is not None:
                    predictions.append(group_pred)

                if not predictions:
                    continue

                combined = float(np.mean(predictions))
                estimates.append(
                    {
                        **combo,
                        "predicted_delay_minutes": round(max(combined, 0), 2),
                    }
                )

    return sorted(estimates, key=lambda item: item["predicted_delay_minutes"])


def _predict_linear(
    coeffs: np.ndarray, columns: List[str], combo: Dict[str, Any]
) -> float | None:
    try:
        row = pd.DataFrame([combo])
        encoded_row = pd.get_dummies(row, prefix_sep="=")
        feature_columns = columns[1:]
        encoded_row = encoded_row.reindex(columns=feature_columns, fill_value=0)
        vector = np.concatenate(([1.0], encoded_row.to_numpy(dtype=float)[0]))
        return float(np.dot(coeffs, vector))
    except Exception:
        return None


def _group_average_delay(df: pd.DataFrame, combo: Dict[str, Any]) -> float | None:
    subset = df.copy()
    for key, value in combo.items():
        subset = subset[subset[key] == value]
    if not subset.empty:
        return float(subset["delay_minutes"].mean())

    fallback_orders = [
        ("route", "warehouse"),
        ("route", "delay_reason"),
        ("warehouse", "delay_reason"),
        ("route",),
        ("warehouse",),
        ("delay_reason",),
    ]

    for keys in fallback_orders:
        partial = df.copy()
        for key in keys:
            partial = partial[partial[key] == combo[key]]
        if not partial.empty:
            return float(partial["delay_minutes"].mean())

    if not df.empty:
        return float(df["delay_minutes"].mean())
    return None


def _format_recommendations(estimates: List[Dict[str, Any]]) -> List[str]:
    formatted: List[str] = []
    for estimate in estimates[:3]:
        route = estimate.get("route")
        warehouse = estimate.get("warehouse")
        reason = estimate.get("delay_reason")
        delay = estimate.get("predicted_delay_minutes")
        route_label = str(route)
        if isinstance(route_label, str) and route_label.lower().startswith("route"):
            route_phrase = route_label
        else:
            route_phrase = f"Route {route_label}"
        reason_clause = (
            "minimal weather risk"
            if isinstance(reason, str) and reason.lower() == "none"
            else f"watch for {str(reason).lower()} delays"
        )
        formatted.append(
            f"{route_phrase} via {warehouse} → ~{float(delay):.1f} min; {reason_clause}."  # noqa: E501
        )
    return formatted


def _primary_delay_risk(df: pd.DataFrame) -> str | None:
    delayed = df[df["delay_minutes"] > 0]
    if delayed.empty:
        return None
    grouped = (
        delayed.groupby("delay_reason")["delay_minutes"]
        .mean()
        .sort_values(ascending=False)
    )
    if grouped.empty:
        return None
    reason = grouped.index[0]
    value = grouped.iloc[0]
    return f"Primary disruption driver: {reason} (~{value:.1f} minutes when it occurs)."


def _describe_horizon(days: int) -> str:
    if days % 30 == 0:
        months = days // 30
        return f"{months} month{'s' if months != 1 else ''}" if months else "0 days"
    if days % 7 == 0 and days >= 7:
        weeks = days // 7
        return f"{weeks} week{'s' if weeks != 1 else ''}"
    return f"{days} day{'s' if days != 1 else ''}"

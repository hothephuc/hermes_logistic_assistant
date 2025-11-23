import json
import logging
import os
from typing import Any, Dict, Optional

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())
try:
    from groq import Groq
except ImportError as e:
    raise RuntimeError(
        "Groq SDK not installed. Add 'groq' to backend dependencies."
    ) from e

_INTENTS = [
    "greeting",
    "gratitude",
    "clarify",
    "prediction",
    "warehouse",
    "route",
    "delay_reason",
    "delay",
    "analytics",
    # New lightweight conversational intents
    "conversation",  # qualitative/explanatory answer, no viz
    "text_only",  # explicit user request for no visualization
]

logger = logging.getLogger("hermes.intent")
if not logger.handlers:
    logging.basicConfig(level=os.getenv("HERMES_LOG_LEVEL", "INFO"))

_MODEL_MAP = {
    "intent": "llama-3.1-8b-instant",
    "clarify": "llama-3.3-70b-versatile",
    "metadata": "llama-3.1-70b-versatile",
    "reasoning": "llama-3.1-70b-versatile",
    "default": "llama-3.1-8b-instant",
}

_CAPABILITY_TOKENS = {
    "reasoning": ["reasoning", "think", "chain", "complex"],
    "function": ["function", "tool", "call"],
    "vision": ["image", "vision", "picture"],
}


def select_model(purpose: str, query: str) -> str:
    for capability, tokens in _CAPABILITY_TOKENS.items():
        if any(t in query.lower() for t in tokens):
            return _MODEL_MAP.get(capability, _MODEL_MAP["default"])
    return _MODEL_MAP.get(purpose, _MODEL_MAP["default"])


def _get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set in environment or .env file.")
    try:
        return Groq(api_key=api_key)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize Groq client: {e}") from e


def llm_classify_intent(query: str, history: list | None = None) -> Optional[str]:
    """
    Use Groq LLM to classify intent with conversation history.
    Raises RuntimeError if Groq is unavailable.
    """
    client = _get_groq_client()
    history = history or []
    recent = history[-3:]
    recent_text = "\n".join(
        f"- User: {h.get('query')} | Intent: {h.get('intent')} | Summary: {h.get('summary')} | Insight: {h.get('insight')}"  # noqa: E501
        for h in recent
        if h.get("query")
    )
    model = select_model("intent", query)
    prompt = (
        "You are an intent classifier for the Hermes logistics analytics assistant.\n"
        "Classify the user's request into ONE intent strictly from this list: \n"
        "greeting = salutations like hi/hello.\n"
        "gratitude = user is thanking or expressing appreciation.\n"
        "clarify = very short / ambiguous request that needs disambiguation.\n"
        "prediction = asks for forecasts, projections, next week, future values.\n"
        "warehouse = comparative performance of warehouses.\n"
        "route = performance or delays by route.\n"
        "delay_reason = why shipments are delayed; breakdown of reasons.\n"
        "delay = delay statistics, averages, patterns (not reasons).\n"
        "analytics = general quantitative overview of current dataset.\n"
        "conversation = explanatory, qualitative question seeking an insight narrative WITHOUT charts (keywords: explain, why, how, tell me about, interpret, insight).\n"  # noqa: E501
        "text_only = user explicitly requests no visualization (keywords: 'no chart', 'just text', 'text only', 'no visualization').\n\n"  # noqa: E501
        "If the user asks for visualization (keywords: show, chart, graph, plot, visualize, bar, line, pie) DO NOT choose conversation/text_only; pick the underlying analytic intent instead.\n"  # noqa: E501
        "Prefer specificity: warehouse/route/delay/delay_reason/prediction over analytics when keywords match.\n"  # noqa: E501
        "Never output anything except valid JSON.\n\n"
        f"Recent conversation (most recent last):\n{recent_text or '(none)'}\n\n"
        f"Current user query: {query}\n"
        'Return ONLY JSON: {\n  "intent": "one_intent"\n}'
    )
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Classify logistics analytics intents."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=64,
    )
    content = completion.choices[0].message.content.strip()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Intent classifier JSON parse failed: %s", content)
        return None
    intent = (data.get("intent") or "").strip()
    if intent not in _INTENTS:
        logger.info(
            "Classifier proposed unknown intent '%s' for query '%s'", intent, query
        )
        return None
    logger.info(
        "Selected intent '%s' via model '%s' for query: %s", intent, model, query
    )
    if intent in _INTENTS:
        return intent
    return None


def llm_generate_reply(query: str, history: list | None = None) -> str:
    """
    Generate a direct conversational reply when intent is unclear.
    Uses a larger Llama 3.3 70B model for richer clarification.
    """
    client = _get_groq_client()
    history = history or []
    recent = history[-3:]
    convo = "\n".join(
        f"User: {h.get('query')}\nAssistant: {(h.get('insight') or h.get('summary'))}"
        for h in recent
        if h.get("summary") or h.get("insight")
    )
    model = select_model("clarify", query)
    prompt = (
        "You are Hermes, a logistics analytics assistant. The user's latest message is ambiguous.\n"  # noqa: E501
        "Ask for clarification or suggest example queries about shipments, delays, warehouses, routes, or predictions.\n"  # noqa: E501
        "Keep it concise.\n\n"
        f"Recent conversation:\n{convo or '(none)'}\n\n"
        f"User message: {query}\n\nReply:"
    )
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Clarify ambiguous logistics queries."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=160,
    )
    return completion.choices[0].message.content.strip()


def llm_parse_query_metadata(
    query: str,
    *,
    options: Dict[str, list[str]] | None = None,
    history: list | None = None,
) -> Dict[str, Any]:
    """Extract timeframe/filter metadata via Groq with structured JSON output."""

    client = _get_groq_client()
    options = options or {}
    history = history or []
    recent = history[-2:]
    recent_text = "\n".join(f"User: {h.get('query')}" for h in recent if h.get("query"))

    context_lines = []
    for key, values in options.items():
        if values:
            joined = ", ".join(str(v) for v in values[:10])
            context_lines.append(f"- {key}: {joined}")
    context = "\n".join(context_lines) or "(no hints provided)"

    model = select_model("metadata", query)
    prompt = (
        "You analyze user logistics questions across languages and return structured JSON.\n"  # noqa: E501
        "Supported fields: route, warehouse, delay_reason.\n"
        "Detect timeframe expressions (language-agnostic) and return either relative ranges or absolute ISO dates.\n"  # noqa: E501
        "If user mentions forecast length, convert to horizon days.\n"
        "Only return values present/derivable from the query.\n\n"
        f"Known entity values to match (case-insensitive):\n{context}\n\n"
        f"Recent user turns:\n{recent_text or '(none)'}\n\n"
        f"Current query: {query}\n\n"
        "Return STRICT JSON: {\n"
        '  "language": "detected language name or code",\n'
        '  "timeframe": {\n'
        '    "type": "relative" | "absolute" | "none",\n'
        '    "value": {"amount": integer, "unit": "day|week|month|quarter|year" } OR {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}\n'  # noqa: E501
        "  },\n"
        '  "filters": {"route": [..], "warehouse": [..], "delay_reason": [..]},\n'
        '  "forecast": {"horizon_days": integer | null}\n'
        "}\n"
        "Use null when data is unavailable."
    )

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Extract logistics query metadata with JSON output.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=220,
        )
    except Exception as exc:
        logger.warning("Metadata extractor call failed: %s", exc)
        return {}

    content = completion.choices[0].message.content.strip()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Metadata extractor JSON parse failed: %s", content)
        return {}
    return data if isinstance(data, dict) else {}

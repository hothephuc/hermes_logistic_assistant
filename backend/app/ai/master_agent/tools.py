import json
import os
from typing import Optional

try:
    from groq import Groq
except ImportError:
    Groq = None  # SDK not installed fallback

_INTENTS = ["prediction", "warehouse", "route", "delay_reason", "delay", "analytics"]


def _get_groq_client() -> Optional[object]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or Groq is None:
        return None
    try:
        return Groq(api_key=api_key)
    except Exception:
        return None


def llm_classify_intent(query: str) -> Optional[str]:
    """
    Use Groq LLM to classify intent.
    Returns an intent string or None on failure.
    """
    client = _get_groq_client()
    if client is None:
        return None

    prompt = (
        "You are an intent classifier for a logistics analytics assistant.\n"
        "Available intents:\n"
        "- prediction: forecasting future delays\n"
        "- warehouse: warehouse performance metrics\n"
        "- route: route delay performance\n"
        "- delay_reason: causes of delays\n"
        "- delay: time-based delay statistics\n"
        "- analytics: general overview when nothing matches\n\n"
        f"User query: {query}\n"
        'Respond ONLY with JSON: {"intent": "one_of_intents"}'
    )
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Classify logistics analytics intents."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=64,
        )
        content = completion.choices[0].message.content.strip()
        # Extract JSON
        data = json.loads(content)
        intent = data.get("intent")
        if intent in _INTENTS:
            return intent
    except Exception:
        return None
    return None

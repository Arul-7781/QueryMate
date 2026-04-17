import os
from typing import Dict, List
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Load environment variables from .env file
load_dotenv()

_CLIENT_CACHE: Dict[str, ChatGroq] = {}


def _get_api_key() -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in .env file")
    return api_key


def _get_model_priority() -> List[str]:
    """
    Returns ordered model priority for failover.

    Priority rules:
    1) GROQ_MODEL (single preferred model) goes first if set.
    2) GROQ_MODELS provides fallback chain (comma-separated).
    3) Default chain if none provided.
    """
    preferred = os.getenv("GROQ_MODEL", "").strip()
    configured = os.getenv("GROQ_MODELS", "").strip()

    if configured:
        models = [m.strip() for m in configured.split(",") if m.strip()]
    else:
        models = [
            "llama-3.1-8b-instant",
            "llama-3.3-70b-versatile",
        ]

    if preferred and preferred not in models:
        models.insert(0, preferred)
    elif preferred:
        models = [preferred] + [m for m in models if m != preferred]

    return models


def _get_client(model_name: str, temperature: float = 0.0) -> ChatGroq:
    cache_key = f"{model_name}:{temperature}"
    if cache_key not in _CLIENT_CACHE:
        _CLIENT_CACHE[cache_key] = ChatGroq(
            model=model_name,
            temperature=temperature,
            api_key=_get_api_key(),
        )
    return _CLIENT_CACHE[cache_key]


def _is_retryable_model_error(exc: Exception) -> bool:
    text = str(exc).lower()
    retry_signals = [
        "rate limit",
        "429",
        "too many requests",
        "timed out",
        "timeout",
        "service unavailable",
        "overloaded",
        "internal server error",
    ]
    return any(token in text for token in retry_signals)


def invoke_with_fallback(prompt: str, temperature: float = 0.0):
    """
    Invoke LLM with automatic fallback across configured models.

    This improves resilience when the primary model hits rate limits
    or transient service errors.
    """
    models = _get_model_priority()
    last_error = None

    for model_name in models:
        try:
            client = _get_client(model_name, temperature=temperature)
            return client.invoke(prompt)
        except Exception as exc:
            last_error = exc
            if not _is_retryable_model_error(exc):
                break

    raise RuntimeError(f"All configured models failed. Last error: {last_error}")

def get_llm():
    """
    Backward-compatible helper returning the primary configured model client.
    """
    primary = _get_model_priority()[0]
    return _get_client(primary, temperature=0.0)
"""
Unified multi-provider LLM access with ordered fallback.
"""

import logging
import time

logger = logging.getLogger(__name__)

_groq_client = None
_hf_client = None
_gemini_client = None


def _get_groq():
    global _groq_client
    if _groq_client is None:
        from config import GROQ_API_KEY

        if GROQ_API_KEY:
            from groq import Groq

            _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client


def _get_hf():
    global _hf_client
    if _hf_client is None:
        from config import HF_TOKEN

        if HF_TOKEN:
            from huggingface_hub import InferenceClient

            _hf_client = InferenceClient(api_key=HF_TOKEN)
    return _hf_client


def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        from config import GEMINI_API_KEY

        if GEMINI_API_KEY:
            from google import genai

            _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client


def _call_groq(model: str, messages: list, max_tokens: int, temperature: float) -> str:
    client = _get_groq()
    if not client:
        raise RuntimeError("Groq API key not configured")

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content


def _call_hf(model: str, messages: list, max_tokens: int, temperature: float) -> str:
    client = _get_hf()
    if not client:
        raise RuntimeError("HuggingFace token not configured")

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content


def _call_gemini(model: str, messages: list, max_tokens: int, temperature: float) -> str:
    client = _get_gemini()
    if not client:
        raise RuntimeError("Gemini API key not configured")

    prompt_parts = []
    for message in messages:
        role = message["role"]
        content = message["content"]
        if role == "system":
            prompt_parts.append(f"Instructions:\n{content}")
        else:
            prompt_parts.append(content)

    full_prompt = "\n\n".join(prompt_parts)

    from google.genai import types

    response = client.models.generate_content(
        model=model,
        contents=full_prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        ),
    )
    return getattr(response, "text", "") or ""


def call_llm(
    prompt: str,
    system_prompt: str = "",
    task: str = "primary",
    max_tokens: int = 500,
    temperature: float = 0.2,
    max_retries: int = 2,
) -> str:
    """
    Call the best available LLM with automatic fallback.
    """
    from config import GEMINI_API_KEY, GROQ_API_KEY, HF_TOKEN, LLM_MODELS, LLM_PRIORITY

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    providers = []
    for provider_name in LLM_PRIORITY:
        if provider_name == "gemini" and GEMINI_API_KEY:
            model = LLM_MODELS["gemini"].get(task, LLM_MODELS["gemini"]["primary"])
            providers.append(("gemini", model, _call_gemini))
        elif provider_name == "groq" and GROQ_API_KEY:
            model = LLM_MODELS["groq"].get(task, LLM_MODELS["groq"]["primary"])
            providers.append(("groq", model, _call_groq))
        elif provider_name == "huggingface" and HF_TOKEN:
            model = LLM_MODELS["huggingface"].get(task, LLM_MODELS["huggingface"]["primary"])
            providers.append(("huggingface", model, _call_hf))

    if not providers:
        return (
            "Error: No LLM API keys configured. Set GEMINI_API_KEY, "
            "GROQ_API_KEY, or HUGGINGFACE_API_TOKEN in backend/.env"
        )

    last_error = None
    for provider_name, model, call_fn in providers:
        for attempt in range(max_retries):
            try:
                result = call_fn(model, messages, max_tokens, temperature)
                if result:
                    logger.info("LLM call succeeded via %s/%s", provider_name, model)
                    return result
            except Exception as exc:
                last_error = exc
                logger.warning("%s/%s attempt %s failed: %s", provider_name, model, attempt + 1, exc)
                if "rate_limit" in str(exc).lower() or "429" in str(exc):
                    time.sleep(2**attempt)
                continue
        logger.warning("All retries exhausted for %s/%s", provider_name, model)

    return f"Error: All LLM providers failed. Last error: {last_error}"


def call_gemini_only(
    prompt: str,
    system_prompt: str = "",
    task: str = "primary",
    max_tokens: int = 500,
    temperature: float = 0.2,
) -> str:
    """
    Force a Gemini-only text generation call.
    Useful for UI surfaces that should stay on a single provider.
    """
    from config import GEMINI_API_KEY, LLM_MODELS

    if not GEMINI_API_KEY:
        return "Error: Gemini API key not configured."

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    model = LLM_MODELS["gemini"].get(task, LLM_MODELS["gemini"]["primary"])
    try:
        result = _call_gemini(model, messages, max_tokens, temperature)
        if result:
            logger.info("LLM call succeeded via gemini-only/%s", model)
            return result
        return "No response from Gemini."
    except Exception as exc:
        logger.warning("gemini-only/%s failed: %s", model, exc)
        return f"Error: Gemini request failed. {exc}"

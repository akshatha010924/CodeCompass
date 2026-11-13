"""LLM access for local Ollama or optional Anthropic API usage."""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import config


def available() -> bool:
    """Return whether an LLM provider is configured.

    For Ollama, the actual connection is checked during generate(); this avoids
    making an extra network request for every chat message.
    """
    if config.LLM_PROVIDER == "ollama":
        return True
    if config.LLM_PROVIDER == "anthropic":
        return bool(config.ANTHROPIC_API_KEY)
    return False


def _generate_ollama(system: str, messages: list[dict], max_tokens: int) -> str:
    ollama_messages = [{"role": "system", "content": system}]
    for message in messages:
        role = message.get("role", "user")
        if role not in {"system", "user", "assistant"}:
            continue
        content = message.get("content", "")
        if isinstance(content, str) and content.strip():
            ollama_messages.append({"role": role, "content": content})

    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": ollama_messages,
        "stream": False,
        "options": {"num_predict": max_tokens},
    }
    request = Request(
        f"{config.OLLAMA_BASE_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=config.OLLAMA_TIMEOUT) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama returned HTTP {exc.code}: {details[:500]}") from exc
    except URLError as exc:
        raise RuntimeError(
            "Cannot connect to Ollama. Make sure the Ollama app/server is running."
        ) from exc

    answer = result.get("message", {}).get("content", "").strip()
    if not answer:
        raise RuntimeError("Ollama returned an empty response.")
    return answer


def generate(system: str, messages: list[dict], max_tokens: int = 1200) -> str:
    if config.LLM_PROVIDER == "ollama":
        return _generate_ollama(system, messages, max_tokens)

    if config.LLM_PROVIDER == "anthropic":
        if not config.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured.")
        import anthropic

        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=config.LLM_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        return "".join(block.text for block in response.content if block.type == "text")

    raise RuntimeError(
        f"Unsupported LLM_PROVIDER '{config.LLM_PROVIDER}'. Use 'ollama' or 'anthropic'."
    )

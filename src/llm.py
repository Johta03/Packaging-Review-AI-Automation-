"""LLM client wrapper: OpenAI, Groq (free tier), or Ollama (local, free)."""
import json
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Load .env from project root (parent of src/) so it works when run as python -m src.run
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")

# Provider: openai (default), groq (free tier), ollama (local, free)
GROQ_BASE = "https://api.groq.com/openai/v1"
OLLAMA_BASE = "http://localhost:11434/v1"


def get_client() -> OpenAI:
    """Return OpenAI-compatible client based on LLM_PROVIDER in .env."""
    provider = (os.getenv("LLM_PROVIDER") or "openai").strip().lower()

    if provider == "groq":
        key = os.getenv("GROQ_API_KEY")
        if not key or key.startswith("gsk_REPLACE"):
            raise ValueError(
                "Groq API key not set. Set LLM_PROVIDER=groq and GROQ_API_KEY=your-key in .env. "
                "Get a free key at https://console.groq.com/"
            )
        return OpenAI(api_key=key, base_url=GROQ_BASE)

    if provider == "ollama":
        # Ollama has no auth; use a placeholder key. Ensure Ollama is running: ollama run llama3.2
        return OpenAI(api_key="ollama", base_url=OLLAMA_BASE)

    # default: openai
    key = os.getenv("OPENAI_API_KEY")
    if not key or key.startswith("sk-REPLACE"):
        raise ValueError(
            "OpenAI API key not set. Create .env and set OPENAI_API_KEY=your-key, "
            "or use a free option: LLM_PROVIDER=groq + GROQ_API_KEY (get at https://console.groq.com/) "
            "or LLM_PROVIDER=ollama (run 'ollama run llama3.2' first)."
        )
    return OpenAI(api_key=key)


def get_model() -> str:
    """Return model name from env or default for current provider."""
    provider = (os.getenv("LLM_PROVIDER") or "openai").strip().lower()
    if provider == "groq":
        return os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    if provider == "ollama":
        return os.getenv("OLLAMA_MODEL", "llama3.2")
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def complete(system: str, user: str, model: str | None = None) -> str:
    """
    Single completion. Returns the assistant message content.
    """
    client = get_client()
    model = model or get_model()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    msg = resp.choices[0].message
    return msg.content or ""


def extract_json_from_response(text: str) -> dict:
    """
    Try to find a JSON object in the response (between ```json ... ``` or raw).
    Returns the parsed dict or raises ValueError.
    """
    text = text.strip()
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        text = text[start:end].strip()
    return json.loads(text)

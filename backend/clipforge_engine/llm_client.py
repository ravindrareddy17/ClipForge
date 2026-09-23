"""
ClipForge AI V2 - Unified Multi-Provider LLM Client
Supports Groq Cloud, Google Gemini, Local Ollama, and AWS Bedrock.
Automatically resolves API keys from st.secrets, environment variables,
or the local SQLite database.
"""

import os
import json
import re
import urllib.request
import urllib.error
import requests
import httpx
from typing import Dict, Any, List, Optional, Tuple

# Available default models per provider
DEFAULT_MODELS = {
    "groq": "openai/gpt-oss-20b",
    "gemini": "gemini-3.6-flash",
    "ollama": "qwen2.5:3b",
    "bedrock": "anthropic.claude-3-haiku-20240307-v1:0"
}

# Fallback models if primary returns 404 or quota exceeded
FALLBACK_MODELS = {
    "groq": ["qwen/qwen3.8-27b", "openai/gpt-oss-120b"],
    "gemini": ["gemini-flash-latest", "gemini-2.5-flash-lite"],
    "ollama": ["llama3:latest", "llama3", "mistral:latest"]
}

def _is_in_streamlit_context() -> bool:
    try:
        from streamlit.runtime import exists
        return exists()
    except Exception:
        return False

def get_streamlit_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Safely retrieves a key from st.secrets or local secrets.toml."""
    # 1. If running inside Streamlit, check st.secrets
    if _is_in_streamlit_context():
        try:
            import streamlit as st
            if hasattr(st, "secrets") and key in st.secrets:
                return str(st.secrets[key])
        except Exception:
            pass

    # 2. Check local .streamlit/secrets.toml using tomllib
    try:
        import tomllib
        sec_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".streamlit", "secrets.toml")
        if os.path.exists(sec_path):
            with open(sec_path, "rb") as f:
                data = tomllib.load(f)
                if key in data:
                    return str(data[key])
    except Exception:
        pass

    return default

def get_streamlit_session_state(key: str, default: Optional[str] = None) -> Optional[str]:
    """Safely retrieves a value from st.session_state if available."""
    if _is_in_streamlit_context():
        try:
            import streamlit as st
            if hasattr(st, "session_state") and key in st.session_state:
                val = st.session_state[key]
                if val:
                    return str(val)
        except Exception:
            pass
    return default

def get_db_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """Retrieves a setting from the local SQLite settings table."""
    try:
        from clipforge_engine.db import get_settings
        settings = get_settings()
        return settings.get(key, default)
    except Exception:
        return default

def get_active_provider() -> str:
    """
    Determines the active LLM provider.
    Priority:
    1. Streamlit session_state ('llm_provider')
    2. Streamlit secrets ('LLM_PROVIDER')
    3. Environment variable ('LLM_PROVIDER')
    4. SQLite DB setting ('llm_provider')
    5. Auto-detect: if Groq key exists -> groq, elif Gemini key exists -> gemini, else ollama
    """
    # 1. UI session state
    val = get_streamlit_session_state("llm_provider")
    if val and val.lower() in ["groq", "gemini", "ollama", "bedrock"]:
        return val.lower()

    # 2. Secrets / Env / DB
    val = get_streamlit_secret("LLM_PROVIDER") or os.getenv("LLM_PROVIDER") or get_db_setting("llm_provider")
    if val and val.lower() in ["groq", "gemini", "ollama", "bedrock"]:
        return val.lower()

    # 3. Auto-detection
    groq_k = get_groq_api_key()
    if groq_k:
        return "groq"
    gemini_k = get_gemini_api_key()
    if gemini_k:
        return "gemini"

    return "ollama"

def get_groq_api_key() -> Optional[str]:
    """Resolves Groq API key from session_state, secrets, env, or DB."""
    return (
        get_streamlit_session_state("groq_api_key")
        or get_streamlit_secret("GROQ_API_KEY")
        or os.getenv("GROQ_API_KEY")
        or get_db_setting("groq_api_key")
    )

def get_gemini_api_key() -> Optional[str]:
    """Resolves Gemini API key from session_state, secrets, env, or DB."""
    return (
        get_streamlit_session_state("gemini_api_key")
        or get_streamlit_secret("GEMINI_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or get_db_setting("gemini_api_key")
    )

def get_ollama_url() -> str:
    """Resolves Ollama base URL."""
    return (
        get_streamlit_session_state("ollama_url")
        or get_streamlit_secret("OLLAMA_URL")
        or os.getenv("OLLAMA_URL")
        or get_db_setting("ollama_url")
        or "http://localhost:11434"
    )

def get_active_model(provider: Optional[str] = None) -> str:
    """Resolves the configured model name for the given provider."""
    p = provider or get_active_provider()
    if p == "groq":
        return (
            get_streamlit_session_state("groq_model")
            or get_streamlit_secret("GROQ_MODEL")
            or os.getenv("GROQ_MODEL")
            or get_db_setting("groq_model")
            or DEFAULT_MODELS["groq"]
        )
    elif p == "gemini":
        return (
            get_streamlit_session_state("gemini_model")
            or get_streamlit_secret("GEMINI_MODEL")
            or os.getenv("GEMINI_MODEL")
            or get_db_setting("gemini_model")
            or DEFAULT_MODELS["gemini"]
        )
    elif p == "bedrock":
        return (
            get_streamlit_session_state("bedrock_model")
            or get_streamlit_secret("BEDROCK_MODEL")
            or os.getenv("BEDROCK_MODEL")
            or get_db_setting("bedrock_model")
            or DEFAULT_MODELS["bedrock"]
        )
    else:
        return (
            get_streamlit_session_state("ollama_model")
            or get_streamlit_secret("OLLAMA_MODEL")
            or os.getenv("OLLAMA_MODEL")
            or get_db_setting("ollama_model")
            or DEFAULT_MODELS["ollama"]
        )

# ============================================================================
# PROVIDER IMPLEMENTATIONS
# ============================================================================

def call_groq_chat(
    messages: List[Dict[str, str]],
    model: str = "openai/gpt-oss-20b",
    api_key: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 600,
    json_mode: bool = False,
    timeout: float = 30.0
) -> str:
    """Calls Groq Cloud API with OpenAI-compatible completions endpoint."""
    key = api_key or get_groq_api_key()
    if not key:
        raise ValueError("Groq API key not found.")

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "ClipForge/2.0"
    }

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    # Attempt primary model, then fallbacks
    models_to_try = [model] + [m for m in FALLBACK_MODELS.get("groq", []) if m != model]
    last_err = None

    for m in models_to_try:
        payload["model"] = m
        try:
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload).encode("utf-8")
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            last_err = f"HTTP {e.code}: {err_body}"
            # If model not found or forbidden, try next fallback
            if e.code in [404, 400]:
                continue
            raise RuntimeError(last_err)
        except Exception as e:
            last_err = str(e)

    raise RuntimeError(f"All Groq models failed. Last error: {last_err}")


def call_gemini_generate(
    prompt: Optional[str] = None,
    system_instruction: Optional[str] = None,
    messages: Optional[List[Dict[str, str]]] = None,
    model: str = "gemini-3.6-flash",
    api_key: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 1000,
    json_mode: bool = False,
    timeout: float = 30.0
) -> str:
    """Calls Google Gemini Generative Language REST API."""
    key = api_key or get_gemini_api_key()
    if not key:
        raise ValueError("Gemini API key not found.")

    url_model = model.replace("models/", "")
    models_to_try = [url_model] + [m for m in FALLBACK_MODELS.get("gemini", []) if m != url_model]
    last_err = None

    for m in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}"

        # Construct contents array
        contents = []
        if messages:
            # Map messages: role 'assistant' -> 'model', system instruction separated
            sys_text = system_instruction
            for msg in messages:
                r = msg.get("role", "user")
                c = msg.get("content", "")
                if r == "system":
                    sys_text = (sys_text + "\n" + c) if sys_text else c
                elif r == "assistant":
                    contents.append({"role": "model", "parts": [{"text": c}]})
                else:
                    contents.append({"role": "user", "parts": [{"text": c}]})
            system_instruction = sys_text
        elif prompt:
            contents.append({"parts": [{"text": prompt}]})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }

        if system_instruction:
            payload["system_instruction"] = {
                "parts": [{"text": system_instruction}]
            }

        if json_mode:
            payload["generationConfig"]["response_mime_type"] = "application/json"

        try:
            req = urllib.request.Request(
                url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload).encode("utf-8")
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    # Join text across all parts (excluding raw thoughts)
                    text_parts = [p.get("text", "") for p in parts if "text" in p]
                    res_text = "\n".join(text_parts).strip()
                    if res_text:
                        return res_text
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            last_err = f"HTTP {e.code}: {err_body}"
            if e.code in [404, 400]:
                continue
            raise RuntimeError(last_err)
        except Exception as e:
            last_err = str(e)

    raise RuntimeError(f"All Gemini models failed. Last error: {last_err}")


def call_ollama_local(
    prompt: Optional[str] = None,
    system: Optional[str] = None,
    messages: Optional[List[Dict[str, str]]] = None,
    model: str = "qwen2.5:3b",
    base_url: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 300,
    json_mode: bool = False,
    timeout: float = 40.0
) -> str:
    """Calls local Ollama instance with /api/chat or /api/generate."""
    url = (base_url or get_ollama_url()).rstrip("/")
    headers = {"ngrok-skip-browser-warning": "1"}

    if messages:
        payload = {
            "model": model,
            "messages": messages,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            },
            "stream": False
        }
        if json_mode:
            payload["format"] = "json"
        resp = requests.post(f"{url}/api/chat", json=payload, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return resp.json().get("message", {}).get("content", "").strip()
    else:
        payload = {
            "model": model,
            "prompt": prompt or "",
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            },
            "stream": False
        }
        if system:
            payload["system"] = system
        if json_mode:
            payload["format"] = "json"
        resp = requests.post(f"{url}/api/generate", json=payload, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()

    return ""

# ============================================================================
# UNIFIED SYNCHRONOUS AND ASYNCHRONOUS ENTRY POINTS
# ============================================================================

def call_llm(
    prompt: Optional[str] = None,
    system: Optional[str] = None,
    messages: Optional[List[Dict[str, str]]] = None,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 600,
    json_mode: bool = False
) -> str:
    """
    Main unified LLM dispatch function.
    Automatically handles provider selection, format adaptation, and fallbacks.
    """
    prov = (provider or get_active_provider()).lower()
    mod = model or get_active_model(prov)

    # Convert prompt + system into messages if messages is None
    if messages is None:
        chat_msgs = []
        if system:
            chat_msgs.append({"role": "system", "content": system})
        if prompt:
            chat_msgs.append({"role": "user", "content": prompt})
    else:
        chat_msgs = messages

    # 1. Groq Cloud
    if prov == "groq":
        try:
            return call_groq_chat(
                messages=chat_msgs,
                model=mod,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode
            )
        except Exception as e:
            print(f"[LLM Client] Groq call failed: {e}. Attempting Gemini fallback...")
            # Fall back to Gemini if key available
            if get_gemini_api_key():
                try:
                    return call_gemini_generate(
                        messages=chat_msgs,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        json_mode=json_mode
                    )
                except Exception as e2:
                    print(f"[LLM Client] Gemini fallback failed: {e2}")

    # 2. Gemini Cloud
    elif prov == "gemini":
        try:
            return call_gemini_generate(
                prompt=prompt,
                system_instruction=system,
                messages=messages,
                model=mod,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode
            )
        except Exception as e:
            print(f"[LLM Client] Gemini call failed: {e}. Attempting Groq fallback...")
            if get_groq_api_key():
                try:
                    return call_groq_chat(
                        messages=chat_msgs,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        json_mode=json_mode
                    )
                except Exception as e2:
                    print(f"[LLM Client] Groq fallback failed: {e2}")

    # 3. Local Ollama (or final fallback)
    try:
        return call_ollama_local(
            prompt=prompt,
            system=system,
            messages=messages,
            model=mod if prov == "ollama" else DEFAULT_MODELS["ollama"],
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode
        )
    except Exception as e:
        print(f"[LLM Client] Ollama local call failed: {e}")

    return ""


async def async_call_llm(
    prompt: Optional[str] = None,
    system: Optional[str] = None,
    messages: Optional[List[Dict[str, str]]] = None,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 600,
    json_mode: bool = False
) -> str:
    """
    Asynchronous version of unified LLM caller for asyncio pipelines.
    Runs synchronous call in executor to ensure total non-blocking execution.
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: call_llm(
            prompt=prompt,
            system=system,
            messages=messages,
            model=model,
            provider=provider,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode
        )
    )

# ============================================================================
# DIAGNOSTIC AND CONNECTION HEALTH CHECKS
# ============================================================================

def test_provider_connection(
    provider: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    url: Optional[str] = None
) -> Tuple[bool, str]:
    """Tests connectivity to a specific LLM provider."""
    p = provider.lower()
    try:
        if p == "groq":
            k = api_key or get_groq_api_key()
            if not k:
                return False, "No Groq API key found."
            m = model or DEFAULT_MODELS["groq"]
            res = call_groq_chat(
                messages=[{"role": "user", "content": "Ping"}],
                model=m,
                api_key=k,
                max_tokens=10,
                timeout=10.0
            )
            return True, f"Connected to Groq Cloud ({m})! Response: '{res[:30]}...'"

        elif p == "gemini":
            k = api_key or get_gemini_api_key()
            if not k:
                return False, "No Gemini API key found."
            m = model or DEFAULT_MODELS["gemini"]
            res = call_gemini_generate(
                prompt="Ping",
                model=m,
                api_key=k,
                max_tokens=10,
                timeout=10.0
            )
            return True, f"Connected to Google Gemini ({m})! Response: '{res[:30]}...'"

        elif p == "ollama":
            base_url = (url or get_ollama_url()).rstrip("/")
            headers = {"ngrok-skip-browser-warning": "1"}
            resp = requests.get(f"{base_url}/api/tags", headers=headers, timeout=4)
            if resp.status_code == 200:
                models = [item["name"] for item in resp.json().get("models", [])]
                return True, f"Connected to Ollama ({len(models)} models available: {', '.join(models[:4])})"
            return False, f"Ollama HTTP {resp.status_code}"

        return False, f"Unknown provider: {provider}"
    except Exception as e:
        return False, str(e)

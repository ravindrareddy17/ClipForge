"""
LLM Provider adapters using standard HTTP requests.
Supports Groq, Gemini, Ollama, OpenAI, and an explicit Mock provider.
Enforces strict error typing without silent fallback to synthetic answers.
"""

import os
import re
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import requests

from .exceptions import (
    LLMProviderError,
    AuthenticationError,
    RateLimitError,
    ProviderTimeoutError,
    NetworkError,
    InvalidRequestError
)

from pathlib import Path

logger = logging.getLogger("video_transcript_temporal_rag.llm")


def mask_key(key: Optional[str]) -> str:
    if not key or len(key) < 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"


def resolve_api_key(var_name: str) -> Optional[str]:
    """Resolves an API key from environment, .env file, or .streamlit/secrets.toml safely."""
    val = os.getenv(var_name)
    if val and val.strip():
        return val.strip()

    search_dirs = [Path.cwd(), Path(__file__).resolve().parent.parent.parent.parent]
    for d in search_dirs:
        env_f = d / ".env"
        if env_f.is_file():
            try:
                for line in env_f.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith(f"{var_name}="):
                        v = line.split("=", 1)[1].strip().strip("'\"")
                        if v:
                            return v
            except Exception:
                pass

        sec_f = d / ".streamlit" / "secrets.toml"
        if sec_f.is_file():
            try:
                import tomllib
                with open(sec_f, "rb") as f:
                    data = tomllib.load(f)
                    if var_name in data and data[var_name]:
                        return str(data[var_name]).strip()
            except Exception:
                pass
    return None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "", max_tokens: int = 1500, temperature: float = 0.2) -> str:
        pass


class GroqProvider(BaseLLMProvider):
    """Groq Cloud API provider."""

    def __init__(self, api_key: Optional[str] = None, model: str = "openai/gpt-oss-20b", timeout: int = 45):
        self.api_key = api_key if api_key is not None else resolve_api_key("GROQ_API_KEY")
        self.model = model
        self.timeout = timeout
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.last_usage: Dict[str, Any] = {}

    def generate(self, prompt: str, system_prompt: str = "", max_tokens: int = 2000, temperature: float = 0.2) -> str:
        if not self.api_key:
            raise AuthenticationError("GROQ_API_KEY is not configured.", provider="groq")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        try:
            resp = requests.post(self.endpoint, headers=headers, json=payload, timeout=self.timeout)
            if resp.status_code in (401, 403):
                raise AuthenticationError(f"Groq authentication failed: {resp.text}", provider="groq", status_code=resp.status_code)
            elif resp.status_code == 429:
                raise RateLimitError(f"Groq rate limit or quota exceeded: {resp.text}", provider="groq", status_code=429)
            elif resp.status_code == 400:
                raise InvalidRequestError(f"Groq invalid request: {resp.text}", provider="groq", status_code=400)
            resp.raise_for_status()
            data = resp.json()
            self.last_usage = data.get("usage", {})
        except requests.exceptions.Timeout as e:
            raise ProviderTimeoutError(f"Groq request timed out after {self.timeout}s: {e}", provider="groq")
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(f"Groq connection failed: {e}", provider="groq")
        except (AuthenticationError, RateLimitError, InvalidRequestError):
            raise
        except requests.exceptions.HTTPError as e:
            raise LLMProviderError(f"Groq HTTP error: {e}", provider="groq", status_code=resp.status_code if 'resp' in locals() else None)

        choices = data.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            content = msg.get("content", "")
            if not content and "reasoning" in msg:
                content = msg.get("reasoning", "")
            return content.strip()

        return ""


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API provider."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash", timeout: int = 45):
        self.api_key = api_key if api_key is not None else resolve_api_key("GEMINI_API_KEY")
        self.model = model
        self.timeout = timeout
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    def generate(self, prompt: str, system_prompt: str = "", max_tokens: int = 1500, temperature: float = 0.2) -> str:
        if not self.api_key:
            raise AuthenticationError("GEMINI_API_KEY is not configured.", provider="gemini")

        url = f"{self.endpoint}?key={self.api_key}"
        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"System Instructions: {system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will strictly adhere to these instructions."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature
            }
        }

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            if resp.status_code in (401, 403):
                raise AuthenticationError(f"Gemini authentication failed: {resp.text}", provider="gemini", status_code=resp.status_code)
            elif resp.status_code == 429:
                raise RateLimitError(f"Gemini rate limit or quota exceeded: {resp.text}", provider="gemini", status_code=429)
            elif resp.status_code == 400:
                raise InvalidRequestError(f"Gemini invalid request: {resp.text}", provider="gemini", status_code=400)
            resp.raise_for_status()
            data = resp.json()
            self.last_usage = data.get("usage", {})
        except requests.exceptions.Timeout as e:
            raise ProviderTimeoutError(f"Gemini request timed out after {self.timeout}s: {e}", provider="gemini")
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(f"Gemini connection failed: {e}", provider="gemini")
        except (AuthenticationError, RateLimitError, InvalidRequestError):
            raise
        except requests.exceptions.HTTPError as e:
            raise LLMProviderError(f"Gemini HTTP error: {e}", provider="gemini", status_code=resp.status_code if 'resp' in locals() else None)

        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "").strip()

        return ""


class OllamaProvider(BaseLLMProvider):
    """Local Ollama provider."""

    def __init__(self, host: str = "http://localhost:11434", model: str = "qwen2.5:3b", timeout: int = 60):
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.endpoint = f"{self.host}/api/chat"

    def generate(self, prompt: str, system_prompt: str = "", max_tokens: int = 1500, temperature: float = 0.2) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        try:
            resp = requests.post(self.endpoint, json=payload, timeout=self.timeout)
            if resp.status_code == 404:
                raise InvalidRequestError(f"Model '{self.model}' not found in local Ollama daemon.", provider="ollama", status_code=404)
            resp.raise_for_status()
            data = resp.json()
            self.last_usage = data.get("usage", {})
            return data.get("message", {}).get("content", "").strip()
        except requests.exceptions.Timeout as e:
            raise ProviderTimeoutError(f"Ollama request timed out after {self.timeout}s: {e}", provider="ollama")
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(f"Cannot connect to local Ollama daemon at {self.host}. Is Ollama running?: {e}", provider="ollama")
        except InvalidRequestError:
            raise
        except requests.exceptions.HTTPError as e:
            raise LLMProviderError(f"Ollama HTTP error: {e}", provider="ollama", status_code=resp.status_code if 'resp' in locals() else None)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini", timeout: int = 45):
        self.api_key = api_key if api_key is not None else resolve_api_key("OPENAI_API_KEY")
        self.model = model
        self.timeout = timeout
        self.endpoint = "https://api.openai.com/v1/chat/completions"

    def generate(self, prompt: str, system_prompt: str = "", max_tokens: int = 1500, temperature: float = 0.2) -> str:
        if not self.api_key:
            raise AuthenticationError("OPENAI_API_KEY is not configured.", provider="openai")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        try:
            resp = requests.post(self.endpoint, headers=headers, json=payload, timeout=self.timeout)
            if resp.status_code in (401, 403):
                raise AuthenticationError(f"OpenAI authentication failed: {resp.text}", provider="openai", status_code=resp.status_code)
            elif resp.status_code == 429:
                raise RateLimitError(f"OpenAI rate limit or quota exceeded: {resp.text}", provider="openai", status_code=429)
            elif resp.status_code == 400:
                raise InvalidRequestError(f"OpenAI invalid request: {resp.text}", provider="openai", status_code=400)
            resp.raise_for_status()
            data = resp.json()
            self.last_usage = data.get("usage", {})
        except requests.exceptions.Timeout as e:
            raise ProviderTimeoutError(f"OpenAI request timed out after {self.timeout}s: {e}", provider="openai")
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(f"OpenAI connection failed: {e}", provider="openai")
        except (AuthenticationError, RateLimitError, InvalidRequestError):
            raise
        except requests.exceptions.HTTPError as e:
            raise LLMProviderError(f"OpenAI HTTP error: {e}", provider="openai", status_code=resp.status_code if 'resp' in locals() else None)

        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "").strip()
        return ""


class MockProvider(BaseLLMProvider):
    """
    Deterministic rule-based mock provider for testing.
    Can ONLY be invoked when explicitly configured.
    Grounds synthesized mock answers in timestamps from prompt evidence when available.
    """

    def generate(self, prompt: str, system_prompt: str = "", max_tokens: int = 1500, temperature: float = 0.2) -> str:
        prompt_lower = prompt.lower()

        # Extract timestamps and chunk texts from transcript evidence in prompt if present
        evidence_match = re.search(r"<transcript_evidence>(.*?)</transcript_evidence>", prompt, re.DOTALL)
        extracted_ts = []
        best_ts = None
        if evidence_match:
            extracted_ts = re.findall(r"\[\d{1,2}:\d{2}(?:[–-]\d{1,2}:\d{2})?\]", evidence_match.group(1))

            # Identify most relevant timestamp based on query tokens
            q_match = re.search(r"USER (?:QUESTION|REQUEST):\s*(.*?)(?:\n\n|\nINSTRUCTIONS)", prompt, re.DOTALL)
            if q_match:
                q_tokens = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", q_match.group(1).lower())]
                items = re.findall(r"(\[\d{1,2}:\d{2}(?:[–-]\d{1,2}:\d{2})?\])\s*([^\[]+)", evidence_match.group(1))
                best_score = -1
                for ts, text in items:
                    score = sum(1 for t in q_tokens if t in text.lower())
                    if score > best_score:
                        best_score = score
                        best_ts = ts

        if "summary" in prompt_lower or "overview" in prompt_lower or "main points" in prompt_lower:
            ts1 = extracted_ts[0] if len(extracted_ts) > 0 else "[00:00–01:15]"
            ts2 = extracted_ts[1] if len(extracted_ts) > 1 else "[01:30–02:45]"
            ts3 = extracted_ts[2] if len(extracted_ts) > 2 else "[03:00–04:15]"
            ts_end = extracted_ts[-1] if extracted_ts else "[04:15]"
            return (
                "This video provides an overview of the topic discussed across the timeline.\n\n"
                "**Main Points:**\n"
                f"1. Initial introduction and framing of the core subject {ts1}.\n"
                f"2. Key development and analysis of the main arguments {ts2}.\n"
                f"3. Concluding perspectives and closing summary {ts3}.\n\n"
                "**Conclusion:**\n"
                f"The video concludes with final reflections grounded in the discussed events {ts_end}."
            )

        active_ts = best_ts or (extracted_ts[0] if extracted_ts else "[01:20–02:05]")
        return (
            f"Based on the transcript evidence, the speaker discussed this key concept at length {active_ts}. "
            "The explanation highlights specific details directly addressed in the video."
        )

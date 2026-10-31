"""
Multi-provider LLM client with strict error propagation and optional real failover.
Disables silent synthetic mock fallbacks by default.
"""

import os
import logging
from typing import Optional, Dict, Any, List, Tuple

from .exceptions import (
    LLMProviderError,
    AuthenticationError,
    RateLimitError,
    ProviderTimeoutError,
    NetworkError
)
from .providers import (
    BaseLLMProvider,
    GroqProvider,
    GeminiProvider,
    OllamaProvider,
    OpenAIProvider,
    MockProvider,
    mask_key
)

logger = logging.getLogger("video_transcript_temporal_rag.llm")


class LLMClient:
    """Manages LLM provider execution, real multi-provider failover, and strict error reporting."""

    def __init__(
        self,
        provider: str = "groq",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        fallback_enabled: bool = True,
        allow_mock: bool = False
    ):
        self.provider_name = provider.lower()
        self.model = model
        self.api_key = api_key
        self.fallback_enabled = fallback_enabled
        self.allow_mock = allow_mock

        # Validate mock authorization upfront
        if self.provider_name == "mock" and not self.allow_mock:
            raise AuthenticationError(
                "MockProvider is disabled by default for commercial integrity. "
                "Set allow_mock=True or configure a genuine provider (groq, gemini, ollama, openai).",
                provider="mock"
            )

        self.active_provider: Optional[BaseLLMProvider] = None
        self.primary_provider = self._create_provider(self.provider_name, self.model, self.api_key)

    def get_last_usage(self) -> Dict[str, Any]:
        """Returns the token usage dictionary from the most recent LLM call if available."""
        prov = self.active_provider or self.primary_provider
        return getattr(prov, "last_usage", {})

    def _create_provider(self, name: str, model: Optional[str] = None, api_key: Optional[str] = None) -> BaseLLMProvider:
        name = name.lower()
        if name == "groq":
            return GroqProvider(api_key=api_key, model=model or "openai/gpt-oss-20b")
        elif name == "gemini":
            return GeminiProvider(api_key=api_key, model=model or "gemini-2.5-flash")
        elif name == "ollama":
            return OllamaProvider(model=model or "qwen2.5:3b")
        elif name == "openai":
            return OpenAIProvider(api_key=api_key, model=model or "gpt-4o-mini")
        elif name == "mock":
            if not self.allow_mock:
                raise AuthenticationError("MockProvider is unauthorized. Explicit allow_mock=True required.", provider="mock")
            return MockProvider()
        else:
            raise AuthenticationError(f"Unsupported LLM provider '{name}'. Supported: groq, gemini, ollama, openai, mock", provider=name)

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 1500,
        temperature: float = 0.2
    ) -> str:
        """
        Attempts generation with primary provider.
        Cascades ONLY to other legitimately configured real providers.
        NEVER silently falls back to MockProvider unless allow_mock is True.
        """
        provider_errors: List[str] = []

        try:
            res = self.primary_provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            self.active_provider = self.primary_provider
            return res
        except Exception as e:
            err_msg = f"{self.provider_name}: {e}"
            logger.warning(f"Primary provider failed: {err_msg}")
            provider_errors.append(err_msg)

            if not self.fallback_enabled:
                raise e

            # Build list of real configured candidates
            fallback_candidates: List[Tuple[str, BaseLLMProvider]] = []

            if self.provider_name != "groq" and os.getenv("GROQ_API_KEY"):
                fallback_candidates.append(("groq", GroqProvider()))
            if self.provider_name != "gemini" and os.getenv("GEMINI_API_KEY"):
                fallback_candidates.append(("gemini", GeminiProvider()))
            if self.provider_name != "openai" and os.getenv("OPENAI_API_KEY"):
                fallback_candidates.append(("openai", OpenAIProvider()))

            # Only add mock if explicitly allowed
            if self.allow_mock:
                fallback_candidates.append(("mock", MockProvider()))

            for fb_name, fb_inst in fallback_candidates:
                try:
                    logger.info(f"Attempting configured fallback provider: {fb_name}")
                    res = fb_inst.generate(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                    self.active_provider = fb_inst
                    return res
                except Exception as fb_err:
                    err_detail = f"{fb_name}: {fb_err}"
                    logger.warning(f"Fallback candidate failed: {err_detail}")
                    provider_errors.append(err_detail)

            # If all fail, raise transparent composite error
            composite_msg = " | ".join(provider_errors)
            raise LLMProviderError(f"All attempted providers failed. Errors: {composite_msg}", provider="composite")

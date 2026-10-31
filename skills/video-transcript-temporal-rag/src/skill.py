"""
VideoIntelligenceSkill: Main public interface for the standalone skill.
Now hardened with file security sandboxing and transparent error handling.
"""

import json
from pathlib import Path
from typing import Union, Optional, Dict, Any, Callable, List

from .models import NormalizedTranscript, SkillResponse
from .normalizer import TranscriptNormalizer
from .storage import InMemoryTranscriptStore, BaseTranscriptStore
from .llm.client import LLMClient
from .llm.exceptions import LLMProviderError, AuthenticationError
from .agents.coordinator import ReActCoordinator
from .security import validate_and_read_transcript_file, SecurityError


class VideoIntelligenceSkill:
    """
    Commercial Video Intelligence Skill for Agensi.io.
    Provides evidence-grounded question answering and adaptive hierarchical summarization
    with exact timestamp citations via a 6-Agent ReAct architecture.
    """

    def __init__(
        self,
        provider: str = "groq",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        store: Optional[BaseTranscriptStore] = None,
        allow_mock: bool = False,
        allowed_directories: Optional[List[Union[str, Path]]] = None
    ):
        self.provider = provider
        # Only allow mock if explicitly requested or provider is 'mock' with allow_mock=True
        is_mock_requested = provider.lower() == "mock"
        self.allow_mock = allow_mock or is_mock_requested
        self.allowed_directories = allowed_directories

        self.store = store or InMemoryTranscriptStore()
        self.llm = LLMClient(
            provider=provider,
            model=model,
            api_key=api_key,
            allow_mock=self.allow_mock
        )
        self.coordinator = ReActCoordinator(store=self.store, llm_client=self.llm)
        self.current_video_id: str = "video_default"
        self.current_video_title: str = "Video"
        self.current_duration: float = 0.0

    def load_transcript(
        self,
        transcript_source: Union[str, dict, list, Path],
        video_id: Optional[str] = None,
        video_title: Optional[str] = None
    ) -> NormalizedTranscript:
        """
        Loads and indexes a transcript from an authorized file path, raw JSON dict/list, or string.
        Enforces safe directory sandboxing and file extension checks.
        """
        raw_data = transcript_source

        # If file path or string, run through security validator
        if isinstance(transcript_source, (str, Path)):
            raw_str = str(transcript_source).strip()
            # If not inline json/srt content, treat as file path
            if not ("\n" in raw_str or raw_str.startswith("{") or raw_str.startswith("[") or "-->" in raw_str):
                validated_content = validate_and_read_transcript_file(
                    transcript_source,
                    allowed_directories=self.allowed_directories
                )
                try:
                    raw_data = json.loads(validated_content)
                except Exception:
                    raw_data = validated_content

        vid = video_id or "video_default"
        title = video_title or "Video"

        normalized = TranscriptNormalizer.normalize(raw_data, video_id=vid, video_title=title)
        self.current_video_id = normalized.video_id
        self.current_video_title = normalized.title
        self.current_duration = normalized.duration

        self.store.load_transcript(normalized)
        return normalized

    def ask(
        self,
        query: str,
        video_id: Optional[str] = None,
        status_callback: Optional[Callable[[str], None]] = None
    ) -> SkillResponse:
        """
        Executes the 6-agent Video QA loop over the indexed transcript.
        """
        vid = video_id or self.current_video_id
        return self.coordinator.process(
            query=query,
            video_id=vid,
            video_title=self.current_video_title,
            duration=self.current_duration,
            status_callback=status_callback
        )

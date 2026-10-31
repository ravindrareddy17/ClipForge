"""
Base class for all Video QA specialized agents.
"""

from abc import ABC, abstractmethod
from typing import Any
from ..models import VideoQAState


class BaseAgent(ABC):
    """Abstract base class for specialized Video QA agents."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def run(self, state: VideoQAState) -> VideoQAState:
        """Executes the agent's logic, mutating and returning the VideoQAState."""
        pass

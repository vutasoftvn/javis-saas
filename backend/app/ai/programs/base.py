"""Abstract Base Class for AI Program Runtimes and COSA Programs."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel

from app.ai.programs.schemas import AIProgramRequest, AIProgramResult


class AIProgramRuntime(ABC):
    """Abstract interface for program execution runtimes."""

    @abstractmethod
    async def run(self, request: AIProgramRequest) -> AIProgramResult:
        """Execute the program with structured input and return normalized result."""
        pass


class BaseCOSAProgram(ABC):
    """Base interface for DSPy cognitive programs in COSA."""

    program_key: str = ""
    default_version: str = "1.0.0"
    input_schema: Optional[Type[BaseModel]] = None
    output_schema: Optional[Type[BaseModel]] = None

    @abstractmethod
    def forward(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute the forward reasoning pass."""
        pass

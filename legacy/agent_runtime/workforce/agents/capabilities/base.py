"""Base contracts and abstractions for Capability Providers in COSA OS.

Separates high-level Capabilities (what can be done) from underlying Providers (how it is done).
Implements the Tool Result Contract and Evidence verification requirements.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProviderHealthStatus(str, Enum):
    AVAILABLE = "available"
    MISSING = "missing"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DISABLED = "disabled"


class ProviderHealthResult(BaseModel):
    provider_id: str
    status: ProviderHealthStatus
    message: str = "Healthy"
    latency_ms: Optional[float] = None
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidenceObject(BaseModel):
    """Tamper-evident proof of state mutation or external execution."""
    action: str
    execution_id: str
    status: str = "success"
    provider: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resource_id: Optional[str] = None
    data_hash: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class CapabilityRequest(BaseModel):
    capability: str
    action: str
    workspace_id: Optional[int] = None
    company_id: Optional[int] = None
    user_id: Optional[int] = None
    agent_key: str = "general"
    execution_mode: str = "INTERACTIVE"  # INTERACTIVE, APPROVED_WORKFLOW, AUTONOMOUS_SAFE
    payload: Dict[str, Any] = Field(default_factory=dict)
    execution_id: Optional[str] = None


class CapabilityResult(BaseModel):
    """Standard Tool / Capability Result Contract."""
    ok: bool
    provider: str
    capability: str
    execution_id: str
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    evidence: Optional[EvidenceObject] = None
    duration_ms: Optional[int] = None


class CapabilityProvider(ABC):
    """Abstract interface that every capability provider adapter must implement."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier of the provider (e.g. 'native_cosa', 'claude_code', 'openclaw')."""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """Provider priority for resolution (lower number = higher priority)."""
        pass

    @abstractmethod
    async def health(self) -> ProviderHealthResult:
        """Check provider health and readiness."""
        pass

    @abstractmethod
    async def capabilities(self) -> List[str]:
        """List capability IDs provided by this adapter."""
        pass

    @abstractmethod
    async def execute(self, request: CapabilityRequest) -> CapabilityResult:
        """Execute capability request and return standardized result with evidence."""
        pass

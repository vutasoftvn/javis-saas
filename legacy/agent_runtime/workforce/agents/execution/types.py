from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    QUEUED = "queued"
    PREPARING = "preparing"
    RUNNING = "running"
    COLLECTING = "collecting"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    AWAITING_APPROVAL = "awaiting_approval"
    CANCELLED = "cancelled"
    DESTROYED = "destroyed"


class SandboxPolicy(BaseModel):
    name: str = "safe_analysis"
    image: str = "python:3.11-slim"
    cpu: float = 1.0
    memory_mb: int = 1024
    disk_mb: int = 1024
    timeout_seconds: int = 300
    network_default: str = "deny"
    network_allow: List[str] = Field(default_factory=list)
    fs_read: List[str] = Field(default_factory=lambda: ["/input", "/workspace"])
    fs_write: List[str] = Field(default_factory=lambda: ["/output", "/tmp", "/workspace"])
    commands_allow: List[str] = Field(default_factory=lambda: ["python", "pip"])
    credentials_allow: List[str] = Field(default_factory=list)
    max_artifact_bytes: int = 50 * 1024 * 1024  # 50 MB per artifact
    max_artifact_count: int = 20


class ExecutionStepResult(BaseModel):
    sequence: int = 1
    step_type: str = "command"  # upload, command, download
    command: Optional[str] = None
    status: str = "completed"  # completed, failed, timeout
    exit_code: Optional[int] = 0
    stdout_excerpt: Optional[str] = None
    stderr_excerpt: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


class ArtifactRef(BaseModel):
    name: str
    relative_path: str
    size_bytes: int
    content_hash: str  # sha256
    mime_type: Optional[str] = "application/octet-stream"
    object_storage_uri: Optional[str] = None
    artifact_id: Optional[str] = None


class ExecutionJobRequest(BaseModel):
    workspace_id: int
    brain_id: Optional[int] = None
    user_id: int
    agent_key: str
    agent_run_id: Optional[int] = None
    provider: Optional[str] = None
    policy_name: str = "safe_analysis"
    custom_policy: Optional[SandboxPolicy] = None
    commands: List[str] = Field(default_factory=list)
    input_files: Dict[str, bytes] = Field(default_factory=dict)  # relative_path -> bytes
    metadata: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None


class ExecutionJobResult(BaseModel):
    job_id: str
    workspace_id: int
    status: ExecutionStatus
    provider: str
    sandbox_id: Optional[str] = None
    steps: List[ExecutionStepResult] = Field(default_factory=list)
    artifacts: List[ArtifactRef] = Field(default_factory=list)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    destroyed_at: Optional[datetime] = None


class ExecutionHealth(BaseModel):
    provider: str
    available: bool
    version: Optional[str] = None
    active_sandboxes: int = 0
    details: Dict[str, Any] = Field(default_factory=dict)

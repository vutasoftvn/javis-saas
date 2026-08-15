import ipaddress
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

from app.agents.execution.errors import ExecutionErrorCode, ExecutionRuntimeError
from app.agents.execution.types import SandboxPolicy

FORBIDDEN_HOST_PATTERNS = [
    re.compile(r"^localhost$", re.IGNORECASE),
    re.compile(r"^127\."),
    re.compile(r"^169\.254\."),
    re.compile(r"^10\."),
    re.compile(r"^192\.168\."),
    re.compile(r"^172\.(1[6-9]|2[0-9]|3[0-1])\."),
    re.compile(r"^0\.0\.0\.0$"),
    re.compile(r"^::1$"),
]


class SkillPermissions(BaseModel):
    network: List[str] = Field(default_factory=list)
    filesystem: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "read": ["/input", "/workspace"],
            "write": ["/output", "/tmp", "/workspace"],
        }
    )
    credentials: List[str] = Field(default_factory=list)


class SkillResources(BaseModel):
    cpu: float = Field(default=1.0, ge=0.1, le=2.0)
    memory_mb: int = Field(default=1024, ge=128, le=2048)
    disk_mb: int = Field(default=1024, ge=256, le=2048)
    timeout_seconds: int = Field(default=300, ge=10, le=600)


class SkillManifest(BaseModel):
    name: str
    version: str = "1.0.0"
    description: Optional[str] = None
    runtime: str = "python:3.11-slim"
    entrypoint: str = "main.py"
    commands: Optional[List[str]] = None
    permissions: SkillPermissions = Field(default_factory=SkillPermissions)
    resources: SkillResources = Field(default_factory=SkillResources)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9_-]{3,64}$", v):
            raise ValueError("Skill name must be 3-64 alphanumeric, underscore, or hyphen characters.")
        return v


def validate_manifest_to_policy(manifest: SkillManifest) -> SandboxPolicy:
    """Validate skill manifest safety requirements and convert into an isolated SandboxPolicy."""
    # 1. Validate Network Allowlist Safety (Strict zero LAN / zero metadata rule)
    allowed_domains: List[str] = []
    for host in manifest.permissions.network:
        host_clean = host.strip().lower()
        if not host_clean:
            continue

        for pat in FORBIDDEN_HOST_PATTERNS:
            if pat.search(host_clean):
                raise ExecutionRuntimeError(
                    code=ExecutionErrorCode.EXEC_POLICY_VIOLATION,
                    message=f"Skill network allowlist contains forbidden private/internal destination: '{host_clean}'",
                )

        try:
            ip_obj = ipaddress.ip_address(host_clean)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
                raise ExecutionRuntimeError(
                    code=ExecutionErrorCode.EXEC_POLICY_VIOLATION,
                    message=f"Skill network allowlist cannot contain private/local IP: '{host_clean}'",
                )
        except ValueError:
            # Valid domain name format
            pass

        allowed_domains.append(host_clean)

    # 2. Filesystem Paths
    fs_read = manifest.permissions.filesystem.get("read", ["/input", "/workspace"])
    fs_write = manifest.permissions.filesystem.get("write", ["/output", "/tmp", "/workspace"])

    # 3. Commands Allowlist
    cmds_allow = ["python", "python3", "node", "npm", "bash", "sh"]

    # 4. Generate SandboxPolicy
    return SandboxPolicy(
        name=f"skill_{manifest.name}",
        image=manifest.runtime,
        cpu=manifest.resources.cpu,
        memory_mb=manifest.resources.memory_mb,
        disk_mb=manifest.resources.disk_mb,
        timeout_seconds=manifest.resources.timeout_seconds,
        network_default="deny",
        network_allow=allowed_domains,
        fs_read=fs_read,
        fs_write=fs_write,
        commands_allow=cmds_allow,
        credentials_allow=manifest.permissions.credentials,
        max_artifact_bytes=50 * 1024 * 1024,
        max_artifact_count=30,
    )

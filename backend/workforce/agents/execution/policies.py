from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from workforce.agents.execution.types import SandboxPolicy

DEFAULT_PRESETS: Dict[str, SandboxPolicy] = {
    "safe_analysis": SandboxPolicy(
        name="safe_analysis",
        image="python:3.11-slim",
        cpu=1.0,
        memory_mb=1024,
        disk_mb=1024,
        timeout_seconds=300,
        network_default="deny",
        network_allow=[],
        fs_read=["/input", "/workspace"],
        fs_write=["/output", "/tmp", "/workspace"],
        commands_allow=["python", "python3", "pip"],
        credentials_allow=[],
        max_artifact_bytes=50 * 1024 * 1024,
        max_artifact_count=20,
    ),
    "research": SandboxPolicy(
        name="research",
        image="python:3.11-slim",
        cpu=1.0,
        memory_mb=1024,
        disk_mb=1024,
        timeout_seconds=300,
        network_default="deny",
        network_allow=["api.openai.com", "api.deepseek.com", "openrouter.ai"],
        fs_read=["/input", "/workspace"],
        fs_write=["/output", "/tmp", "/workspace"],
        commands_allow=["python", "python3", "curl"],
        credentials_allow=[],
        max_artifact_bytes=50 * 1024 * 1024,
        max_artifact_count=30,
    ),
    "marketing": SandboxPolicy(
        name="marketing",
        image="python:3.11-slim",
        cpu=1.0,
        memory_mb=1024,
        disk_mb=1024,
        timeout_seconds=300,
        network_default="deny",
        network_allow=[],
        fs_read=["/input", "/workspace"],
        fs_write=["/output", "/tmp", "/workspace"],
        commands_allow=["python", "python3"],
        credentials_allow=[],
        max_artifact_bytes=50 * 1024 * 1024,
        max_artifact_count=20,
    ),
    "finance": SandboxPolicy(
        name="finance",
        image="python:3.11-slim",
        cpu=1.0,
        memory_mb=1024,
        disk_mb=1024,
        timeout_seconds=300,
        network_default="deny",
        network_allow=[],
        fs_read=["/input", "/workspace"],
        fs_write=["/output", "/tmp", "/workspace"],
        commands_allow=["python", "python3"],
        credentials_allow=[],
        max_artifact_bytes=50 * 1024 * 1024,
        max_artifact_count=20,
    ),
    "coding": SandboxPolicy(
        name="coding",
        image="python:3.11-slim",
        cpu=2.0,
        memory_mb=2048,
        disk_mb=2048,
        timeout_seconds=600,
        network_default="deny",
        network_allow=["github.com", "pypi.org", "files.pythonhosted.org"],
        fs_read=["/input", "/workspace"],
        fs_write=["/output", "/tmp", "/workspace"],
        commands_allow=["python", "python3", "pytest", "git", "pip"],
        credentials_allow=[],
        max_artifact_bytes=100 * 1024 * 1024,
        max_artifact_count=50,
    ),
}


def load_policy(
    db: Optional[Session] = None,
    workspace_id: Optional[int] = None,
    preset_name: str = "safe_analysis",
) -> SandboxPolicy:
    """Load sandbox policy from database with workspace override or fallback to default preset."""
    if db is not None:
        try:
            from workforce.agents.execution.models import SandboxPolicyRecord

            # 1. Check workspace-specific policy
            if workspace_id:
                rec = (
                    db.query(SandboxPolicyRecord)
                    .filter(
                        SandboxPolicyRecord.workspace_id == workspace_id,
                        SandboxPolicyRecord.name == preset_name,
                    )
                    .first()
                )
                if rec:
                    return _record_to_policy(rec)

            # 2. Check global policy (workspace_id IS NULL)
            rec = (
                db.query(SandboxPolicyRecord)
                .filter(
                    SandboxPolicyRecord.workspace_id.is_(None),
                    SandboxPolicyRecord.name == preset_name,
                )
                .first()
            )
            if rec:
                return _record_to_policy(rec)
        except Exception:
            pass

    # Fallback to built-in presets
    return DEFAULT_PRESETS.get(preset_name, DEFAULT_PRESETS["safe_analysis"]).model_copy(deep=True)


def _record_to_policy(rec: Any) -> SandboxPolicy:
    limits = rec.resource_limit_jsonb or {}
    net = rec.network_policy_jsonb or {}
    fs = rec.filesystem_policy_jsonb or {}
    cmds = rec.command_policy_jsonb or {}
    creds = rec.credential_policy_jsonb or {}

    return SandboxPolicy(
        name=rec.name,
        image=limits.get("image", "python:3.11-slim"),
        cpu=float(limits.get("cpu", 1.0)),
        memory_mb=int(limits.get("memory_mb", 1024)),
        disk_mb=int(limits.get("disk_mb", 1024)),
        timeout_seconds=int(rec.timeout_seconds or 300),
        network_default=net.get("default", "deny"),
        network_allow=net.get("allow", []),
        fs_read=fs.get("read", ["/input", "/workspace"]),
        fs_write=fs.get("write", ["/output", "/tmp", "/workspace"]),
        commands_allow=cmds.get("allow", ["python"]),
        credentials_allow=creds.get("allow", []),
        max_artifact_bytes=int(limits.get("max_artifact_bytes", 50 * 1024 * 1024)),
        max_artifact_count=int(limits.get("max_artifact_count", 20)),
    )

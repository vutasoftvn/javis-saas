"""Agent workspace của founder = bản clone bị ràng buộc của một agent built-in.

Spec: docs/superpowers/specs/2026-09-27-agent-clone-executor-design.md.

`content_json` của asset AGENT là *override manifest* (`workspace_agent.v1`), không phải spec đầy
đủ: chỉ tên, mô tả, phần instructions bổ sung và tập capability thu hẹp. Model policy, autonomy
(tier), prompt_ref, pinned_skills luôn lấy từ spec gốc đã pin (id + version + hash), nên clone không
thể leo thang quyền hay đổi model policy. Module này là nguồn DUY NHẤT của luật đó — evaluation
(apps/cosa/assets/evaluation_service.py) và runtime (worker) cùng gọi vào đây.
"""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass
from typing import Any, Literal

from agent.assets.contracts import AssetKind, AssetLifecycle, AssetOrigin
from agent.contracts.spec import AgentSpec
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.agents.startup_team_profiles_generated import STARTUP_TEAM_PROFILE_KEYS

__all__ = [
    "MAX_ADDENDUM_LEN",
    "MAX_DESCRIPTION_LEN",
    "MAX_NAME_LEN",
    "WORKSPACE_AGENT_SCHEMA",
    "AgentViolation",
    "ResolvedWorkspaceAgent",
    "WorkspaceAgentContent",
    "WorkspaceAgentError",
    "build_clone_content",
    "build_effective_spec",
    "cloneable_profiles",
    "evaluate_agent_content",
    "profile_for_spec_id",
    "publish_manifest",
    "resolve_builtin_origin",
    "resolve_workspace_agent_spec",
    "workspace_agent_spec_id",
]

WORKSPACE_AGENT_SCHEMA = "workspace_agent.v1"
MAX_NAME_LEN = 80
MAX_DESCRIPTION_LEN = 500
MAX_ADDENDUM_LEN = 4000

# customer_support chạy nhánh copilot + knowledge gate riêng; founder_assistant không phải agent vận
# hành của Project. Hai profile này không clone được.
_NON_CLONEABLE_PROFILES = frozenset({"founder_assistant", "customer_support"})

# Cùng pattern với services/company/operations/services/founder-asset-authoring.service.ts
# (SECRET_PATTERNS) để company và evaluation chặn cùng một loại chuỗi.
_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "api_key_or_token",
        re.compile(r"\b(sk-[A-Za-z0-9]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{12,})\b"),
    ),
    (
        "jwt_like_token",
        re.compile(r"\bey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    ),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9\-_.]{20,}", re.IGNORECASE)),
    ("pem_private_key", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    ("raw_http_header", re.compile(r"\b(Authorization|Cookie)\s*:\s*\S+", re.IGNORECASE)),
)


class WorkspaceAgentError(Exception):
    """Lỗi có mã ổn định (an toàn để trả về client/callback)."""

    def __init__(self, reason_code: str, message: str | None = None) -> None:
        super().__init__(message or reason_code)
        self.reason_code = reason_code


@dataclass(frozen=True)
class AgentViolation:
    code: str
    message: str


class WorkspaceAgentOrigin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_key: str
    spec_id: str
    version: str
    definition_hash: str


class WorkspaceAgentContent(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["workspace_agent.v1"] = Field(alias="schema")
    origin: WorkspaceAgentOrigin
    name: str
    description: str = ""
    instructions_addendum: str = ""
    capability_refs: list[str]


def cloneable_profiles() -> dict[str, AgentSpec]:
    return {
        key: AGENT_PROFILE_SPECS[key]
        for key in STARTUP_TEAM_PROFILE_KEYS
        if key in AGENT_PROFILE_SPECS and key not in _NON_CLONEABLE_PROFILES
    }


def profile_for_spec_id(spec_id: str) -> str | None:
    for key, spec in cloneable_profiles().items():
        if spec.id == spec_id:
            return key
    return None


def _spec_hash(spec: AgentSpec) -> str:
    return spec.compute_hash()


async def resolve_builtin_origin(
    spec_registry: Any | None,
    spec_id: str,
    version: str | None = None,
    definition_hash: str | None = None,
) -> tuple[str, AgentSpec, str]:
    """Pin spec built-in gốc. Trả (profile_key, spec, definition_hash).

    Không truyền version+hash → pin bản built-in đang import. Có truyền → phải khớp tuyệt đối với
    bản đang import hoặc bản bất biến trong spec registry (như `_spec_for_authority` của worker).
    """
    profile = profile_for_spec_id(spec_id)
    if profile is None:
        raise WorkspaceAgentError(
            "AGENT_ORIGIN_UNAVAILABLE", f"{spec_id} is not a cloneable built-in agent"
        )
    local = cloneable_profiles()[profile]
    if not version and not definition_hash:
        return profile, local, _spec_hash(local)
    if not version or not definition_hash:
        raise WorkspaceAgentError(
            "AGENT_ORIGIN_UNAVAILABLE", "origin pin needs both version and definition_hash"
        )
    if local.version == version and _spec_hash(local) == definition_hash:
        return profile, local, definition_hash
    record = None
    if spec_registry is not None:
        with contextlib.suppress(Exception):
            record = await spec_registry.get("agent", spec_id, version)
    if record is not None and getattr(record, "definition_hash", None) == definition_hash:
        return profile, AgentSpec(**record.content), definition_hash
    raise WorkspaceAgentError(
        "AGENT_ORIGIN_UNAVAILABLE", f"{spec_id}@{version} with the pinned hash is not available"
    )


def build_clone_content(
    profile_key: str,
    origin_spec: AgentSpec,
    origin_hash: str,
    *,
    name: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": WORKSPACE_AGENT_SCHEMA,
        "origin": {
            "profile_key": profile_key,
            "spec_id": origin_spec.id,
            "version": origin_spec.version,
            "definition_hash": origin_hash,
        },
        "name": (name or f"{profile_key} (custom)")[:MAX_NAME_LEN],
        "description": (description or "")[:MAX_DESCRIPTION_LEN],
        "instructions_addendum": "",
        "capability_refs": list(origin_spec.capability_refs),
    }


def _secret_violation(value: str, field: str) -> AgentViolation | None:
    for name, pattern in _SECRET_PATTERNS:
        if pattern.search(value):
            return AgentViolation("AGENT_SECRET_DETECTED", f"{field} looks like a {name}")
    return None


async def evaluate_agent_content(
    content: dict[str, Any],
    *,
    lineage: AssetOrigin | None,
    spec_registry: Any | None,
) -> tuple[list[AgentViolation], WorkspaceAgentContent | None, AgentSpec | None]:
    """Chạy toàn bộ luật cho một asset AGENT. Trả (vi phạm, manifest đã parse, spec gốc)."""
    if lineage is None or not lineage.asset_id:
        return (
            [AgentViolation("AGENT_ORIGIN_REQUIRED", "agent asset has no built-in lineage")],
            None,
            None,
        )
    try:
        manifest = WorkspaceAgentContent.model_validate(content)
    except ValidationError as exc:
        fields = sorted({".".join(str(p) for p in err["loc"]) for err in exc.errors()})
        return (
            [AgentViolation("AGENT_MANIFEST_INVALID", f"invalid fields: {', '.join(fields)}")],
            None,
            None,
        )

    violations: list[AgentViolation] = []
    origin = manifest.origin
    if (
        origin.spec_id != lineage.asset_id
        or origin.version != lineage.version
        or origin.definition_hash != lineage.definition_hash
    ):
        violations.append(
            AgentViolation("AGENT_ORIGIN_MISMATCH", "content origin differs from asset lineage")
        )

    origin_spec: AgentSpec | None = None
    try:
        profile, origin_spec, _ = await resolve_builtin_origin(
            spec_registry, lineage.asset_id, lineage.version, lineage.definition_hash
        )
        if profile != origin.profile_key:
            violations.append(
                AgentViolation("AGENT_ORIGIN_MISMATCH", "origin profile_key differs from lineage")
            )
    except WorkspaceAgentError as exc:
        violations.append(AgentViolation(exc.reason_code, str(exc)))

    if origin_spec is not None:
        extra = sorted(set(manifest.capability_refs) - set(origin_spec.capability_refs))
        if extra:
            violations.append(
                AgentViolation(
                    "AGENT_CAPABILITY_ESCALATION",
                    f"capability_refs not granted to the origin agent: {', '.join(extra)}",
                )
            )

    name = manifest.name.strip()
    if not name or len(manifest.name) > MAX_NAME_LEN:
        violations.append(AgentViolation("AGENT_NAME_INVALID", "name must be 1-80 characters"))
    if len(manifest.description) > MAX_DESCRIPTION_LEN:
        violations.append(
            AgentViolation("AGENT_DESCRIPTION_TOO_LONG", "description exceeds 500 characters")
        )
    if len(manifest.instructions_addendum) > MAX_ADDENDUM_LEN:
        violations.append(
            AgentViolation(
                "AGENT_ADDENDUM_TOO_LONG", "instructions_addendum exceeds 4000 characters"
            )
        )
    for field, value in (
        ("name", manifest.name),
        ("description", manifest.description),
        ("instructions_addendum", manifest.instructions_addendum),
    ):
        hit = _secret_violation(value, field)
        if hit is not None:
            violations.append(hit)
    return violations, manifest, origin_spec


def workspace_agent_spec_id(workspace_id: str, asset_id: str) -> str:
    # Spec registry là toàn cục: gắn workspace vào id để hai workspace clone cùng built-in (cùng
    # asset version 0.1.0, nội dung khác) không đụng nhau.
    return f"workspace.{workspace_id}.{asset_id}"


def build_effective_spec(
    origin_spec: AgentSpec,
    manifest: WorkspaceAgentContent,
    *,
    workspace_id: str,
    asset_id: str,
    version: str,
    asset_definition_hash: str,
) -> AgentSpec:
    """Spec hiệu lực = spec gốc + override. Không trường nào ngoài tên/mô tả/addendum/capability
    thay đổi so với spec gốc; capability giữ thứ tự của gốc và chỉ còn phần giao."""
    allowed = set(manifest.capability_refs)
    capability_refs = [c for c in origin_spec.capability_refs if c in allowed]
    tool_contract_refs = [
        ref for ref in origin_spec.tool_contract_refs if ref.capability_id in allowed
    ]
    addendum = manifest.instructions_addendum.strip()
    instructions = origin_spec.instructions
    if addendum:
        instructions = f"{instructions}\n\n{addendum}" if instructions else addendum
    metadata = {
        **origin_spec.metadata,
        "origin_agent_spec_id": origin_spec.id,
        "workspace_agent": {
            "asset_id": asset_id,
            "version": version,
            "definition_hash": asset_definition_hash,
            "display_name": manifest.name,
            "description": manifest.description,
            "origin": manifest.origin.model_dump(),
        },
    }
    effective = origin_spec.model_copy(
        update={
            "id": workspace_agent_spec_id(workspace_id, asset_id),
            "version": version,
            "instructions": instructions,
            "capability_refs": capability_refs,
            "tool_contract_refs": tool_contract_refs,
            "metadata": metadata,
            "definition_hash": None,
        }
    )
    return effective.with_hash()


def publish_manifest(content: dict[str, Any]) -> dict[str, Any] | None:
    """`agentManifest` cho callback PUBLISH (company dùng làm biên nhận để cấp grant)."""
    try:
        manifest = WorkspaceAgentContent.model_validate(content)
    except ValidationError:
        return None
    return {
        "originProfileKey": manifest.origin.profile_key,
        "originSpec": {
            "id": manifest.origin.spec_id,
            "version": manifest.origin.version,
            "definitionHash": manifest.origin.definition_hash,
        },
        "capabilityRefs": list(manifest.capability_refs),
        "displayName": manifest.name,
    }


@dataclass(frozen=True)
class ResolvedWorkspaceAgent:
    spec: AgentSpec
    origin_spec: AgentSpec
    profile_key: str
    display_name: str


async def resolve_workspace_agent_spec(
    *,
    asset_repository: Any,
    spec_registry: Any | None,
    workspace_id: str,
    asset_id: str,
    version: str,
    definition_hash: str,
) -> ResolvedWorkspaceAgent:
    """Load đúng version PUBLISHED (exact hash, không "latest") rồi dựng spec hiệu lực."""
    if asset_repository is None:
        raise WorkspaceAgentError("workspace_agent_repository_unavailable")
    item = await asset_repository.get_version(workspace_id, asset_id, version)
    if item is None:
        raise WorkspaceAgentError("workspace_agent_not_found")
    if item.kind != AssetKind.AGENT:
        raise WorkspaceAgentError("workspace_agent_not_agent")
    if item.lifecycle != AssetLifecycle.PUBLISHED:
        raise WorkspaceAgentError("workspace_agent_not_published")
    if item.definition_hash != definition_hash:
        raise WorkspaceAgentError("workspace_agent_hash_mismatch")

    violations, manifest, origin_spec = await evaluate_agent_content(
        item.content_json, lineage=item.origin, spec_registry=spec_registry
    )
    if violations or manifest is None or origin_spec is None:
        code = violations[0].code if violations else "AGENT_MANIFEST_INVALID"
        raise WorkspaceAgentError("workspace_agent_invalid", code)

    spec = build_effective_spec(
        origin_spec,
        manifest,
        workspace_id=workspace_id,
        asset_id=asset_id,
        version=version,
        asset_definition_hash=item.definition_hash,
    )
    return ResolvedWorkspaceAgent(
        spec=spec,
        origin_spec=origin_spec,
        profile_key=manifest.origin.profile_key,
        display_name=manifest.name,
    )

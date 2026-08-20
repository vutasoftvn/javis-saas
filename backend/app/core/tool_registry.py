from dataclasses import dataclass
from collections.abc import Callable
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.feature_flags import is_enabled


@dataclass(frozen=True)
class ToolSpec:
    namespace: str
    name: str
    callable: Callable
    flag_key: Optional[str] = None
    # JSON Schema để phát tool này cho chat text. Voice không cần: livekit-agents suy ra
    # schema từ chữ ký Python + docstring của wrapper, còn provider chat đòi schema tường
    # minh. Để None nghĩa là "tool này cố tình không dành cho chat" - xem
    # test_tool_registry.py::test_every_tool_declares_whether_chat_can_use_it, nó bắt phải
    # quyết định chứ không cho quên.
    chat_schema: Optional[dict[str, Any]] = None
    risk_level: str = "low"  # "low" | "medium" | "high" | "critical"
    permission_level: str = "read_only"  # "read_only" | "scoped_write" | "admin_write"
    requires_approval: bool = False
    idempotency: bool = True
    allowed_agent_keys: Optional[list[str]] = None
    mutating: bool = False
    external: bool = False
    # G3 Phase 1C (Toolset Resolver). All four default to "no restriction" so
    # every tool registered before this phase behaves exactly as before.
    #
    # availability_check: fail-closed extra gate evaluated by
    # toolset_resolver.resolve_toolset() right before a tool would be
    # offered to an LLM - receives a ToolsetContext, returns False (or
    # raises) to exclude. Distinct from allowed_agent_keys (static allowlist)
    # because it can depend on runtime state (workspace stage, plan, env).
    availability_check: Optional[Callable[[Any], bool]] = None
    # Free-form classification, not yet enforced anywhere - lets a tool
    # declare "read" | "draft" | "external" | "destructive" richer than the
    # mutating/external booleans above without forcing every existing
    # registration to be re-classified in this pass.
    side_effect_type: Optional[str] = None
    # e.g. "native" | "connector" | "automation" - which subsystem actually
    # executes the tool. Metadata only for now.
    execution_backend: str = "native"
    # None = available at every workspace stage. Set to restrict a tool to
    # specific `Workspace.company_stage` values (see toolset_resolver.py).
    available_stages: Optional[frozenset[str]] = None
    
    # Phase 3 Extensibility Fields
    input_schema: Optional[dict[str, Any]] = None
    output_schema: Optional[dict[str, Any]] = None
    timeout_seconds: Optional[int] = None
    retry_policy: Optional[dict[str, Any]] = None
    idempotency_key_field: Optional[str] = None
    concurrency_key: Optional[str] = None
    required_scope_level: Optional[str] = None
    required_secret_refs: Optional[list[str]] = None
    backend_id: Optional[str] = None

    @property
    def qualified_name(self) -> str:
        return f"{self.namespace}.{self.name}"

    @property
    def flat_name(self) -> str:
        """Tên gửi cho provider chat. Dấu chấm bị loại vì tên function của OpenAI (và các
        client tương thích) chỉ nhận ``^[a-zA-Z0-9_-]{1,64}$`` - gửi "company.ceo_brief"
        là provider trả 400 và hỏng cả lượt chat."""
        return f"{self.namespace}_{self.name}"

    def to_openai_spec(self) -> dict[str, Any]:
        schema = self.chat_schema or {}
        return {
            "type": "function",
            "function": {
                "name": self.flat_name,
                "description": schema.get("description", ""),
                "parameters": schema.get(
                    "parameters", {"type": "object", "properties": {}, "required": []}
                ),
            },
        }


_registry: dict[str, ToolSpec] = {}


def register(
    namespace: str,
    name: str,
    flag_key: Optional[str] = None,
    chat_schema: Optional[dict[str, Any]] = None,
    risk_level: str = "low",
    permission_level: str = "read_only",
    requires_approval: bool = False,
    idempotency: bool = True,
    allowed_agent_keys: Optional[list[str]] = None,
    mutating: bool = False,
    external: bool = False,
    availability_check: Optional[Callable[[Any], bool]] = None,
    side_effect_type: Optional[str] = None,
    execution_backend: str = "native",
    available_stages: Optional[frozenset[str]] = None,
    input_schema: Optional[dict[str, Any]] = None,
    output_schema: Optional[dict[str, Any]] = None,
    timeout_seconds: Optional[int] = None,
    retry_policy: Optional[dict[str, Any]] = None,
    idempotency_key_field: Optional[str] = None,
    concurrency_key: Optional[str] = None,
    required_scope_level: Optional[str] = None,
    required_secret_refs: Optional[list[str]] = None,
    backend_id: Optional[str] = None,
):
    def decorator(function: Callable) -> Callable:
        spec = ToolSpec(
            namespace=namespace,
            name=name,
            callable=function,
            flag_key=flag_key,
            chat_schema=chat_schema,
            risk_level=risk_level,
            permission_level=permission_level,
            requires_approval=requires_approval,
            idempotency=idempotency,
            allowed_agent_keys=allowed_agent_keys,
            mutating=mutating,
            external=external,
            availability_check=availability_check,
            side_effect_type=side_effect_type,
            execution_backend=execution_backend,
            available_stages=available_stages,
            input_schema=input_schema,
            output_schema=output_schema,
            timeout_seconds=timeout_seconds,
            retry_policy=retry_policy,
            idempotency_key_field=idempotency_key_field,
            concurrency_key=concurrency_key,
            required_scope_level=required_scope_level,
            required_secret_refs=required_secret_refs,
            backend_id=backend_id,
        )
        _registry[spec.qualified_name] = spec
        return function
    return decorator


def get_registered_tools() -> dict[str, ToolSpec]:
    return dict(_registry)


def available_tools(db: Session, workspace_id: int) -> list[ToolSpec]:
    return [
        spec for spec in _registry.values()
        if spec.flag_key is None or is_enabled(db, spec.flag_key, workspace_id)
    ]


def chat_tools(db: Session, workspace_id: int) -> list[ToolSpec]:
    """Tập con của ``available_tools`` mà chat text được phép gọi.

    Chat đọc cả email và tài liệu do người ngoài gửi tới, nên mọi tool ghi/hành động đều
    cố tình không có ``chat_schema``: chặn bằng cấu trúc (model không hề nhìn thấy tool)
    thay vì bằng câu dặn trong system prompt, cùng lý do gmail_tools không có tool gửi thư.

    ``mutating`` bị loại thêm một lần nữa ở đây (không chỉ dựa vào quy ước "quên
    chat_schema"): company_tools.py gọi thẳng ``execute_tool_spec`` mà không qua
    GovernanceKernel, nên một tool mutating lỡ khai báo cả ``chat_schema`` vẫn không được
    lọt vào danh sách này.
    """
    return [
        spec for spec in available_tools(db, workspace_id)
        if spec.chat_schema and not spec.mutating
    ]


def get_tool_by_flat_name(flat_name: str) -> Optional[ToolSpec]:
    """Tra ngược tên phẳng model gửi lên về ToolSpec.

    Duyệt tuyến tính thay vì dựng thêm một dict song song: registry chỉ vài chục mục và
    một dict thứ hai là một chỗ nữa có thể lệch với ``_registry``.
    """
    for spec in _registry.values():
        if spec.flat_name == flat_name:
            return spec
    return None

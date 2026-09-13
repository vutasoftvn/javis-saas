from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent.workflows.schema import StepType, WorkflowSpec

__all__ = [
    "UnsupportedWorkflowStepError",
    "WorkflowPublishValidator",
    "WorkflowValidationContext",
    "WorkflowValidationResult",
]


class UnsupportedWorkflowStepError(Exception):
    """Raised when an engine encounters a workflow step type with no registered executor."""

    def __init__(self, step_id: str, step_type: Any) -> None:
        type_str = step_type.value if hasattr(step_type, "value") else str(step_type)
        super().__init__(f"Unsupported workflow step type '{type_str}' for step '{step_id}'")
        self.step_id = step_id
        self.step_type = type_str


@dataclass
class WorkflowValidationContext:
    workspace_id: str
    project_id: str | None = None
    active_deployments: dict[str, Any] = field(default_factory=dict)
    active_capabilities: set[str] = field(default_factory=set)
    registered_handlers: set[str] = field(default_factory=set)
    published_assets: dict[str, Any] = field(default_factory=dict)
    registered_executors: set[StepType | str] = field(
        default_factory=lambda: {StepType.TOOL_CALL, StepType.APPROVAL_GATE, StepType.DETERMINISTIC}
    )


@dataclass
class WorkflowValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class WorkflowPublishValidator:
    """Two-level validator enforcing structural DAG validity and execution plane readiness."""

    SUPPORTED_V1_STEP_TYPES = frozenset(
        {
            StepType.AGENT,
            StepType.TOOL_CALL,
            StepType.APPROVAL_GATE,
            StepType.DETERMINISTIC,
            StepType.RETRY,
        }
    )

    DEFAULT_EXECUTABLE_STEP_TYPES = frozenset(
        {
            StepType.AGENT,
            StepType.TOOL_CALL,
            StepType.APPROVAL_GATE,
            StepType.DETERMINISTIC,
            StepType.RETRY,
        }
    )

    @classmethod
    def validate(
        cls,
        spec: WorkflowSpec,
        context: WorkflowValidationContext | dict[str, Any] | None = None,
    ) -> WorkflowValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        ctx: WorkflowValidationContext | None = None
        if isinstance(context, WorkflowValidationContext):
            ctx = context
        elif isinstance(context, dict):
            ctx = WorkflowValidationContext(
                workspace_id=context.get("workspace_id", "default"),
                project_id=context.get("project_id"),
                active_deployments=context.get("active_deployments", {}),
                active_capabilities=set(context.get("active_capabilities", [])),
                registered_handlers=set(context.get("registered_handlers", [])),
                published_assets=context.get("published_assets", {}),
                registered_executors=set(context.get("registered_executors", cls.DEFAULT_EXECUTABLE_STEP_TYPES)),
            )

        executors = (
            set(ctx.registered_executors)
            if (ctx and ctx.registered_executors is not None)
            else set(cls.DEFAULT_EXECUTABLE_STEP_TYPES)
        )
        executor_types: set[Any] = set()
        for e in executors:
            if isinstance(e, StepType):
                executor_types.add(e)
                executor_types.add(e.value)
            elif isinstance(e, str):
                executor_types.add(e)
                try:
                    executor_types.add(StepType(e))
                except ValueError:
                    pass

        # 1. Structural DAG validation
        try:
            getattr(spec, "_validate_dag")()
        except Exception as exc:
            errors.append(f"DAG structure error: {exc}")

        # 2. Node semantics and context checks
        for step in spec.steps:
            if step.type not in cls.SUPPORTED_V1_STEP_TYPES:
                errors.append(
                    f"Step '{step.id}' uses unsupported type '{step.type}'. "
                    f"Supported types: {sorted(t.value for t in cls.SUPPORTED_V1_STEP_TYPES)}"
                )
                continue

            if step.type not in executor_types and step.type.value not in executor_types:
                errors.append(
                    f"Step '{step.id}' uses step type '{step.type.value}' which has no registered executor "
                    f"in execution plane; publish rejected until executor is implemented"
                )
                continue

            if step.type == StepType.AGENT:
                dep_id = (
                    step.project_agent_deployment_id
                    or step.inputs.get("project_agent_deployment_id")
                    or step.metadata.get("project_agent_deployment_id")
                )
                if not dep_id:
                    errors.append(f"AGENT step '{step.id}' missing project_agent_deployment_id")
                elif ctx and ctx.active_deployments and dep_id not in ctx.active_deployments:
                    errors.append(
                        f"AGENT step '{step.id}' references inactive or unknown deployment '{dep_id}'"
                    )

            elif step.type == StepType.TOOL_CALL:
                tool_name = step.tool or step.inputs.get("tool") or step.inputs.get("capability_id")
                if not tool_name:
                    errors.append(f"TOOL_CALL step '{step.id}' missing tool/capability identifier")
                elif ctx and ctx.active_capabilities and tool_name not in ctx.active_capabilities:
                    errors.append(
                        f"TOOL_CALL step '{step.id}' references non-allowlisted capability '{tool_name}'"
                    )

            elif step.type == StepType.APPROVAL_GATE:
                action = step.action or step.inputs.get("action")
                subject = step.subject_key or step.inputs.get("subject_key")
                if not action:
                    errors.append(f"APPROVAL_GATE step '{step.id}' missing action")
                if not subject:
                    errors.append(f"APPROVAL_GATE step '{step.id}' missing subject_key")

            elif step.type == StepType.RETRY:
                handler = step.handler or (step.inputs.get("handler") if step.inputs else None) or step.action
                if not handler:
                    errors.append(f"RETRY step '{step.id}' missing registered retry target")
                else:
                    from agent.workflows.deterministic_handlers import WHITELISTED_DETERMINISTIC_HANDLERS

                    known_handlers = (
                        set(ctx.registered_handlers)
                        if (ctx and ctx.registered_handlers)
                        else set(WHITELISTED_DETERMINISTIC_HANDLERS.keys())
                    )
                    if handler not in known_handlers:
                        errors.append(
                            f"RETRY step '{step.id}' references unregistered retry target '{handler}'"
                        )
                max_attempts = step.inputs.get("max_attempts") or step.metadata.get("max_attempts")
                if max_attempts is not None:
                    try:
                        m = int(max_attempts)
                        if not (1 <= m <= 10):
                            errors.append(f"RETRY step '{step.id}' max_attempts must be between 1 and 10")
                    except (ValueError, TypeError):
                        errors.append(f"RETRY step '{step.id}' max_attempts must be an integer")

            elif step.type == StepType.DETERMINISTIC:
                handler = step.handler or (step.inputs.get("handler") if step.inputs else None) or step.action
                if not handler:
                    errors.append(f"DETERMINISTIC step '{step.id}' missing handler")
                else:
                    from agent.workflows.deterministic_handlers import WHITELISTED_DETERMINISTIC_HANDLERS

                    known_handlers = (
                        set(ctx.registered_handlers)
                        if (ctx and ctx.registered_handlers)
                        else set(WHITELISTED_DETERMINISTIC_HANDLERS.keys())
                    )
                    if handler not in known_handlers:
                        errors.append(
                            f"DETERMINISTIC step '{step.id}' references unregistered handler '{handler}'"
                        )

        return WorkflowValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

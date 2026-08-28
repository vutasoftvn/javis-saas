from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agent_core.workflows.schema import WorkflowSpec

__all__ = ["WorkflowDefinitionLoadError", "load_workflow_spec"]


class WorkflowDefinitionLoadError(Exception):
    pass


def load_workflow_spec(source: str | Path | dict[str, Any]) -> WorkflowSpec:
    """Nạp và validate declarative WorkflowSpec từ file YAML, chuỗi YAML hoặc raw dictionary."""
    if isinstance(source, dict):
        return WorkflowSpec.model_validate(source)

    if isinstance(source, Path) or (
        isinstance(source, str)
        and ("\n" not in source and (source.endswith(".yaml") or source.endswith(".yml")))
    ):
        path = Path(source)
        if not path.exists():
            raise WorkflowDefinitionLoadError(f"Workflow YAML file not found: {path}")
        content = path.read_text(encoding="utf-8")
    else:
        content = str(source)

    try:
        raw = yaml.safe_load(content)
    except Exception as exc:
        raise WorkflowDefinitionLoadError(f"Failed to parse YAML content: {exc}") from exc

    if not isinstance(raw, dict):
        raise WorkflowDefinitionLoadError(
            f"Expected YAML object/dict at root, got: {type(raw).__name__}"
        )

    try:
        return WorkflowSpec.model_validate(raw)
    except Exception as exc:
        raise WorkflowDefinitionLoadError(f"Workflow schema validation failed: {exc}") from exc

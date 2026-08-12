from dataclasses import dataclass
from collections.abc import Callable
from typing import Optional

from sqlalchemy.orm import Session

from app.core.feature_flags import is_enabled


@dataclass(frozen=True)
class ToolSpec:
    namespace: str
    name: str
    callable: Callable
    flag_key: Optional[str] = None

    @property
    def qualified_name(self) -> str:
        return f"{self.namespace}.{self.name}"


_registry: dict[str, ToolSpec] = {}


def register(namespace: str, name: str, flag_key: Optional[str] = None):
    def decorator(function: Callable) -> Callable:
        spec = ToolSpec(namespace=namespace, name=name, callable=function, flag_key=flag_key)
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

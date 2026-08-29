from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class ModelInputGuard(Protocol):
    async def prepare_initial_input(
        self, run_context: Mapping[str, Any], raw_input: str
    ) -> str:
        ...

    async def prepare_tool_output(
        self, run_context: Mapping[str, Any], capability_id: str, output: Any
    ) -> Any:
        ...

    async def assert_before_model_call(
        self, run_context: Mapping[str, Any]
    ) -> None:
        ...

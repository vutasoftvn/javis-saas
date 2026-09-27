"""Worker chạy đúng version agent mà authority của Project pin.

Regression PR vutasoftvn/javis-saas#12: nâng spec operations 1.3.0 -> 1.4.0
làm workspace đã kích hoạt trước đó (workspace_agents pin 1.3.0) bị
`spec_hash_mismatch`. Không được tự nâng pin (tự tăng quyền, quy tắc 13) —
chạy đúng bản đã pin từ registry bất biến; không có bản đó thì fail closed.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from agent.registry.models import PublishedSpecRecord
from agent.registry.repository import InMemorySpecRegistryRepository

from apps.cosa.agents.specs import COSA_OPERATIONS_AGENT_SPEC
from apps.cosa.worker.handlers import _spec_for_authority

pytestmark = pytest.mark.asyncio

_OLD = COSA_OPERATIONS_AGENT_SPEC.model_copy(
    update={
        "version": "1.3.0",
        "capability_refs": [
            c
            for c in COSA_OPERATIONS_AGENT_SPEC.capability_refs
            if c != "operations.execution_plan.read"
        ],
        "definition_hash": None,
    }
)


def _pin(spec):
    return SimpleNamespace(id=spec.id, version=spec.version, hash=spec.compute_hash())


async def test_matching_pin_uses_current_spec():
    plane = SimpleNamespace(spec_registry=InMemorySpecRegistryRepository())
    got = await _spec_for_authority(
        plane, COSA_OPERATIONS_AGENT_SPEC, _pin(COSA_OPERATIONS_AGENT_SPEC), run_id="r"
    )
    assert got is COSA_OPERATIONS_AGENT_SPEC


async def test_older_pin_runs_exact_pinned_version_from_registry():
    registry = InMemorySpecRegistryRepository()
    await registry.publish(
        PublishedSpecRecord(
            spec_kind="agent",
            spec_id=_OLD.id,
            version=_OLD.version,
            definition_hash=_OLD.compute_hash(),
            content=_OLD.model_dump(mode="json"),
        )
    )
    got = await _spec_for_authority(
        SimpleNamespace(spec_registry=registry),
        COSA_OPERATIONS_AGENT_SPEC,
        _pin(_OLD),
        run_id="r",
    )
    assert got is not None and got.version == "1.3.0"
    # không tự nhận capability mới của 1.4.0
    assert "operations.execution_plan.read" not in got.capability_refs


async def test_unknown_pin_fails_closed():
    registry = InMemorySpecRegistryRepository()
    bogus = SimpleNamespace(id=_OLD.id, version="1.3.0", hash="deadbeef")
    await registry.publish(
        PublishedSpecRecord(
            spec_kind="agent",
            spec_id=_OLD.id,
            version=_OLD.version,
            definition_hash=_OLD.compute_hash(),
            content=_OLD.model_dump(mode="json"),
        )
    )
    assert (
        await _spec_for_authority(
            SimpleNamespace(spec_registry=registry), COSA_OPERATIONS_AGENT_SPEC, bogus, run_id="r"
        )
        is None
    )

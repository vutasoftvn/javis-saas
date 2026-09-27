from __future__ import annotations

from types import SimpleNamespace

import pytest

from apps.cosa.api.project_context import _WORKSPACE_NAME_CACHE, verify_project_context


class _Client:
    def __init__(self, workspace_resp):
        self._workspace_resp = workspace_resp

    async def get(self, path, headers=None):
        if path.startswith("/operations/projects/"):
            return {"id": "p1", "title": "Miva Core"}
        if isinstance(self._workspace_resp, Exception):
            raise self._workspace_resp
        return self._workspace_resp


@pytest.fixture(autouse=True)
def _clear_workspace_name_cache():
    _WORKSPACE_NAME_CACHE.clear()
    yield
    _WORKSPACE_NAME_CACHE.clear()


def _identity():
    return SimpleNamespace(workspace_id="w1", mint_delegation=lambda: "tok")


@pytest.mark.asyncio
async def test_workspace_name_is_resolved() -> None:
    plane = SimpleNamespace(company_client=_Client({"id": "w1", "name": " Miva "}))
    ctx = await verify_project_context(plane, _identity(), "p1")
    assert ctx.title == "Miva Core" and ctx.workspace_name == "Miva"


@pytest.mark.asyncio
async def test_workspace_name_failure_does_not_break_verification() -> None:
    plane = SimpleNamespace(company_client=_Client(RuntimeError("boom")))
    ctx = await verify_project_context(plane, _identity(), "p1")
    assert ctx.project_id == "p1" and ctx.workspace_name is None


@pytest.mark.asyncio
async def test_workspace_name_is_cached_but_project_is_verified_every_time() -> None:
    client = _Client({"id": "w1", "name": "Miva"})
    calls: list[str] = []
    original = client.get

    async def counting_get(path, headers=None):
        calls.append(path)
        return await original(path, headers=headers)

    client.get = counting_get  # type: ignore[method-assign]
    plane = SimpleNamespace(company_client=client)
    await verify_project_context(plane, _identity(), "p1")
    ctx = await verify_project_context(plane, _identity(), "p1")
    assert ctx.workspace_name == "Miva"
    assert sum(p.startswith("/operations/projects/") for p in calls) == 2
    assert sum(p.startswith("/identity/workspaces/") for p in calls) == 1

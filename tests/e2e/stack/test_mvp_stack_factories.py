from __future__ import annotations

import pytest

from tests.e2e.mvp_stack import MvpStack


def test_from_base_urls_builds_clients() -> None:
    stack = MvpStack.from_base_urls(
        company="http://127.0.0.1:4000",
        platform="http://127.0.0.1:4001",
        agent="http://127.0.0.1:8001",
        apps_cosa="http://127.0.0.1:8001",
        worker_health_url="http://127.0.0.1:8090/live",
    )
    assert stack.company.base_url == "http://127.0.0.1:4000"
    assert stack.uses_mock_transport is False
    assert not hasattr(stack, "migration_versions")


def test_mock_transport_flag_cannot_be_enabled() -> None:
    with pytest.raises(ValueError):
        MvpStack(
            company=MvpStack.from_base_urls(
                company="x", platform="x", agent="x", apps_cosa="x", worker_health_url="x"
            ).company,
            platform=MvpStack.from_base_urls(
                company="x", platform="x", agent="x", apps_cosa="x", worker_health_url="x"
            ).platform,
            agent=MvpStack.from_base_urls(
                company="x", platform="x", agent="x", apps_cosa="x", worker_health_url="x"
            ).agent,
            apps_cosa=MvpStack.from_base_urls(
                company="x", platform="x", agent="x", apps_cosa="x", worker_health_url="x"
            ).apps_cosa,
            worker_health_url="x",
            uses_mock_transport=True,
        )

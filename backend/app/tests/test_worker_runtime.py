import asyncio
from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_run_all_registers_delegation_loop(monkeypatch):
    from app import worker_main

    loops = {
        "chat_loop": AsyncMock(),
        "channel_worker_loop": AsyncMock(),
        "heartbeat_loop": AsyncMock(),
        "execution_loop": AsyncMock(),
        "execution_cleanup_loop": AsyncMock(),
        "delegation_loop": AsyncMock(),
        "mission_resume_loop": AsyncMock(),
    }
    for name, mock in loops.items():
        monkeypatch.setattr(worker_main, name, mock)
    monkeypatch.setattr(worker_main, "_run_background_worker", lambda: None)

    real_gather = asyncio.gather

    async def consume(*awaitables):
        await real_gather(*awaitables)

    monkeypatch.setattr(worker_main.asyncio, "gather", consume)
    await worker_main._run_all()

    for loop in loops.values():
        loop.assert_awaited_once()

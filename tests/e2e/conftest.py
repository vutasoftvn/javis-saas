from __future__ import annotations

import asyncio
import os
import time
from typing import AsyncIterator

import httpx
import jwt as pyjwt
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from apps.cosa.auth.jwt import mint_delegation_token
from apps.cosa.composition.agent_plane import CosaAgentPlane, build_cosa_agent_plane, close_cosa_agent_plane
from agent_testkit.fake_sdk_model import FakeSDKModel

# Default test constants
DEFAULT_PLATFORM_SECRET = "cosa-super-secret-platform-jwt-key-change-in-prod"
DEFAULT_WORKER_SECRET = "cosa-worker-service-jwt-key-change-in-prod-min32chars"

WS_1 = "ws_e2e_alpha"
WS_2 = "ws_e2e_beta"
USER_ALICE_ID = "user_e2e_alice_101"
USER_BOB_ID = "user_e2e_bob_202"


def mint_test_platform_token(
    user_id: str,
    secret: str = DEFAULT_PLATFORM_SECRET,
    aud: str = "cosa",
    ttl_seconds: int = 3600,
) -> str:
    """Tạo JWT platform token chuẩn cho E2E test."""
    payload = {
        "sub": user_id,
        "aud": aud,
        "role": "user",
        "iss": "cosa_platform",
        "exp": int(time.time()) + ttl_seconds,
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")


def mint_test_worker_token(
    worker_id: str = "worker-e2e",
    secret: str = DEFAULT_WORKER_SECRET,
    aud: str = "control_plane",
    ttl_seconds: int = 3600,
) -> str:
    """Tạo JWT worker service token chuẩn."""
    payload = {
        "sub": worker_id,
        "aud": aud,
        "role": "worker_service",
        "iss": "cosa_control_plane",
        "exp": int(time.time()) + ttl_seconds,
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture(scope="session")
def e2e_env():
    """Load and expose environment settings."""
    env = dict(os.environ)
    api_url = env.get("E2E_BASE_URL_API") or env.get("COSA_API_URL") or "http://127.0.0.1:8001"
    cosa_url = env.get("E2E_BASE_URL_COSA") or env.get("COSA_CONTROL_PLANE_URL") or "http://127.0.0.1:4001"
    company_url = env.get("E2E_BASE_URL_COMPANY") or env.get("COMPANY_SERVICE_URL") or "http://127.0.0.1:4000"

    db_agent_core = env.get(
        "AGENT_CORE_DATABASE_URL",
        "postgresql+asyncpg://javis:javis@127.0.0.1:5432/javis",
    )
    db_cosa = env.get(
        "COSA_DATABASE_URL",
        "postgresql://javis:javis@127.0.0.1:5432/cosa_control_plane?sslmode=disable",
    )
    db_company = env.get(
        "COMPANY_DATABASE_URL",
        "postgresql://javis:javis@127.0.0.1:5432/company?sslmode=disable",
    )

    return {
        "api_url": api_url.rstrip("/"),
        "cosa_url": cosa_url.rstrip("/"),
        "company_url": company_url.rstrip("/"),
        "db_agent_core": db_agent_core,
        "db_cosa": db_cosa,
        "db_company": db_company,
        "platform_jwt_secret": env.get("PLATFORM_JWT_SECRET", DEFAULT_PLATFORM_SECRET),
        "worker_jwt_secret": env.get("WORKER_SERVICE_JWT_SECRET", DEFAULT_WORKER_SECRET),
    }


@pytest.fixture
def alice_token(e2e_env):
    return mint_test_platform_token(USER_ALICE_ID, secret=e2e_env["platform_jwt_secret"])


@pytest.fixture
def bob_token(e2e_env):
    return mint_test_platform_token(USER_BOB_ID, secret=e2e_env["platform_jwt_secret"])


@pytest.fixture
def worker_token(e2e_env):
    return mint_test_worker_token("worker-e2e", secret=e2e_env["worker_jwt_secret"])


@pytest_asyncio.fixture
async def e2e_agent_plane(e2e_env) -> AsyncIterator[CosaAgentPlane]:
    """CosaAgentPlane fixture connected to real DB with scheduler."""
    os.environ["COSA_MODEL_PROVIDER"] = "fake"
    from agent_core.coordination.scheduler import RunScheduler
    from agent_core.runs.leases import RunLeaseManager
    from tests.apps.cosa.policy_test_helpers import fake_active_tenant_policy_client

    plane = build_cosa_agent_plane(
        database_url=e2e_env["db_agent_core"],
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        tenant_policy_client=fake_active_tenant_policy_client(workspace_id=WS_1),
        model=FakeSDKModel(),
    )
    from apps.cosa.agents.seed import seed_cosa_agent_specs
    await seed_cosa_agent_specs(plane.spec_registry)
    try:
        yield plane
    finally:
        await close_cosa_agent_plane(plane)


@pytest_asyncio.fixture
async def e2e_http_client(e2e_env, e2e_agent_plane) -> AsyncIterator[httpx.AsyncClient]:
    """HTTP client targeting live container API if reachable, else ASGI in-process app."""
    live_reachable = False
    try:
        async with httpx.AsyncClient(timeout=1.0) as check_client:
            res = await check_client.get(f"{e2e_env['api_url']}/healthz")
            if res.status_code == 200:
                live_reachable = True
    except Exception:
        live_reachable = False

    if live_reachable:
        async with httpx.AsyncClient(base_url=e2e_env["api_url"], timeout=10.0) as client:
            yield client
    else:
        # Fallback to in-process ASGI app with real DB & seeded specs
        from apps.cosa.api.app import create_cosa_app
        from apps.cosa.auth.workspace_client import WorkspaceTenantContextClient
        from apps.cosa.auth.dependency import set_workspace_tenant_context_client

        # Configure workspace client mock transport for in-process tenancy
        def tenant_handler(request: httpx.Request) -> httpx.Response:
            try:
                import json
                body = json.loads(request.content)
                ws_id = body.get("workspaceId", WS_1)
            except Exception:
                ws_id = WS_1
            return httpx.Response(
                200,
                json={
                    "workspaceId": str(ws_id),
                    "userId": USER_ALICE_ID,
                    "membershipRole": "founder",
                    "permissions": ["*"],
                    "correlationId": "corr-e2e",
                },
            )

        mock_tenant_client = WorkspaceTenantContextClient(
            base_url="http://test", transport=httpx.MockTransport(tenant_handler)
        )
        set_workspace_tenant_context_client(mock_tenant_client)

        app = create_cosa_app(plane=e2e_agent_plane)
        transport = httpx.ASGITransport(app=app)
        try:
            async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=10.0) as client:
                yield client
        finally:
            set_workspace_tenant_context_client(None)

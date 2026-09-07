"""Task 5 (plan 2026-09-07-local-first-model-routing) — chứng minh end-to-end
fallback allowlist, compliance deny, CLI cancellation và không rò rỉ
prompt/ciphertext ra telemetry cho toàn bộ tính năng workspace model routing
(Task 1-4).

Nhẹ hơn `tests/e2e/test_local_knowledge_workspace.py` (không cần Encore CLI/
Postgres disposable — xem quyết định trong task-5-report.md): dựng thẳng
`InMemoryModelRoutingRepository`/`InMemoryCredentialRepository` (Task 1/2) +
`ModelRouteResolver`/`ModelProviderFactory` (Task 1/2) THẬT, 1 fake HTTP
server local (http.server, không phải mock của chính resolver/factory) đóng
vai "provider" API, và `CliBridge` (Task 3) THẬT gọi script fixture cục bộ
đóng vai claude/codex/gemini CLI — không bao giờ dùng credential/CLI thật.

KHÔNG mock resolver/factory/compliance — chỉ fake những gì thật sự bên ngoài
tiến trình (HTTP provider, CLI binary), đúng yêu cầu của brief.
"""

from __future__ import annotations

import json
import logging
import os
import stat
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from agents import ModelSettings
from agents.models.interface import ModelTracing

from apps.cosa.compliance.contracts import ComplianceDenied
from apps.cosa.models.cli_bridge import (
    CliBridge,
    CliBridgeModel,
    ModelProviderTimeout,
)
from apps.cosa.models.contracts import (
    ModelRouteNotFound,
    PolicyScope,
    ProfileStatus,
    ProviderType,
    SystemDefaultModelProfile,
)
from apps.cosa.models.credential_store import (
    InMemoryCredentialRepository,
    LocalCredentialStore,
)
from apps.cosa.models.repository import InMemoryModelRoutingRepository
from apps.cosa.models.resolver import ModelRouteResolver
from apps.cosa.models.providers import ModelProviderFactory
from apps.cosa.worker.run_core import (
    RunCoreError,
    prepare_request,
    run_kernel,
)

# litellm giữ 1 `LoggingWorker` global gắn với event loop của lần gọi
# `acompletion()` đầu tiên; pytest-asyncio (function-scoped event loop mặc
# định) tạo loop MỚI mỗi test — lúc teardown, litellm cố `await` lại worker cũ
# trên loop đã đóng và tự log RuntimeWarning. Đây là hành vi nội bộ của
# thư viện litellm khi chạy dưới nhiều event loop ngắn hạn, không liên quan gì
# tới đúng/sai của property đang test (fallback/compliance/CLI/telemetry) —
# filter narrow, chỉ đúng 1 warning message này, để output còn lại vẫn sạch.
pytestmark = pytest.mark.filterwarnings(
    "ignore:coroutine 'Logging.async_success_handler' was never awaited:RuntimeWarning"
)


# ── Fake HTTP provider — đóng vai 1 API provider OpenAI-compatible thật sự
# nhận request qua network cục bộ (KHÔNG mock resolver/factory) ──


class _FakeChatServer:
    """1 server HTTP thật (loopback) trả response Chat Completions tối giản.
    `requests` ghi lại từng request THẬT nhận được — dùng để khẳng định
    "provider X chưa từng nhận request nào" bằng bằng chứng mạng thật, không
    chỉ bằng assertion trên mock."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.requests: list[dict[str, Any]] = []
        outer = self

        class _Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                outer.requests.append(
                    {
                        "path": self.path,
                        "body": json.loads(body.decode("utf-8")),
                        "authorization": self.headers.get("Authorization", ""),
                    }
                )
                resp = {
                    "id": "chatcmpl-fake",
                    "object": "chat.completion",
                    "created": 0,
                    "model": "fake-model",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": f"reply-from-{outer.label}",
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                }
                payload = json.dumps(resp).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                pass

        self._server = HTTPServer(("127.0.0.1", 0), _Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def base_url(self) -> str:
        port = self._server.server_address[1]
        return f"http://127.0.0.1:{port}/v1"

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()


@pytest.fixture
def fake_provider_servers():
    labels = ("provider-a", "provider-b", "provider-c", "external-openai")
    servers = {label: _FakeChatServer(label) for label in labels}
    try:
        yield servers
    finally:
        for server in servers.values():
            server.stop()


# ── Bó tiện ích Task 1/2 thật (không mock) ──


def _system_default() -> SystemDefaultModelProfile:
    return SystemDefaultModelProfile(
        profile_id="system-default",
        provider_type=ProviderType.DEEPSEEK_API,
        model_id="deepseek-chat",
        credential_ref=None,
    )


@dataclass
class RoutingStack:
    routing_repo: InMemoryModelRoutingRepository
    resolver: ModelRouteResolver
    factory: ModelProviderFactory
    credential_store: LocalCredentialStore
    key_file_path: Any


@pytest.fixture
def routing_stack(tmp_path):
    """Fixture nhẹ, KHÔNG cần Encore/Postgres — Task 1 (`InMemoryModelRoutingRepository`)
    + Task 2 (`LocalCredentialStore`/`InMemoryCredentialRepository`, key file
    cục bộ mode 0600 do chính `load_local_secrets_key()` thật tự tạo) +
    `ModelRouteResolver`/`ModelProviderFactory` thật (Task 1/2), không mock
    logic routing/resolve/build-client nào."""
    key_file_path = tmp_path / "local_secrets.key"
    routing_repo = InMemoryModelRoutingRepository()
    credential_store = LocalCredentialStore(InMemoryCredentialRepository(), key_file_path=key_file_path)
    resolver = ModelRouteResolver(repository=routing_repo, system_default=_system_default())
    factory = ModelProviderFactory(credential_store, profile_repository=routing_repo)
    return RoutingStack(
        routing_repo=routing_repo,
        resolver=resolver,
        factory=factory,
        credential_store=credential_store,
        key_file_path=key_file_path,
    )


async def _invoke(model: Any, prompt: str) -> str:
    """Gọi `model.get_response()` — đúng interface `agents.models.interface.Model`
    mà kernel thật dùng, không phải 1 API tự chế riêng cho test — dùng chung
    cho cả `LitellmModel` (API provider) lẫn `CliBridgeModel` (CLI provider)."""
    response = await model.get_response(
        system_instructions=None,
        input=prompt,
        model_settings=ModelSettings(),
        tools=[],
        output_schema=None,
        handoffs=[],
        tracing=ModelTracing.DISABLED,
    )
    return response.output[0].content[0].text


def _spec(agent_spec_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=agent_spec_id,
        spec_id=agent_spec_id,
        to_pinned_identity=lambda: f"{agent_spec_id}@1.0.0#hash",
    )


# ── Property 1: quota exhausted trên primary chỉ được dùng fallback đã duyệt
# tường minh, KHÔNG BAO GIỜ 1 provider không có trong allowlist (dù nó ACTIVE
# và tồn tại thật trong workspace) ──


@pytest.mark.asyncio
async def test_quota_exhausted_primary_falls_over_to_approved_fallback_only(
    routing_stack: RoutingStack, fake_provider_servers
) -> None:
    workspace_id = "ws-fallback"
    agent_spec_id = "cosa.agents.operations"
    servers = fake_provider_servers

    for label in ("provider-a", "provider-b", "provider-c"):
        await routing_stack.routing_repo.create_profile(
            workspace_id,
            label,
            ProviderType.LOCAL_OPENAI_COMPATIBLE,
            base_url=servers[label].base_url,
        )

    # provider-c KHÔNG có trong policy — chỉ provider-b là fallback được duyệt.
    await routing_stack.routing_repo.set_policy(
        workspace_id,
        PolicyScope.AGENT_PROFILE,
        agent_spec_id,
        "provider-a",
        ("provider-b",),
    )

    # Trước khi "hết quota" — primary vẫn được chọn (sanity, chứng minh baseline).
    route_before = await routing_stack.resolver.resolve_route(workspace_id, agent_spec_id)
    assert route_before.profile_id == "provider-a"

    # "Quota exhausted" trong hệ thống này biểu hiện bằng việc profile bị đưa
    # về DISABLED (cơ chế thật duy nhất resolver dùng để loại 1 candidate khỏi
    # vòng chọn — xem apps/cosa/models/resolver.py: chỉ xét status ACTIVE).
    await routing_stack.routing_repo.create_profile(
        workspace_id,
        "provider-a",
        ProviderType.LOCAL_OPENAI_COMPATIBLE,
        base_url=servers["provider-a"].base_url,
        status=ProfileStatus.DISABLED,
    )

    route_after = await routing_stack.resolver.resolve_route(workspace_id, agent_spec_id)
    assert route_after.profile_id == "provider-b"

    client = await routing_stack.factory.create(route_after)
    text = await _invoke(client, "Tóm tắt")
    assert text == "reply-from-provider-b"

    assert len(servers["provider-a"].requests) == 0
    assert len(servers["provider-b"].requests) == 1
    # Khẳng định cốt lõi: provider-c tồn tại, ACTIVE, cùng workspace — nhưng
    # KHÔNG BAO GIỜ nhận request vì không có trong allowlist fallback tường
    # minh của policy. Nếu resolver bị đổi thành "chọn bất kỳ profile ACTIVE
    # nào khác" (bug thật có thể xảy ra), assertion này sẽ fail.
    assert len(servers["provider-c"].requests) == 0
    assert servers["provider-b"].requests[0]["body"]["messages"][-1]["content"] == "Tóm tắt"


@pytest.mark.asyncio
async def test_resolver_fails_closed_when_no_approved_candidate_is_active(
    routing_stack: RoutingStack, fake_provider_servers
) -> None:
    """Không có fallback nào được duyệt + primary bị disable -> fail-closed,
    KHÔNG bao giờ âm thầm rơi về 1 profile khác không nằm trong policy."""
    workspace_id = "ws-fail-closed"
    agent_spec_id = "cosa.agents.operations"
    servers = fake_provider_servers

    await routing_stack.routing_repo.create_profile(
        workspace_id,
        "provider-a",
        ProviderType.LOCAL_OPENAI_COMPATIBLE,
        base_url=servers["provider-a"].base_url,
    )
    # provider-c tồn tại + ACTIVE trong cùng workspace nhưng KHÔNG nằm trong
    # policy (không phải primary, không phải fallback).
    await routing_stack.routing_repo.create_profile(
        workspace_id,
        "provider-c",
        ProviderType.LOCAL_OPENAI_COMPATIBLE,
        base_url=servers["provider-c"].base_url,
    )
    await routing_stack.routing_repo.set_policy(
        workspace_id, PolicyScope.AGENT_PROFILE, agent_spec_id, "provider-a", ()
    )
    await routing_stack.routing_repo.create_profile(
        workspace_id,
        "provider-a",
        ProviderType.LOCAL_OPENAI_COMPATIBLE,
        base_url=servers["provider-a"].base_url,
        status=ProfileStatus.DISABLED,
    )

    with pytest.raises(ModelRouteNotFound):
        await routing_stack.resolver.resolve_route(workspace_id, agent_spec_id)

    assert len(servers["provider-c"].requests) == 0


# ── Property 2: compliance deny -> 0 request tới provider bị từ chối ──


@pytest.mark.asyncio
async def test_compliance_deny_sends_zero_requests_to_denied_provider(
    routing_stack: RoutingStack, fake_provider_servers
) -> None:
    workspace_id = "ws-deny"
    agent_spec_id = "cosa.agents.finance"
    server = fake_provider_servers["external-openai"]

    await routing_stack.routing_repo.create_profile(
        workspace_id, "external-openai", ProviderType.LOCAL_OPENAI_COMPATIBLE, base_url=server.base_url
    )
    await routing_stack.routing_repo.set_policy(
        workspace_id, PolicyScope.AGENT_PROFILE, agent_spec_id, "external-openai", ()
    )

    denying_compliance_resolver = AsyncMock()
    denying_compliance_resolver.resolve_for_run.side_effect = ComplianceDenied("DATA_EGRESS_BLOCKED")

    plane = SimpleNamespace(
        compliance_resolver=denying_compliance_resolver,
        kernel=AsyncMock(),
        model_route_resolver=routing_stack.resolver,
        model_provider_factory=routing_stack.factory,
    )

    with pytest.raises(RunCoreError) as ei:
        prep = await prepare_request(
            plane,
            spec=_spec(agent_spec_id),
            run_id="r-deny",
            prompt="Dữ liệu nội bộ",
            principal="founder_1",
            workspace_id=workspace_id,
            conversation_id="c1",
            policy_snapshot=None,
        )
        # Nếu prepare_request không raise (bug), dòng dưới mới chạm run_kernel —
        # cố tình để lộ ngay nếu ordering compliance-trước-routing bị phá vỡ.
        await run_kernel(plane, prep, workspace_id=workspace_id, run_id="r-deny")

    assert ei.value.reason_code == "compliance_denied"
    assert ei.value.compliance_code == "DATA_EGRESS_BLOCKED"
    # Khẳng định chính bằng bằng chứng MẠNG THẬT — không chỉ "hàm chưa được
    # gọi" mà "server chưa từng nhận byte nào".
    assert server.requests == []


@pytest.mark.asyncio
async def test_prepare_request_then_run_kernel_reaches_approved_provider_over_real_http(
    monkeypatch, routing_stack: RoutingStack, fake_provider_servers
) -> None:
    """Đối chứng dương cho test deny ở trên — cùng 1 profile/route/plane
    shape, chỉ đổi compliance_resolver từ deny sang approve, để chứng minh
    request=0 ở test trên là DO compliance chặn thật, không phải do fixture
    không bao giờ có khả năng gửi request tới server này."""
    workspace_id = "ws-allow"
    agent_spec_id = "cosa.agents.finance"
    server = fake_provider_servers["external-openai"]

    await routing_stack.routing_repo.create_profile(
        workspace_id, "external-openai", ProviderType.LOCAL_OPENAI_COMPATIBLE, base_url=server.base_url
    )
    await routing_stack.routing_repo.set_policy(
        workspace_id, PolicyScope.AGENT_PROFILE, agent_spec_id, "external-openai", ()
    )

    approving_compliance_resolver = AsyncMock()
    approving_compliance_resolver.resolve_for_run.return_value = {
        "_company_delegation_token": "tok-approve-1"
    }

    plane = SimpleNamespace(
        compliance_resolver=approving_compliance_resolver,
        kernel=AsyncMock(),  # không dùng — route không phải system-default
        model_route_resolver=routing_stack.resolver,
        model_provider_factory=routing_stack.factory,
        repository=object(),
        spec_registry=object(),
        capability_registry=object(),
        gateway=object(),
        policy_engine=object(),
        company_client=object(),
    )

    prep = await prepare_request(
        plane,
        spec=_spec(agent_spec_id),
        run_id="r-allow",
        prompt="Tóm tắt doanh thu quý",
        principal="founder_1",
        workspace_id=workspace_id,
        conversation_id="c1",
        policy_snapshot=None,
    )

    def _fake_build_execution_kernel(**kwargs):
        model = kwargs["model"]
        fake_kernel = AsyncMock()

        async def _run(req, spec):
            text = await _invoke(model, req.input["prompt"])
            return SimpleNamespace(status="completed", final_output={"response": text})

        fake_kernel.run.side_effect = _run
        return fake_kernel, "compliance-resolver-unused-in-this-fake"

    monkeypatch.setattr(
        "apps.cosa.composition.kernel_factory.build_execution_kernel",
        _fake_build_execution_kernel,
    )

    result, _duration = await run_kernel(plane, prep, workspace_id=workspace_id, run_id="r-allow")

    assert result.status == "completed"
    assert result.final_output["response"] == "reply-from-external-openai"
    assert len(server.requests) == 1
    assert server.requests[0]["body"]["messages"][-1]["content"] == "Tóm tắt doanh thu quý"


# ── Property 3: 3 CLI provider claude/codex/gemini + timeout kill process
# group thật, qua entry point Model interface thật (Task 3) ──


def _make_executable(path, content: str) -> None:
    path.write_text(content)
    mode = os.stat(path).st_mode
    os.chmod(path, mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture
def cli_fixtures(tmp_path):
    claude = tmp_path / "fake-claude-cli"
    codex = tmp_path / "fake-codex-cli"
    gemini_hang = tmp_path / "fake-gemini-cli"
    pidfile = tmp_path / "gemini-grandchild.pid"

    _make_executable(claude, '#!/bin/sh\nread -r line\nprintf "claude-reply:%s" "$line"\n')
    _make_executable(codex, '#!/bin/sh\nread -r line\nprintf "codex-reply:%s" "$line"\n')
    # Bỏ qua SIGTERM + spawn 1 grandchild `sleep` — cùng kỹ thuật đã chứng
    # minh trong tests/apps/cosa/models/test_cli_bridge.py (Task 3), tái dùng
    # ở đây qua entry point cao hơn (CliBridgeModel, không phải CliBridge trần).
    _make_executable(
        gemini_hang,
        "#!/bin/sh\ntrap '' TERM\nsleep 100 &\necho $! > '" + str(pidfile) + "'\nwait\n",
    )
    return {
        "claude": str(claude),
        "codex": str(codex),
        "gemini": str(gemini_hang),
        "gemini_pidfile": pidfile,
    }


@pytest.mark.asyncio
async def test_cli_providers_claude_and_codex_exercised_through_provider_factory(
    monkeypatch, tmp_path, cli_fixtures, caplog
) -> None:
    monkeypatch.setenv("COSA_CLI_CLAUDE_PATH", cli_fixtures["claude"])
    monkeypatch.setenv("COSA_CLI_CODEX_PATH", cli_fixtures["codex"])
    monkeypatch.setenv("COSA_CLI_GEMINI_PATH", cli_fixtures["gemini"])

    cli_bridge = CliBridge(
        allowlist={
            cli_fixtures["claude"]: (),
            cli_fixtures["codex"]: (),
            cli_fixtures["gemini"]: (),
        }
    )

    workspace_id = "ws-cli"
    routing_repo = InMemoryModelRoutingRepository()
    credential_store = LocalCredentialStore(
        InMemoryCredentialRepository(), key_file_path=tmp_path / "cli-key"
    )
    factory = ModelProviderFactory(
        credential_store, profile_repository=routing_repo, cli_bridge=cli_bridge
    )
    resolver = ModelRouteResolver(repository=routing_repo, system_default=_system_default())

    await routing_repo.create_profile(
        workspace_id, "profile-claude", ProviderType.CLAUDE_CLI, model_id="claude-cli-default"
    )
    await routing_repo.create_profile(
        workspace_id, "profile-codex", ProviderType.CODEX_CLI, model_id="codex-cli-default"
    )
    await routing_repo.set_policy(
        workspace_id, PolicyScope.AGENT_PROFILE, "cosa.agents.operations", "profile-claude"
    )
    await routing_repo.set_policy(
        workspace_id, PolicyScope.AGENT_PROFILE, "cosa.agents.finance", "profile-codex"
    )

    caplog.set_level(logging.DEBUG)

    route_claude = await resolver.resolve_route(workspace_id, "cosa.agents.operations")
    client_claude = await factory.create(route_claude)
    text_claude = await _invoke(client_claude, "prompt-cho-claude\n")
    assert text_claude == "claude-reply:prompt-cho-claude"

    route_codex = await resolver.resolve_route(workspace_id, "cosa.agents.finance")
    client_codex = await factory.create(route_codex)
    text_codex = await _invoke(client_codex, "prompt-cho-codex\n")
    assert text_codex == "codex-reply:prompt-cho-codex"

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "prompt-cho-claude" not in log_text
    assert "prompt-cho-codex" not in log_text


@pytest.mark.asyncio
async def test_cli_gemini_timeout_kills_real_process_group_through_model_interface(
    cli_fixtures,
) -> None:
    """`ModelProviderFactory._create_cli_client()` không expose tham số
    timeout theo route (hardcode timeout_seconds mặc định của
    `CliBridgeModel` = 120s — quá dài cho 1 test) — dựng thẳng
    `CliBridgeModel` với timeout ngắn, vẫn đi qua đúng entry point Model
    interface thật (`get_response()`) mà kernel thật dùng, không hạ cấp
    xuống gọi `CliBridge.invoke()` trần."""
    cli_bridge = CliBridge(allowlist={cli_fixtures["gemini"]: ()})
    model = CliBridgeModel(
        cli_bridge,
        executable=cli_fixtures["gemini"],
        model_id="gemini-1.5",
        profile_id="profile-gemini",
        # 2.0s (không phải giá trị rất nhỏ như 0.6s) — chừa đủ headroom cho
        # shell fixture fork "sleep 100 &" + ghi pidfile TRƯỚC khi bị SIGKILL,
        # tránh flaky khi máy đang bận (nhiều subprocess khác trong cùng
        # session test vừa chạy trước đó tranh CPU/scheduler).
        timeout_seconds=2.0,
    )

    with pytest.raises(ModelProviderTimeout):
        await _invoke(model, "prompt-cho-gemini")

    pidfile = cli_fixtures["gemini_pidfile"]
    grandchild_pid: int | None = None
    for _ in range(50):
        if pidfile.exists():
            content = pidfile.read_text().strip()
            if content:
                grandchild_pid = int(content)
                break
        time.sleep(0.05)
    assert grandchild_pid is not None, "grandchild pid was never written by fixture script"

    for _ in range(50):
        try:
            os.kill(grandchild_pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)
    else:
        pytest.fail(f"grandchild pid {grandchild_pid} still alive after process-group kill")


# ── Property 4: local secrets key file được tạo mode 0600 (điều kiện Makefile
# target dựa vào) ──


def test_local_secrets_key_file_is_created_with_mode_0600(routing_stack: RoutingStack) -> None:
    mode = stat.S_IMODE(os.stat(routing_stack.key_file_path).st_mode)
    assert mode == 0o600


# ── Property 5: mock telemetry/provenance không chứa prompt hay ciphertext,
# cho cả CLI provider lẫn API provider ──


@pytest.mark.asyncio
async def test_route_provenance_and_logs_never_contain_prompt_or_ciphertext(
    monkeypatch, tmp_path, routing_stack: RoutingStack, fake_provider_servers, cli_fixtures, caplog
) -> None:
    """`apps/cosa/worker/run_core.py::_route_provenance()` là hàm THẬT dùng để
    xây `RunRequest.model_policy` — persist tới telemetry/audit
    (`RunRecord.model_policy`). Test này resolve route + build client THẬT
    (1 API provider có credential mã hoá, 1 CLI provider) rồi kiểm cả (a)
    provenance dict thật không chứa prompt/credential field nào, và (b) log
    output THẬT phát sinh trong lúc gọi provider không chứa plaintext
    prompt/secret/ciphertext nào."""
    from apps.cosa.worker.run_core import _route_provenance

    workspace_id = "ws-telemetry"
    server = fake_provider_servers["external-openai"]

    secret_plaintext = "sk-test-FAKE-not-a-real-key-1234567890"  # pragma: allowlist secret
    from pydantic import SecretStr

    credential_ref = (
        await routing_stack.credential_store.put(workspace_id, SecretStr(secret_plaintext))
    ).id
    stored_ciphertext = await routing_stack.credential_store._repo.raw_ciphertext_for_test(
        credential_ref
    )

    await routing_stack.routing_repo.create_profile(
        workspace_id,
        "external-openai",
        ProviderType.LOCAL_OPENAI_COMPATIBLE,
        base_url=server.base_url,
        credential_ref=credential_ref,
    )
    await routing_stack.routing_repo.set_policy(
        workspace_id, PolicyScope.AGENT_PROFILE, "cosa.agents.finance", "external-openai", ()
    )

    caplog.set_level(logging.DEBUG)
    prompt_marker = "noi-dung-bi-mat-cua-workspace-khong-duoc-lo"

    api_route = await routing_stack.resolver.resolve_route(workspace_id, "cosa.agents.finance")
    api_client = await routing_stack.factory.create(api_route)
    api_text = await _invoke(api_client, prompt_marker)
    assert api_text == "reply-from-external-openai"
    # Credential THẬT được dùng (chứng minh decrypt hoạt động) — Authorization
    # header của request THẬT phải mang đúng plaintext đã lưu.
    assert server.requests[-1]["authorization"] == f"Bearer {secret_plaintext}"

    api_provenance = _route_provenance(api_route)
    api_provenance_text = json.dumps(api_provenance)
    assert prompt_marker not in api_provenance_text
    assert secret_plaintext not in api_provenance_text
    assert stored_ciphertext not in api_provenance_text
    assert credential_ref not in api_provenance_text  # provenance chỉ chứa profile_id/provider_type/model_id

    # CLI provider — cùng property, không có credential nhưng phải không rò
    # prompt qua provenance/log.
    monkeypatch.setenv("COSA_CLI_CLAUDE_PATH", cli_fixtures["claude"])
    cli_bridge = CliBridge(allowlist={cli_fixtures["claude"]: ()})
    cli_factory = ModelProviderFactory(
        routing_stack.credential_store, profile_repository=routing_stack.routing_repo, cli_bridge=cli_bridge
    )
    await routing_stack.routing_repo.create_profile(
        workspace_id, "profile-claude", ProviderType.CLAUDE_CLI, model_id="claude-cli-default"
    )
    await routing_stack.routing_repo.set_policy(
        workspace_id, PolicyScope.AGENT_PROFILE, "cosa.agents.operations", "profile-claude"
    )
    cli_route = await routing_stack.resolver.resolve_route(workspace_id, "cosa.agents.operations")
    cli_client = await cli_factory.create(cli_route)
    cli_text = await _invoke(cli_client, f"{prompt_marker}\n")
    assert cli_text == f"claude-reply:{prompt_marker}"

    cli_provenance = _route_provenance(cli_route)
    cli_provenance_text = json.dumps(cli_provenance)
    assert prompt_marker not in cli_provenance_text

    # Chỉ xét log THẬT do chính COSA phát ra (namespace `apps.cosa.*` — nơi
    # `redact_provider_payload`/`redact_sensitive_text` áp dụng) — không xét
    # log DEBUG nội bộ của thư viện bên thứ 3 (litellm/openai SDK). Phát hiện
    # thật trong lúc build test này: `litellm` ở log level DEBUG tự in
    # nguyên văn `messages=[...]` (bao gồm prompt) ra log của CHÍNH NÓ, không
    # đi qua bất kỳ redaction nào của COSA — đây là hành vi của thư viện bên
    # thứ 3, KHÔNG PHẢI rò rỉ từ code apps/cosa, nhưng vẫn là rủi ro vận hành
    # thật nếu ai đó bật LiteLLM ở mức DEBUG trong production và forward log
    # đó ra ngoài. Đã ghi rõ thành known limitation trong
    # docs/operations/model-routing-runbook.md — KHÔNG bao giờ bật DEBUG log
    # cho litellm ở production/staging.
    cosa_log_text = "\n".join(
        record.getMessage() for record in caplog.records if record.name.startswith("apps.cosa")
    )
    assert prompt_marker not in cosa_log_text
    assert secret_plaintext not in cosa_log_text
    assert stored_ciphertext not in cosa_log_text

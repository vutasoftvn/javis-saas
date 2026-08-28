# PART SEARCH — capability `web.search` (Tavily production adapter)

**Ngày:** 2026-08-28
**Phần của:** [marketingskills-makerskills-program](../integrations/2026-08-28-marketingskills-makerskills-program.md) · §5
**Nhánh đề xuất:** `msmk/part-search-web-search`
**Phụ thuộc:** PART 0

## Context

`web.search` được khai báo bởi `skillpacks/marketing/market-research/manifest.yaml`,
`skillpacks/marketing/seo-plan/manifest.yaml`, và recipe
`packages/agent_recipes/research/research-synthesize/recipe.yaml` +
`packages/agent_recipes/sales/competitor-intelligence/recipe.yaml` — nhưng **chưa đăng ký** trong
`apps/cosa/composition/agent_plane.py` (`build_cosa_agent_plane()` chỉ có `operations.task.list`,
`operations.task.read`, `finance.payout.execute`, `finance.transaction.record`, sandbox MCP).
`docs/development/add-capability.md` tự ghi nhận gap này.

Part SEARCH định nghĩa `web.search` là capability **read-only, workspace-scoped**, có allowlist +
quota/budget + sanitize + provenance + audit, đăng ký tường minh trong `build_cosa_agent_plane()`.
Provider trừu tượng hoá; **Tavily là adapter production thật** (`WEB_SEARCH_PROVIDER=tavily` mặc
định), đổi provider được qua env.

## Pattern tái dùng

- Capability SPEC + handler factory: `apps/cosa/capabilities/operations_read.py`
  (`OPERATIONS_TASK_LIST_SPEC = CapabilitySpec(id=..., risk=CapabilityRisk.LOW, input_schema=...)`,
  `create_operations_task_list_handler(client)` trả `async def handle(payload, ctx)`).
- `CapabilitySpec` / `CapabilityRisk` / `ApprovalPolicy`: `packages/agent_core/contracts/capability.py`,
  `packages/agent_core/governance/contracts.py`.
- Gateway pipeline (idempotency, readiness, policy, audit): `packages/agent_core/capabilities/gateway.py`.
- Audit event: `self._repo.append_event(RunEventRecord(run_id=..., event_type="tool.requested", ...))`.
- Env fail-fast staging/prod: mẫu `services/*/shared/env.ts` (`isStagingOrProd()` throw).
- `WorkspaceArtifact`: `packages/agent_core/artifacts/models.py` (kind `report`, `object_ref`
  `object://`/`artifact://`).

## Danh sách file + thay đổi

### SEARCH.1 Adapter interface + Tavily thật

| File (mới) | Nội dung |
| --- | --- |
| `packages/agent_core/capabilities/web_search/__init__.py` | export `WebSearchProvider`, `WebSearchResult`, `build_web_search_provider`, `NullWebSearchProvider`, `TavilyWebSearchProvider`. |
| `packages/agent_core/capabilities/web_search/provider.py` | `class WebSearchProvider(Protocol)`: `async def search(query: str, *, max_results: int, allow_domains: list[str] \| None, deny_domains: list[str] \| None) -> list[WebSearchResult]`. `WebSearchResult` (pydantic): `url`, `title`, `snippet`, `published_at: datetime \| None`, `raw_excerpt: str` (đã sanitize), `provider: str`, `retrieved_at: datetime`. `NullWebSearchProvider` → trả `[]`. `build_web_search_provider()` đọc `WEB_SEARCH_PROVIDER` (`tavily` default) → dispatch; provider lạ → `ValueError`. |
| `packages/agent_core/capabilities/web_search/tavily.py` | `TavilyWebSearchProvider(api_key, *, base_url, timeout)`: gọi Tavily `/search` qua `httpx.AsyncClient`; map field → `WebSearchResult`; retry/timeout/backoff (`tenacity`, tôn trọng `Retry-After`); áp `allow_domains`/`deny_domains` (lọc post-response nếu API không hỗ trợ). Key qua env `TAVILY_API_KEY`; thiếu ở staging/prod → raise (mẫu `isStagingOrProd`), ở dev → cảnh báo + fallback `NullWebSearchProvider`. |

### SEARCH.2 Capability spec + handler + quota

| File | Thay đổi |
| --- | --- |
| `apps/cosa/capabilities/web_search.py` (mới) | `WEB_SEARCH_SPEC = CapabilitySpec(id="web.search", name="Web Search", risk=CapabilityRisk.LOW, approval_policy=ApprovalPolicy.NEVER, idempotency_semantics="payload_deterministic", input_schema={type:object, required:[query], properties:{query:string, max_results:integer, allow_domains:array, deny_domains:array}}, output_schema={type:object, properties:{results:array, provider:string, retrieved_at:string}}, audit_policy={...})`. `create_web_search_handler(provider, *, workspace_policy_client, budget_store)` → `async def handle(payload, ctx)`: (1) resolve `workspace_id` từ `ctx`; (2) áp workspace allow/deny domain policy (từ `workspace_policy_client`); (3) `budget_store.check_and_consume(workspace_id, cost=1)` — vượt → raise lỗi mã `QUOTA_EXCEEDED`; (4) `provider.search(...)`; (5) sanitize `raw_excerpt` (strip `<script>/<style>`, giới hạn ~4KB), gắn nhãn `untrusted: true`, mỗi item kèm `source_url` + `retrieved_at`; (6) trả `{results, provider, retrieved_at}`. |
| `packages/agent_core/capabilities/web_search/budget.py` (mới) | `WebSearchBudgetStore` protocol + `InMemoryWebSearchBudgetStore` + `PostgresWebSearchBudgetStore` (bảng `agent_web_search_budget`: `workspace_id`, `window_start`, `query_count`, `cost_accumulated`, `daily_query_cap`, `daily_cost_cap`). `check_and_consume` atomic; default cap từ config (`WEB_SEARCH_DAILY_QUERY_CAP`, `WEB_SEARCH_DAILY_COST_CAP`). |
| `apps/cosa/composition/agent_plane.py` | Trong `build_cosa_agent_plane()`, sau các `cap_registry.register(...)` hiện có: `from apps.cosa.capabilities.web_search import WEB_SEARCH_SPEC, create_web_search_handler` + `cap_registry.register(WEB_SEARCH_SPEC, create_web_search_handler(build_web_search_provider(), workspace_policy_client=tenant_policy, budget_store=<postgres nếu resolved_url, else in-memory>))`. |
| `packages/agent_core/knowledge/models.py` / migrations | Thêm migration bảng `agent_web_search_budget`. |

### SEARCH.3 Web evidence artifact

| File | Thay đổi |
| --- | --- |
| `apps/cosa/capabilities/web_search.py` | Tuỳ chọn (flag `WEB_SEARCH_WRITE_EVIDENCE`): sau search, ghi `WorkspaceArtifact` kind `report` chứa raw snapshot + metadata provenance (`source_url`, `retrieved_at`, `confidence=unknown`, `trust=unreviewed`, `sensitivity=public`) qua `artifact_repository`. Part B2/B3 dùng lại làm evidence candidate. |

### SEARCH.4 Test

| File (mới) | Ca kiểm |
| --- | --- |
| `tests/apps/cosa/test_agent_plane_web_search.py` | `build_cosa_agent_plane(... , model=FakeSDKModel())` expose `web.search` (`plane.capability_registry.get("web.search")` không None). Handler: domain ngoài `allow_domains` bị loại; `QUOTA_EXCEEDED` khi vượt `budget_store`; payload có `untrusted:true` + `source_url` mỗi item; audit event `tool.web_search` (hoặc `tool.requested` với capability=`web.search`) được append. |
| `tests/agent_core/capabilities/web_search/test_tavily.py` | Map response Tavily (fixture JSON, **sandbox** — không gọi mạng thật trong CI); retry khi 429 + `Retry-After`; timeout → lỗi rõ; `NullWebSearchProvider` trả `[]`. |
| `tests/apps/cosa/test_agent_plane_skillpack_boundary.py` | Cập nhật `expected_capability_count` từ 5 → 6; danh sách assert thêm `"web.search"`. |
| `scripts/validate_skillpacks.py` whitelist | Gỡ `web.search` khỏi `KNOWN_PENDING_CAPABILITIES` (giờ đã đăng ký) — pack khai `web.search` không còn là exception. |

## Verify

```text
python -m pytest tests/apps/cosa/test_agent_plane_web_search.py tests/agent_core/capabilities/web_search -q
python -m pytest tests/apps/cosa/test_agent_plane_skillpack_boundary.py -q      # count = 6
WEB_SEARCH_PROVIDER=null python -m pytest tests/apps/cosa -q                    # plane vẫn build được không key
python scripts/validate_skillpacks.py                                          # web.search không còn whitelist
```

## Definition of Done

- [ ] `WebSearchProvider` protocol + `TavilyWebSearchProvider` thật (retry/timeout/backoff) + `NullWebSearchProvider`.
- [ ] `build_web_search_provider()` chọn provider theo `WEB_SEARCH_PROVIDER` (`tavily` default); thiếu key ở staging/prod → fail-fast.
- [ ] `WEB_SEARCH_SPEC` (`risk=LOW`, `approval_policy=NEVER`, `idempotency=payload_deterministic`) đăng ký tường minh trong `build_cosa_agent_plane()`.
- [ ] Handler áp workspace allow/deny domain + quota/budget per-workspace (`agent_web_search_budget`), vượt → `QUOTA_EXCEEDED`.
- [ ] Payload trả về gắn nhãn untrusted + `source_url` + `retrieved_at` mỗi item; audit event phát ra; không log full query khi sensitivity cao.
- [ ] `test_agent_plane_web_search.py` + `test_tavily.py` (sandbox) xanh; `test_agent_plane_skillpack_boundary.py` count = 6, xanh.
- [ ] `web.search` gỡ khỏi validator whitelist; pack khai `web.search` pass rule tool-đã-đăng-ký.
- [ ] Chưa pin `web.search` vào SkillSpec nào (việc đó ở Part B2).

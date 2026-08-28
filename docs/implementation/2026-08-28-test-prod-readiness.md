# Test + Prod Readiness — Master Plan

**Ngày:** 2026-08-28
**Trạng thái:** Đề xuất, chia 2 milestone / 13 part giao dần
**Phạm vi rà soát:** nhánh `remediation/dev-readiness-remaining` @ 2026-08-28 (đã đi trước `main` ~301 file / 24k dòng)
**Tham chiếu:**
- [`2026-08-27-dev-readiness-remediation.md`](./2026-08-27-dev-readiness-remediation.md)
- [`2026-08-28-dev-readiness-remediation-remaining.md`](./2026-08-28-dev-readiness-remediation-remaining.md)
- `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md` (nguồn sự thật cao nhất) §29
- [`coverage-baseline-2026-08-28.md`](./coverage-baseline-2026-08-28.md)
- [`readiness-reporting-standard.md`](./readiness-reporting-standard.md)

---

## 1. Context — vì sao có kế hoạch này

Câu hỏi khởi phát: *"Phân tích toàn diện codebase và đề xuất điều chỉnh, bổ sung để tiến tới test và prod."*

Rà soát cho thấy Phases 0–7 của `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25` đã complete, và nhánh hiện tại còn land thêm nhiều khối lớn **chưa merge vào `main`**:

| Khối đã land trên nhánh | Bằng chứng |
| --- | --- |
| Dev-readiness remediation Parts 1–4 | commit `adff857b`; 7 service commercial+finance-legal đã đưa `workspaceId` vào WHERE (`services/company/commercial/services/customer.service.ts:76`); workflow empty-spec → `FAILED` (`packages/agent_core/workflows/{schema,engine}.py`); DEV DSN gỡ khỏi runtime source; Flutter `task_service.dart` hardening; `scripts/check_doc_links.py`, `scripts/load-dev-env.sh` |
| Event-driven agent operating model P0→P2 + closeout 6 gap | transactional outbox; local relay + intake; trigger governance gate trên eval/promotion evidence; **event backbone metrics endpoint**; durable hierarchical supervisor + child-task edges |
| Exec-plane split | execution plane loopback fail-fast vs platform control plane VPS |
| Pluggable `EmbeddingProvider` + pgvector semantic search | `packages/agent_core/knowledge/{embedding,retrieval,store}.py`; vẫn có lexical fallback khi `NotImplementedError` |
| Cross-process crash-recovery test THẬT + stuck-task sweeper | `tests/apps/cosa/worker/test_crash_recovery_subprocess.py` (`@pytest.mark.integration`, spawn `encore run` + 2 OS process + SIGKILL); endpoint `/control-plane/internal/scheduled-tasks/reclaim-stuck` + fencing token |

**Kết luận:** phần lớn "điều chỉnh code" đã có; việc còn lại là **làm cho test gate đáng tin** rồi **đủ điều kiện cutover prod có kiểm soát**.

## 2. Quyết định đã chốt với người dùng

| Câu hỏi | Quyết định |
| --- | --- |
| Deliverable | Assessment + kế hoạch thực thi (bộ doc này), chưa code |
| "Test và prod" nghĩa là gì trước | Cả hai, **theo thứ tự**: staging + test gate trước, prod cutover ngay sau |
| Verify durability qua process thật (2 OS process + Postgres thật, lease `FOR UPDATE`, checkpoint/resume có tool) | **Blocker phải đóng** trong phạm vi này |
| Ưu tiên đầu | Tenant isolation (Part 1) — *nhưng đã land trên nhánh*, nên ưu tiên đầu chuyển sang **Part 0 reconciliation + Part 1C durability** |

## 3. Bảng gap còn mở

| # | Hạng mục | Bằng chứng gap | Part |
| --- | --- | --- | --- |
| 1 | Không có Python quality gate | Repo không có `pyproject.toml` / `ruff` / `mypy` / `pre-commit` / `pytest-cov`; TS chỉ có `tsc --noEmit` | 1A |
| 2 | `packages/agent_integrations/*` (15 adapter) — 0 unit test | Chỉ conformance ở `packages/agent_testkit/` | 1B |
| 3 | Kernel checkpoint/resume không chạy end-to-end | `RealOpenAIAgentsSDKKernel` chưa truyền `tools` cho model API → tool call không sinh → checkpoint không kích hoạt (Phase 7 known gap) | 1B |
| 4 | Durability chưa chứng minh qua CI | `test_crash_recovery_subprocess.py` tồn tại nhưng chưa xác nhận xanh ổn định; lease `FOR UPDATE` mới test trên pglite | 1C |
| 5 | Không có full-stack E2E golden path | E2E-1..3,5,6,7 chỉ ngầm qua job lẻ; chỉ E2E-4 (SSE restart) là test thật | 1D |
| 6 | Worker không có health/readiness endpoint | `apps/cosa/worker/` không expose `/live` `/ready` | 1E |
| 7 | Compose chưa fail-closed, image `:latest` | `deploy/central_vps/docker-compose.yaml`, `docker-compose.yml`: thiếu `${VAR:?}`; minio/livekit/opensandbox chưa pin tag | 1E |
| 8 | Không có schema fingerprint gate (Migration Gate D) | `migrations.md` §29.6 — design only | 1F |
| 9 | Rollback path gãy | legacy `brain-api`: `ModuleNotFoundError: No module named 'full_main'` (`docs/operations/rollback_pre_cutover.md`) | 2A |
| 10 | `.down.sql` chưa test (Migration Gate E) | `docs/operations/migrations.md` | 2A |
| 11 | Observability chưa wire | OTel SDK trong deps, chưa init; chưa có runtime metrics (token/cost/approval latency); `/events/metrics` handler chưa xác nhận đăng ký | 2B |
| 12 | Defense-in-depth tenancy | Python execution plane không cross-check `workspace_id` với `services/company/identity`; `list_approvals` chỉ filter `workspace_id` | 2C |
| 13 | Chưa chốt deploy infra prod | `deploy/k8s/` chỉ có OpenSandbox; `deploy/central_vps` compose chỉ có Postgres | 2D |
| 14 | DR chưa diễn tập | `docs/operations/disaster-recovery.md` tồn tại, chưa chạy thật; sweeper chưa có cron trigger | 2E |
| 15 | Phần hoãn chưa có quyết định chính thức | Conversation history port còn stub; không có runtime agent registration API | 2F |
| 16 | `services/company` typecheck đỏ (4 lỗi) | Part 0 phát hiện: `task-events.service.ts` / `task.service.ts` — 4 type error; `services/company npm run typecheck` fail | 1A (kèm) |
| 17 | `make check-docs` đỏ | Part 0: 10 link hỏng tới doc TPR — **tự khỏi khi bộ doc này đủ 14 file**; verify lại | 0 / 1F |

## 4. Hai milestone

### Milestone 1 — Test gate đáng tin + staging
| Part | Nội dung | File chi tiết |
| --- | --- | --- |
| 0 | Reconciliation — **ĐÃ THỰC HIỆN** (@ `44835086`): items 1/2/3/6/8 VERIFIED+PROD-READY; item 4 (semantic) VERIFIED-PARTIAL cần pgvector live; item 5 (`/events/metrics`) đăng ký OK nhưng `services/company` typecheck đỏ 4 lỗi; **khuyến nghị CHƯA MERGE** vào `main` cho tới khi: (a) fix typecheck `services/company`, (b) doc links xanh, (c) durability chạy với live DB | [part0](./2026-08-28-tpr-part0-reconciliation.md) |
| 1A | Python quality gate (ruff/mypy/pre-commit/coverage + CI job) | [part1a](./2026-08-28-tpr-part1a-python-quality-gate.md) |
| 1B | Đóng gap test coverage (adapters + kernel checkpoint/resume) | [part1b](./2026-08-28-tpr-part1b-test-coverage-gaps.md) |
| 1C | Verify durability qua process thật (BLOCKER) | [part1c](./2026-08-28-tpr-part1c-durability-verification.md) |
| 1D | Full-stack E2E golden path (E2E-1..7) | [part1d](./2026-08-28-tpr-part1d-e2e-golden-path.md) |
| 1E | Dựng staging (worker health, compose fail-closed, pin image) | [part1e](./2026-08-28-tpr-part1e-staging-bringup.md) |
| 1F | CI hardening (doc-links, schema fingerprint Gate D) | [part1f](./2026-08-28-tpr-part1f-ci-hardening.md) |

> **Cổng merge nhánh → `main`** (Part 0 đã chốt 3 điều kiện): (a) `services/company npm run typecheck` xanh — fix 4 lỗi `task-events.service.ts` / `task.service.ts` (làm trong 1A); (b) `make check-docs` xanh — đủ 14 file TPR; (c) Part 1C durability chạy xanh với live Postgres/Encore. Cộng thêm 1A gate cơ bản.

### Milestone 2 — Sẵn sàng cutover production
| Part | Nội dung | File chi tiết |
| --- | --- | --- |
| 2A | Rollback path + Migration Gate E | [part2a](./2026-08-28-tpr-part2a-rollback-path.md) |
| 2B | Observability (OTel, runtime metrics, structured log) | [part2b](./2026-08-28-tpr-part2b-observability.md) |
| 2C | Security / tenancy defense-in-depth + secrets | [part2c](./2026-08-28-tpr-part2c-security-tenancy.md) |
| 2D | Quyết định + hoàn thiện deploy infra prod + Migration Gate G | [part2d](./2026-08-28-tpr-part2d-deploy-infra.md) |
| 2E | Data safety / DR + sweeper cron | [part2e](./2026-08-28-tpr-part2e-data-safety-dr.md) |
| 2F | Hoãn nhưng ghi quyết định (ADR / ticket) | [part2f](./2026-08-28-tpr-part2f-deferred-decisions.md) |

**Deferred — quyết định chính thức:** bảng hợp nhất (mỗi mục có ADR/ticket + điều kiện re-open) tại [`readiness-reporting-standard.md` §4](./readiness-reporting-standard.md#4-deferred--quyết-định-chính-thức-không-chặn-go-live). Gồm: conversation history (ADR-CONV-001), agent registration API (ADR-AGENT-REG-001), evidence-scoring weights (POST-LAUNCH-OPS-001), manual tool loop kernel (ADR-RUNTIME-002), và Part 2C.2 `list_approvals`/`company_id` (đóng bởi migration 017).

## 5. Thứ tự thực thi

```
Part 0 → 1A → 1C (blocker) → 1B → 1D → [merge nhánh vào main] → 1E → 1F
       → 2A → 2B → 2C → 2D → 2E → 2F
```

1A/1C/1B song song được sau Part 0. Milestone 2 chạy tuần tự hơn (2A trước 2D; 2B trước go-live).

## 6. Verification tổng (end-to-end)

1. **Local:** `make verify` + `make lint` + coverage gate xanh.
2. **CI:** job `e2e-golden-path` xanh trên compose stack ephemeral; job `durability` xanh (crash-recovery 2 process thật + lease Postgres thật); job `schema-fingerprint` xanh sau `migrate-all`; job `doc-links` xanh.
3. **Staging:** full stack up qua compose profile; `scripts/e2e/run-golden-path.sh` pass; worker `/ready` xanh; mọi health endpoint không lộ secret/DSN.
4. **Prod:** `make deploy-preflight` pass; `migrate-all` qua đúng đường prod; smoke test (auth → dispatch → SSE → result); diễn tập rollback/restore một lần và document.

## 7. Non-goals (kế thừa doc gốc §11)

- Không khôi phục legacy backend làm runtime.
- Không broad-activate skillpack runtime.
- Không rewrite đồng loạt frontend / thêm route giả.
- Không chạy destructive integration test trên DB development/shared.
- Không đổi secret production ngoài phần 2C đã mô tả.

## 8. Quy ước báo cáo

Theo [`readiness-reporting-standard.md`](./readiness-reporting-standard.md): mọi tuyên bố "done/green" phải kèm **lệnh kiểm tra + ngày + commit**. 5 trục trạng thái (ACCEPTED / IMPLEMENTED / WIRED / VERIFIED / PRODUCTION) là độc lập.

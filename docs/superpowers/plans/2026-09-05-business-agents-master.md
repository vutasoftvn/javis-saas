# Kế hoạch triển khai tổng thể business và agents — overview 07 + 08

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Khắc phục toàn bộ phát hiện F01–F16 và khép vòng strategy → thực thi → kết quả → review, với chu kỳ N tuần, Cas.so/QR founder thanh toán và quyền thống nhất.

**Architecture:** Company/TypeScript giữ dữ liệu và quyết định nghiệp vụ; COSA phân phối chính sách và điều phối; Python thực thi qua gateway; Flutter hiển thị trạng thái thật. Giữ các cơ chế registry pin, outbox, approval và WorkforceMember hiện có, sửa từng đường xuyên lớp trước khi mở rộng tự động hóa.

**Tech Stack:** Encore.ts, TypeScript, Drizzle/PostgreSQL, Python/Pydantic/pytest, Flutter/GetX, Vitest; Cas.so và adapter QR.

**Spec:** [Overview 07](/Volumes/SSD/javis-saas/docs/architecture/overview/07-code-audit-business-agents-2026-09-05.md), [Overview 08](/Volumes/SSD/javis-saas/docs/architecture/overview/08-phan-tich-cycle-cas-permissions-2026-09-05.md). Hai bản là đầu vào phân tích, không chứng minh implementation đã tồn tại. Khi khác nhau, yêu cầu mới của founder trong 08 quyết định thiết kế cycle và payout; mọi nhận định hiện trạng phải kiểm lại code.

## Global Constraints

- Phạm vi “cả hai overview” là 07 và 08; không tự mở phạm vi tài liệu 06 chưa được giao trong chuỗi này.
- “Dùng phương pháp 12WY làm mẫu tổ chức thực thi; mô hình sản phẩm là chu kỳ N tuần do founder chọn.”
- “Không cần triển khai agent tự chuyển tiền cho phạm vi này.”
- “Một bảng permissions hoặc chỉ dẫn trong prompt riêng lẻ không đủ.”
- Làm trực tiếp ở `/Volumes/SSD/javis-saas`, nhánh main; không tạo worktree. Không sửa/xóa thay đổi sẵn có của người khác.
- Một identity WorkforceMember cho người và AI. Snowflake qua JSON là string; không di chuyển ID dữ liệu hiện hữu sang kiểu khác trong đợt này.
- Company service kiểm quyền, tenant và trạng thái; handler không query DB. Agent không ghi business DB trực tiếp.
- Approval giữ binding run_id + tool_call_id + checkpoint_ref; bổ sung resource version/hash. Quyết định đã yêu cầu approval không tự mất khi policy được nới.
- Migration release chỉ Expand; không đổi checksum migration cũ, không drop/rename phá tương thích. Không chuyển toàn bộ framework kế toán hoặc runtime.
- Contract mới cập nhật `shared/contracts/mvp-surface.json` và sinh client theo generator hiện có. Không hand-edit file generator-owned.
- Code hiện tại là Encore/Drizzle, không áp ví dụ FastAPI/SQLAlchemy lỗi thời trong rule full-stack. Mỗi tính năng phải đi hết DTO → service → API → Flutter state → UI → test.
- Plan chưa cho phép gửi email/chat, trả tiền thật, nộp hồ sơ hoặc deploy production. Sandbox/provider readiness và rollout là các bước có đầu ra kiểm chứng riêng.

---

## 1. Cấu trúc plan và thứ tự phụ thuộc

| Plan | Task | Kết quả độc lập |
|---|---|---|
| [A — quyền và governance](/Volumes/SSD/javis-saas/docs/superpowers/plans/2026-09-05-business-agents-permissions.md) | A1–A4 | Tenant guard đúng; founder quản lý quyền; agent bị kiểm tại mỗi lần thực thi |
| [S — strategy và operating](/Volumes/SSD/javis-saas/docs/superpowers/plans/2026-09-05-business-agents-strategy-operating.md) | S1–S5 | Gate có evidence; cycle N tuần, OKR, cam kết và review dùng dữ liệu thật |
| [R — agent runtime](/Volumes/SSD/javis-saas/docs/superpowers/plans/2026-09-05-business-agents-runtime.md) | R1–R4 | Event chạy qua worker; Copilot đúng auth/output; knowledge và readiness thật |
| [L — legal](/Volumes/SSD/javis-saas/docs/superpowers/plans/2026-09-05-business-agents-legal.md) | L1–L3 | Applicability theo pháp nhân; approver đúng quyền; nghĩa vụ có vòng đời |
| [F — finance, Cas và QR](/Volumes/SSD/javis-saas/docs/superpowers/plans/2026-09-05-business-agents-finance.md) | F1–F6 | Sổ/đối soát an toàn; Cas thật; chi QR; TT58 có mapping và UI thực |
| Plan tổng này | H0, H1 | Môi trường test cô lập; kiểm thử xuyên các phần và rollout có kiểm soát |

Thứ tự một người thực hiện: **H0 → A1 → A2 → A3 → A4 → R1 → R2 → L1 → L2 → S1 → S2 → S3 → S4 → S5 → L3 → F1 → F2 → F3 → F4 → F5 → F6 → R3 → R4 → H1**. Có thể tách phần guard/conditional update/currency của F1 thành bản vá sớm sau A1; phần migration mở rộng theo chuỗi L1–L3 rồi F1–F6. Đánh số task chỉ dùng nhận diện, không yêu cầu chạy theo alphabet.

Các nhánh có thể triển khai độc lập nếu sau này được phân công: sau A1, F1 và R1/R2 không phụ thuộc UI permissions; sau A2/A3, S2/S3 và Cas F2/F3 không chia sẻ logic nghiệp vụ. File schema/index, contracts và migration sequence vẫn cần một người tích hợp để tránh ghi đè. Không tự tạo task/agent mới chỉ vì sơ đồ có nhánh.

### Ma trận bao phủ hai overview

| Nguồn | Task nhận trách nhiệm | Bằng chứng đóng hạng mục |
|---|---|---|
| F01 tenant weekly review/action proposal | A1 | Workspace B không đọc/sửa được ID của A; không có outbox phụ |
| F02 quyền sửa policy | A1, A2–A4 | Auditor bị chặn ở service; founder sửa policy có version/audit |
| F03 evidence và edge W-stage | S1 | Candidate/expired bị loại; edge denied luôn chặn |
| F04 event→worker | R1, R4 | Producer thật → scheduler → worker, retry không tạo run phụ |
| F05 Copilot prefetch auth | R2 | Read qua gateway; token đúng hướng; context tới model |
| F06 completion giả | R2, R4 | FAILED không callback completed; artifact lỗi không thành công |
| F07 khóa kỳ | F1 | Posting/confirm/void không ghi vào kỳ đã khóa |
| F08 đối soát cạnh tranh | F1, F4 | Hai connection DB tranh cùng tiền không phân bổ vượt số dư |
| F09 currency | F1, F6 | Không cộng VND+USD; tiền và burn đúng nguồn |
| F10 tuần 1 | S2 | Chọn tuần 2 không ghi đè tuần 1 |
| F11 UI 12WY stub | S5 | Reload vẫn có dữ liệu; chọn project đúng |
| F12 PMF | S1 | Không approved evidence không PROMISING; score hiểu metric |
| F13 assumption mẫu | S4 | Thay context thật làm recommendation đổi; thiếu dữ liệu trả lý do |
| F14 kickoff changed | S2 | Giữ action ID, đổi nội dung cập nhật task đúng version |
| F15 legal enum/applicability | L1, L3, S4 | OPEN/VERIFIED được evaluate theo từng pháp nhân |
| F16 deployment founder giả | A1, L2 | Member tự tạo deployment không tự thành approver |
| 07: project gate→decision→execution | S1, S4 | Decision giữ evaluation/evidence/policy version, bind khi transition |
| 07: Definition of done và rollup | S3, R2, R4 | Run completed chưa tự đóng task; score có evidence |
| 07: budget actual/committed/forecast | F6, S4 | Payment request và bank allocation không cộng đôi |
| 07: capability readiness, knowledge, marketing | R3 | Tool đủ theo skill; nguồn tri thức/project/CRM có provenance |
| 07: autopilot/takeover/durable eval | R4 | Test handler/gateway thật, restart process thật |
| 08: N tuần, horizon OKR, review | S2, S3, S5 | 2/6/12/16 tuần; nhiều cycle phục vụ KR; không tuần 13 bắt buộc |
| 08: Cas Link, GET, webhook, grant | F2, F3 | Contract provider đã chốt; đồng bộ bù thiếu; revoke dừng sync |
| 08: chi QR do founder chuyển | F4, F6 | Approval gắn nội dung; QR không đánh PAID; đối soát phần còn lại |
| 08: TT58 theo pháp nhân/kỳ | F5, L1 | Mapping có nguồn; BCTC đối chiếu số liệu; không áp đại trà |
| 08: permissions cho người/AI | A2–A4, L2, F4 | Role/scope/policy/grant/approval cùng được enforce |

## 2. Hợp đồng chung giữa các plan

Các tên sau là giao diện **đề xuất mới**, không khẳng định có sẵn:

```ts
type Effect = "ALLOW" | "DENY" | "REQUIRE_APPROVAL";
type ResourceScope = { workspaceId: string; projectId?: string; legalEntityId?: string };
type Money = { minor: string; currency: string };
type ResourceVersion = { id: string; version: number };
type RuleDecision = {
  effect: Effect; reasonCodes: string[]; policyVersion: number;
  matchedRuleIds: string[]; approvalRequired: boolean;
};
```

A2 định nghĩa permission/action catalog và `authorizeBusinessAction(ctx, action, scope, facts): Promise<RuleDecision>`; service gọi `requireBusinessAction` để chặn hoặc yêu cầu approval. A3 đưa decision có version tới runtime. S2 là chủ của `cycleId/weekNo`; S3 là chủ observation/score; S4 là chủ action context tổng hợp. F3 tạo canonical bank transaction; F4 là chủ payment request và allocation; F5 là chủ posting/report mapping; L1 là chủ applicability decision theo entity. Không để model sinh các cờ authorization hoặc ghi PAID.

Lỗi nghiệp vụ qua APIError kèm code ổn định trong response contract: `PERMISSION_DENIED`, `APPROVAL_REQUIRED`, `VERSION_CONFLICT`, `INSUFFICIENT_DATA`, `PROVIDER_NOT_READY`, `REAUTH_REQUIRED`, `PERIOD_CLOSED`, `ALLOCATION_EXCEEDED`. Flutter xử lý theo code, không parse câu chữ. HTTP mapping theo Encore: permissionDenied/failedPrecondition/aborted/unavailable/invalidArgument; xác nhận enum thực tế của SDK trước khi thêm adapter.

## 3. H0 — Harness kiểm thử và chuẩn bị migration

**Files:** tạo [run_business_audit_tests.py](/Volumes/SSD/javis-saas/scripts/run_business_audit_tests.py), [test_business_audit_runner.py](/Volumes/SSD/javis-saas/tests/e2e/stack/test_business_audit_runner.py); tái sử dụng [disposable_postgres.py](/Volumes/SSD/javis-saas/tests/e2e/stack/disposable_postgres.py), [Makefile](/Volumes/SSD/javis-saas/Makefile). Không sửa password/env dev để làm test pass.

**Interfaces:** CLI `.venv/bin/python scripts/run_business_audit_tests.py company|cosa <vitest-file>...`; tạo cluster mới ngẫu nhiên, migrate Agent→COSA→Company, subprocess chạy Vitest với URL disposable, truyền nguyên exit code, teardown trong finally. Từ chối service lạ và đường test ra ngoài service root. Không in URL/secret.

- [ ] Viết test runner bằng monkeypatch subprocess/cluster: nonzero exit vẫn teardown; đầu vào `../` bị chặn; tất cả URL con là disposable. Chạy `.venv/bin/python -m pytest tests/e2e/stack/test_business_audit_runner.py -q`, ban đầu FAIL vì thiếu runner.
- [ ] Triển khai runner theo lifecycle sau, với validation service/file trước khi tạo DB:

```python
cluster = create_disposable_cluster(secrets.token_hex(8))
try:
    apply_migrations(cluster)
    child_env = dict(os.environ)
    child_env.update(
        WORKSPACE_DATABASE_URL=cluster.workspace_app_url,
        COSA_DATABASE_URL=cluster.cosa_app_url,
        AGENT_DATABASE_URL=cluster.agent_app_url,
    )
    result = subprocess.run(
        ["npx", "vitest", "run", *test_files],
        cwd=repo_root / "services" / service,
        env=child_env,
        check=False,
    )
finally:
    drop_disposable_cluster(cluster)
```

- [ ] Chạy runner với `company operations/tests/okr-scoring.test.ts`; chứng minh cluster mới, test chạy, DB được dọn. Nếu admin Postgres/Encore thiếu, trả lỗi rõ; không fallback sang DB dev hay gọi skip rồi báo pass.
- [ ] Chốt migration sequence theo cây code lúc thực thi. Baseline hiện thấy identity 7, operations 40, finance-legal 31, COSA 30; tên đề xuất trong plan là sequence kế tiếp. Nếu có migration mới từ công việc khác, tăng sequence của file chưa áp dụng trước khi merge; không renumber migration đã chạy.
- [ ] Chạy test runner unit và test disposable hiện có; review diff; commit riêng `test: isolate business audit integration runs` sau khi test pass.

**Quy ước lệnh trong các task:** `DBTEST company <file>` là viết tắt cho CLI runner vừa định nghĩa, chạy từ repository root. `PYTEST <file>` là `AGENT_DATABASE_URL= COSA_DATABASE_URL= DATABASE_URL= PYTHONPATH=.:packages/agent .venv/bin/python -m pytest <file> -q` cho unit tests dùng dependency giả; test durability/DB phải dùng cluster riêng, không lệnh unit này. `FLUTTER <file>` là `flutter test <file>` tại `/Volumes/SSD/javis-saas/frontend`. Đây là ký hiệu trong plan, không phải lệnh shell có sẵn.

## 4. Migration và tương thích

1. Thêm cột nullable/bảng mới, writer/reader hiểu cả dữ liệu cũ và mới; feature mặc định chưa bật. Mọi backfill có dry-run đếm theo workspace và idempotent checkpoint.
2. Không tự gán owner, baseline KR, pháp nhân hay người nhận nếu thiếu bằng chứng. Đưa vào trạng thái cần cấu hình; hiển thị trên UI. Rule pháp lý cũ giữ source/version và bản hiệu chỉnh mới.
3. Policy mới: backfill từ nguồn cũ theo quy tắc A2/A3, so sánh quyết định, rồi chuyển writer về một nguồn. Giới hạn hard deny và quyền command đã sửa vẫn luôn enforce trong giai đoạn chuyển đổi.
4. Worker chạy hỗn hợp: envelope/schema có version; không deploy producer mới trước consumer tương thích. Pin AgentSpec/skill đồng bộ hash.
5. Rollback ứng dụng giữ schema Expand. Tắt writer mới nhưng tiếp tục nhận bank inbox/reconcile dữ liệu đã phát sinh; không drop payment request, observation, journal hoặc approval. Không rollback quyền về phiên bản còn lỗ hổng F01/F02/F16.

Gate thay schema: `make migration-compat-check`, chạy migration hai lần trên disposable DB, thử app N-1 với schema mới cho các route giữ tương thích; chỉ cập nhật fingerprint bằng `make schema-fingerprint-write` sau khi inspect schema đúng. Gate code: typecheck service bị sửa, relevant tests, `make company-boundary-check`, `make encore-handler-boundary-check`, `make ts-suppression-check`; route Flutter chạy thêm `make frontend-api-contract-check`, `make mvp-contracts-check`.

## 5. H1 — E2E nghiệp vụ và nghiệm thu

**Files:** tạo [test_business_operating_loop.py](/Volumes/SSD/javis-saas/tests/e2e/test_business_operating_loop.py), [business_operating_loop.dart](/Volumes/SSD/javis-saas/frontend/integration_test/business_operating_loop.dart); tái sử dụng [subprocess_stack.py](/Volumes/SSD/javis-saas/tests/e2e/stack/subprocess_stack.py), [mvp_stack.py](/Volumes/SSD/javis-saas/tests/e2e/mvp_stack.py). Tạo [business-agents-release.md](/Volumes/SSD/javis-saas/docs/testing/business-agents-release.md) làm checklist evidence khi thực thi.

**Consumes:** A1–A4, S1–S5, R1–R4, L1–L3, F1–F6. **Produces:** kết quả từng F01–F16, migration/backfill evidence, UI walkthrough và danh sách tính năng được bật.

- [ ] Viết scenario dữ liệu cố định: workspace A/B, founder/auditor/finance agent; project A, KR 5 pilot, cycle 6 tuần; tuần 2, nghĩa vụ OPEN; đề nghị chi 1.500.000 VND. Seed qua public/internal API đúng quyền, không chèn bypass vào service business trong E2E.
- [ ] Chạy luồng HTTP + worker thật: giao việc → run → artifact → task validation → review; kiểm KR chưa đạt nếu chưa có pilot evidence. Mô phỏng provider transport Cas, giữ parser/ingestion/service thật. Assert request APPROVED vẫn UNPAID trước bank evidence; duplicate webhook + GET chỉ một transaction/allocation.
- [ ] Chạy các nhánh âm: workspace B truy cập tài nguyên A; auditor sửa quyền; revoke khi run chờ duyệt; target/beneficiary đổi version; accounting period đóng; stale evidence; provider mất kết nối; retry sau restart; founder takeover autopilot. Mỗi nhánh kiểm cả response và DB/outbox, không chỉ status HTTP.
- [ ] Flutter test desktop/mobile: chọn project/cycle → lưu/reload → weekly review; Cas Link success/cancel/reauth; request QR approved/partial/paid; permissions simulation/save/conflict. Loading/error/empty/pending thể hiện inline, không báo thành công khi server chưa persist.
- [ ] Chạy relevant suites và `make e2e-cross-plane-smoke`; test mới có marker cross_plane phải được chạy tường minh thêm bằng `.venv/bin/python -m pytest tests/e2e/test_business_operating_loop.py -m cross_plane -q`. Test subprocess không có DB/Encore phải FAIL preflight, không silently skip.
- [ ] Review ma trận bao phủ; điền checklist release bằng log/artifact thực. Commit `test: verify founder operating loop across business and agents` khi mọi gate liên quan pass.

**Điều kiện bật tính năng:** không còn bypass tenant/permission; không báo completed/PAID giả; migration/backfill không mất dữ liệu; KR/weekly không ghi đè lịch sử; Cas sandbox xác nhận contract; bộ TT58 có source và expected report được review. Bật theo workspace: permissions → cycle/weekly → read-only bank sync → payment request/QR → report đã verify → tăng autonomy có giới hạn. Chưa có evidence thì UI trả trạng thái chưa khả dụng, không dùng dữ liệu mẫu.

**Các đầu vào bên ngoài cần thu thập trong lúc thực thi:** Cas sandbox client/grant, cơ chế xác thực webhook production và ngân hàng/scopes được hỗ trợ (F2); toàn văn/phụ lục chế độ kế toán và bộ số kiểm chứng được reviewer chuyên môn xác nhận (F5). Thiếu đầu vào chỉ giữ tính năng tương ứng chưa bật; vẫn thực hiện các task code độc lập. Plan không tự giả lập chúng thành điều kiện đã đạt.

## 6. Theo dõi tiến độ

Mỗi task báo: trạng thái chưa làm/đang làm/đã kiểm chứng; commit; test command + kết quả; migration; phát hiện audit đã đóng; giới hạn còn lại. Một test unit pass không tự đóng hạng mục cần Postgres/cross-process/provider contract. Không dùng 77 test pass của audit 07 làm bằng chứng cho code mới.

Kế hoạch này được lập từ code và hai overview; mọi checkbox hiện chưa thực hiện. Ước lượng lịch chỉ lập sau H0/A1 và F2 discovery có số liệu về hạ tầng/provider; không cam kết thời gian bằng giả định chưa kiểm chứng.

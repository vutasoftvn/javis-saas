# PHẦN 2 — Workflow spec rỗng + P0 residual (DEV DSN)

**Ngày:** 2026-08-28
**Phần của:** [dev-readiness-remediation-remaining](./2026-08-28-dev-readiness-remediation-remaining.md) · doc gốc §8 + §4
**Nhánh đề xuất:** `remediation/part2-workflow-and-p0-residual`
**Phụ thuộc:** không (song song được với PHẦN 1)

## Context

Hai fix nhỏ, độc lập, gộp chung một nhánh:

- **2a.** `WorkflowSpec._validate_dag()` (commit `dd6185d6`) đã reject cycle / dangling dep /
  dup id / bad `on_failure`/`compensate_with`, nhưng **chưa** reject spec `steps=[]` hoặc spec
  mà mọi step đều là compensation target. Khi đó `_execute_dag()` có `forward_steps == []`,
  vòng `while 0 < 0` không chạy, không rơi vào nhánh fail-safe (nhánh đó chỉ bắt "còn forward
  step nhưng không step nào ready"), và cuối hàm `transition(WorkflowStatus.COMPLETED)` với
  `completed_steps == []` → success giả.
- **2b.** DEV DSN có `user:password` vẫn nằm inline trong runtime source (doc gốc §4 tiêu chí
  "Không còn DSN có username/password runtime trong source tracked").

---

## 2a. Workflow spec rỗng / không có forward step

### File

- `packages/agent_core/workflows/schema.py` — `WorkflowSpec._validate_dag` (~L65-123).
- `packages/agent_core/workflows/engine.py` — `_execute_dag` (~L196-302).
- `tests/agent_core/workflows/test_dag_validation.py` — mở rộng.

### Thay đổi schema.py

Trong `_validate_dag`, thêm ở đầu (sau khi tính `step_ids`, `compensation_targets`):

```python
if len(self.steps) == 0:
    raise ValueError("WorkflowSpec has no steps")

compensation_targets = {s.on_failure for s in self.steps if s.on_failure}
forward_steps = [s for s in self.steps if s.id not in compensation_targets]
if not forward_steps:
    raise ValueError(
        "WorkflowSpec has no forward steps: every step is a compensation target"
    )
```

(Đưa phần tính `compensation_targets` lên trước; nhánh check "forward depends_on compensation
target" ở cuối hàm dùng lại biến này, không tính lại.)

### Thay đổi engine.py (fail-safe tầng engine)

Trong `_execute_dag`, ngay sau khi tính `forward_steps` (~L207), trước vòng `while`:

```python
if not forward_steps:
    workflow.error = (
        "workflow has no forward steps (empty spec or all-compensation spec "
        "bypassed schema validation)"
    )
    workflow.transition(WorkflowStatus.FAILED)
    return workflow
```

Không được để rơi xuống `transition(WorkflowStatus.COMPLETED)`.

### Test (`test_dag_validation.py`)

- `test_empty_spec_rejected` — `WorkflowSpec(name=..., steps=[])` → `ValidationError` (message chứa "no steps").
- `test_all_compensation_spec_rejected` — spec 1 forward + 1 step chỉ là `on_failure` target của
  nó, rồi bỏ forward → chỉ còn compensation → `ValidationError`.
- `test_engine_rejects_empty_forward_via_model_construct` — dựng spec bypass validate
  (`model_construct`) với `forward_steps` rỗng, chạy engine → `WorkflowStatus.FAILED`, **không**
  `COMPLETED`, `completed_steps == []`.
- `test_completed_implies_all_forward_steps_done` — với spec hợp lệ chạy xong: assert
  `set(workflow.completed_steps) >= {s.id for s in forward_steps}` khi status `COMPLETED`.
- Giữ nguyên toàn bộ test cycle / dangling / dup / parallel / approval / compensation hiện có.

### Verify 2a

```text
.venv/bin/pytest tests/agent_core/workflows -q
```

---

## 2b. Chuyển DEV DSN ra khỏi runtime source

### File

- `services/cosa/storage/client.ts` — `DEV_COSA_DB_URL` (L7-8, chứa
  `cosa_central_admin:SecureCentralPass2026`), `resolveCosaDatabaseUrl` (L10-20).
- `services/company/shared/db/client.ts` — `DEV_COMPANY_DB_URL` (chứa `cosa:cosa`),
  `resolveCompanyDatabaseUrl`.
- `.env.example`, `services/.env.example` — bổ sung biến nếu thiếu.
- Test: `services/cosa/tests/`, `services/company/tests/`.

### Thay đổi

1. Xoá hằng DSN đầy đủ có credential. `resolve*DatabaseUrl()` trở thành: yêu cầu env var ở
   **mọi** environment; thiếu → `throw new Error("COSA_DATABASE_URL (hoặc CONTROL_PLANE_DATABASE_URL) is required; set it in .env for local dev")` (nêu tên biến, **không** log giá trị).
   Giữ nhánh `isStagingOrProd()` với message riêng nếu muốn phân biệt, nhưng không còn fallback DSN.
2. `DEFAULT_COSA_DB_URL` / tham số mặc định `getOrCreatePool(connectionString = DEFAULT_...)` giữ
   nguyên chữ ký — chỉ nguồn giá trị đổi (từ env, không từ hằng credential).
3. Local dev: `.env` / bootstrap (PHẦN 4) cấp `COSA_DATABASE_URL`, `COMPANY_DATABASE_URL`.
   `.env.example` liệt kê 2 biến với placeholder không đăng nhập được
   (`postgresql://USER:PASSWORD@127.0.0.1:5434/cosa?sslmode=disable`).
4. Test cần DB: fixture đặt `process.env.COSA_DATABASE_URL` / `COMPANY_DATABASE_URL` trỏ Postgres
   disposable **trước** khi import module client (fixture có tên rõ ràng trong `tests/`), không
   phụ thuộc default runtime.

### Test 2b

- `services/cosa/tests/db-url-resolution.test.ts` (mới): `resolveCosaDatabaseUrl` throw khi
  `COSA_DATABASE_URL` và `CONTROL_PLANE_DATABASE_URL` đều trống — ở `development`, `staging`,
  `production`; message chứa tên biến, không chứa chuỗi giống DSN.
- Tương tự `services/company/tests/db-url-resolution.test.ts`.
- Xác nhận `grep -rn "cosa_central_admin:SecureCentralPass2026\|cosa:cosa@" services/ --include=*.ts`
  chỉ còn khớp trong `tests/` (nếu có) — không còn trong source runtime.

### Verify 2b

```text
cd services/cosa && npm run typecheck && npm test
cd services/company && npm run typecheck && npm test
```

---

## Definition of Done (ánh xạ doc gốc §8 + §4)

- [ ] Spec `steps=[]` và spec toàn compensation bị reject ở validation với lỗi tường minh.
- [ ] Engine không bao giờ trả `COMPLETED` khi `forward_steps` rỗng (fail-safe → `FAILED`).
- [ ] Có assertion: workflow `COMPLETED` ⇒ mọi forward step nằm trong `completed_steps`.
- [ ] Test cycle / dangling / DAG hợp lệ / approval / compensation hiện có vẫn xanh.
- [ ] Không còn DSN có `username:password` trong source runtime tracked (chỉ còn trong `tests/` nếu cần).
- [ ] `resolve*DatabaseUrl()` fail nêu tên biến, tuyệt đối không log giá trị secret.
- [ ] `.env.example` có `COSA_DATABASE_URL` + `COMPANY_DATABASE_URL` với placeholder không đăng nhập được.
- [ ] `pytest tests/agent_core/workflows`, `services/cosa` + `services/company` typecheck & test xanh.

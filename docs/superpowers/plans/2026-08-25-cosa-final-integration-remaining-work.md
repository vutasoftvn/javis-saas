# COSA Final Integration — Remaining Work Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the gaps listed in `COSA_FINAL_INTEGRATION_EXECUTION_STATUS_2026-08-25.md` §3 ("Việc cần làm tiếp theo") now that Docker, Encore CLI, real Postgres (`cosa_postgres`, healthy), and `DEEPSEEK_API_KEY`/`OPENAI_API_KEY` are available in this environment — none of these were available in the session that wrote that document.

**Architecture:** No new architecture — this plan only *verifies with real infrastructure* what earlier phases implemented and simulated with `pglite`/mocks, then performs one controlled deployment cutover (Phase 8) and prepares (but does not execute) the final `legacy/` removal (Phase 10 stays blocked until this plan's Task 7 checklist is 100%).

**Tech Stack:** Postgres 16 (`pgvector/pgvector:pg16`, container `cosa_postgres`), Encore CLI v1.58.2, Docker Compose, Python 3.11 (`apps/cosa`), Node (`services/cosa`, `services/company`), pytest, vitest (via `encore test`).

## Global Constraints

- Mọi thay đổi hành vi phải có test tương ứng; chạy test trước khi báo cáo hoàn thành (CLAUDE.md #11).
- `git status` trước bất kỳ thao tác nào có thể mất dữ liệu (CLAUDE.md #10); không `--force`/`--no-verify`.
- Không tự ý xóa `legacy/` hay bỏ mount `legacy/backend` khỏi các service production-critical mà không xác nhận với người dùng trước khi thực thi bước đó cụ thể (tài liệu gốc Phase 8 đã tự flag rủi ro này — Task 6 dưới đây thực hiện dạng "song song rồi mới cutover", không xóa ngay).
- Trạng thái ACCEPTED/IMPLEMENTED/WIRED/VERIFIED/PRODUCTION là 5 trục khác nhau — mỗi task dưới đây phải đạt VERIFIED bằng lệnh thật, không chỉ đọc code (CLAUDE.md, mục "Trạng thái ACCEPTED...").
- Backup trước migration đổi PK/constraint hiện có nếu DB đã có data thật (`docs/operations/migrations.md` mục "Trước khi chạy trên Postgres thật"). Trong môi trường dev hiện tại DB mới khởi động (`cosa_postgres` "Up 5 seconds" lúc kiểm tra) nên rủi ro thấp, nhưng vẫn xác nhận bằng `\dt` trước khi migrate.

---

### Task 1: Chạy migration thật trên Postgres thật (baseline_v1 + agent_core)

**Files:**
- Không tạo/sửa file code — chỉ chạy migration đã có sẵn:
  - `services/cosa/migrations/1_baseline_identity_and_agent_policy.up.sql` (+ các migration `2`-`9` sau baseline nếu có)
  - `services/company/identity/migrations/1_baseline_workspace_user_workforce.up.sql` (+ migration của `commercial`/`finance-legal`/`operations`)
  - `packages/agent_core/migrations/*.sql` (tới `011_run_stream_events.sql`)
- Nếu phát hiện lỗi migration thật (khác với kết quả `pglite` đã verify): sửa file migration tương ứng, KHÔNG sửa test giả định.

**Interfaces:**
- Không có interface code mới — output là state DB thật để Task 2-4 dùng.

- [ ] **Step 1: Xác nhận DB rỗng/an toàn**

```bash
docker exec -it cosa_postgres psql -U javis -d javis -c "\dt cosa.*" 2>&1 | head -5
docker exec -it cosa_postgres psql -U javis -d javis -c "\dt core.*" 2>&1 | head -5
```
Expected: `Did not find any relation` hoặc bảng rỗng (DB mới khởi động, chưa có identity/agent_policy schema).

- [ ] **Step 2: Xác nhận role/database phụ đã tồn tại cho company + control-plane**

`services/company/scripts/migrate.mjs` dùng `COMPANY_DATABASE_URL || DATABASE_URL` (đã set = `postgresql://javis_app:...@postgres:5432/javis`); `services/cosa/scripts/migrate.mjs` dùng `COSA_DATABASE_URL || CONTROL_PLANE_DATABASE_URL` (đã set). Kiểm tra role `javis_app` và `cosa_control_plane_app` đã tồn tại trong container (compose không có init script tạo role phụ ngoài `POSTGRES_USER=javis`):

```bash
docker exec -it cosa_postgres psql -U javis -d javis -c "\du" 2>&1
```

Nếu thiếu role `javis_app`/`cosa_control_plane_app` hoặc database `cosa_control_plane`: tạo thủ công (dev-only, không phải bước bí mật — password lấy từ giá trị fallback trong `docker-compose.yml`/`.env`):

```bash
docker exec -it cosa_postgres psql -U javis -d javis -c "
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'javis_app') THEN
    CREATE ROLE javis_app LOGIN PASSWORD 'change-me-javis-app';
  END IF;
END \$\$;"
docker exec -it cosa_postgres psql -U javis -d javis -c "GRANT ALL ON DATABASE javis TO javis_app;"
docker exec -it cosa_postgres psql -U javis -d javis -c "
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'cosa_control_plane_app') THEN
    CREATE ROLE cosa_control_plane_app LOGIN PASSWORD 'change-me-control-plane-app';
  END IF;
END \$\$;"
docker exec -it cosa_postgres psql -U javis -d javis -c "SELECT 1 FROM pg_database WHERE datname='cosa_control_plane'" | grep -q 1 || \
  docker exec -it cosa_postgres psql -U javis -d javis -c "CREATE DATABASE cosa_control_plane OWNER cosa_control_plane_app;"
```

- [ ] **Step 3: Chạy migrate cho cả 3 hệ**

```bash
cd /Volumes/SSD/javis-saas
make services-migrate-cosa
make services-migrate-company
make migrate-agent-platform
```

- [ ] **Step 4: Verify kết quả khớp con số đã verify qua pglite**

```bash
docker exec -it cosa_postgres psql "$CONTROL_PLANE_DATABASE_URL" -c "\dt cosa.*" | wc -l   # kỳ vọng khớp 9 bảng (Phase 1 pglite: cosa 9 bảng)
docker exec -it cosa_postgres psql "$DATABASE_URL" -c "\dt core.*" -c "\dt agent_core.*" | wc -l
```
Ghi lại số bảng thật vào commit message ở Step 5 — nếu lệch số với `docs/operations/migrations.md` (50 bảng company full-stack, 9+12 cosa), DỪNG và điều tra trước khi tiếp tục Task 2 (không tự ý coi migration "thành công" nếu số không khớp).

- [ ] **Step 5: Cập nhật `docs/operations/migrations.md`**

Thay đoạn "**CHƯA làm (để CI/staging có Docker/Postgres thật xử lý tiếp):**" — xóa dòng "Chưa chạy qua chính `node scripts/migrate.mjs` thật", thêm dòng xác nhận đã chạy thật ngày hiện tại kèm số bảng thật quan sát được.

- [ ] **Step 6: Commit**

```bash
git add docs/operations/migrations.md
git commit -m "docs(migrations): xác nhận baseline_v1 + agent_core migration chạy thật trên Postgres, không chỉ pglite"
```

---

### Task 2: `encore run` + `encore test` cho `services/cosa`

**Files:**
- Không sửa code trừ khi test thật phát hiện lỗi so với `tsc --noEmit` từng pass giả (Phase 3/6 ghi nhận `tsc` sạch nhưng `vitest` chưa từng chạy).
- Test đã có sẵn: `services/cosa/tests/agent-policy.test.ts`, `services/cosa/tests/control-plane.test.ts`.

**Interfaces:**
- Consumes: DB thật từ Task 1 (schema `cosa`, `control_plane` phải tồn tại trước khi `encore run` khởi động — Encore tự chạy migration nội bộ khi start nhưng baseline đã áp ở Task 1 nên chỉ là xác nhận idempotent).

- [ ] **Step 1: Chạy `encore test` (không cần `encore run` riêng — `encore test` tự quản lý test DB)**

```bash
cd services/cosa
encore test ./tests/... 2>&1 | tee /tmp/encore-cosa-test.log
```
Expected: PASS toàn bộ `agent-policy.test.ts` (4 test mới từ Phase 3) và `control-plane.test.ts`.

- [ ] **Step 2: Nếu FAIL — phân loại lỗi**

Nếu lỗi là do khác biệt môi trường test (test-DB riêng của `encore test`, không phải `cosa_postgres` dev), đó là bình thường — Encore tự tạo ephemeral test DB. Nếu lỗi là logic (assertion sai), sửa code nguồn tương ứng trong `services/cosa/services/agent-policy.service.ts` hoặc `services/cosa/handlers/agent-policy.handler.ts`, không sửa test để pass giả.

- [ ] **Step 3: `encore run` thật, gọi endpoint mới bằng tay**

```bash
cd services/cosa
encore run &
sleep 5
curl -s -H "Authorization: Bearer <token thật hoặc test JWT>" \
  http://localhost:4000/platform/auth/me/agent-policy-snapshot | head -c 500
kill %1
```
Ghi lại response thật (hoặc lỗi auth cụ thể) — mục tiêu là xác nhận route thật sự đăng ký và không 404/500 do lỗi wiring, không nhất thiết phải có token hợp lệ sẵn.

- [ ] **Step 4: Cập nhật `COSA_FINAL_INTEGRATION_EXECUTION_STATUS_2026-08-25.md` Phase 3/6**

Sửa dòng "Chưa làm: verify TS test thật qua `encore test`." → xác nhận đã chạy, kèm kết quả PASS/FAIL thật và số test.

- [ ] **Step 5: Commit**

```bash
git add COSA_FINAL_INTEGRATION_EXECUTION_STATUS_2026-08-25.md
git commit -m "test(cosa): xác nhận encore test chạy thật cho agent-policy + control-plane"
```

---

### Task 3: Cross-process crash-recovery thật cho worker (CLAUDE.md #6)

**Files:**
- Create: `tests/apps/cosa/worker/test_crash_recovery_subprocess.py`
- Read (không sửa): `apps/cosa/worker/main.py`, `apps/cosa/worker/handlers.py`, `packages/agent_core/coordination/control_plane_scheduler_client.py`

**Interfaces:**
- Consumes: `apps/cosa/worker/main.py` phải có entrypoint chạy được qua `python -m apps.cosa.worker.main` với env `WORKER_ID` để phân biệt 2 process (đọc `main.py` để xác nhận tên biến env thật trước khi viết test — nếu tên khác `WORKER_ID`, dùng tên thật).
- Produces: bằng chứng sống rằng 2 **process hệ điều hành thật** (không phải 2 lần gọi hàm trong cùng process — đây chính là gap Phase 4 đã cảnh báo) tranh chấp lease đúng qua Postgres thật.

- [ ] **Step 1: Đọc `apps/cosa/worker/main.py` để xác nhận cách khởi động 1 vòng dispatch từ CLI**

```bash
grep -n "def main\|if __name__\|WORKER_ID\|argv\|argparse" apps/cosa/worker/main.py
```

- [ ] **Step 2: Viết test khởi 2 subprocess Python thật, dùng chung `DATABASE_URL`/`CONTROL_PLANE_DATABASE_URL` trỏ `cosa_postgres`**

```python
import os
import subprocess
import sys
import time
import uuid

import pytest


@pytest.mark.integration
def test_two_real_processes_do_not_double_claim_same_task(postgres_dsn):
    """Kill worker A giữa chừng, xác nhận worker B thật (process khác) resume đúng task, không double-process."""
    task_id = str(uuid.uuid4())
    env_a = {**os.environ, "WORKER_ID": "worker-a", "DATABASE_URL": postgres_dsn, "CONTROL_PLANE_DATABASE_URL": postgres_dsn}
    env_b = {**os.environ, "WORKER_ID": "worker-b", "DATABASE_URL": postgres_dsn, "CONTROL_PLANE_DATABASE_URL": postgres_dsn}

    proc_a = subprocess.Popen(
        [sys.executable, "-m", "apps.cosa.worker.main", "--once", "--task-id", task_id],
        env=env_a, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    time.sleep(1.0)  # để worker A claim lease trước khi bị kill
    proc_a.kill()
    proc_a.wait(timeout=5)

    proc_b = subprocess.Popen(
        [sys.executable, "-m", "apps.cosa.worker.main", "--once", "--task-id", task_id],
        env=env_b, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    out_b, _ = proc_b.communicate(timeout=15)

    assert proc_b.returncode == 0, out_b.decode()
    assert b"completed" in out_b.lower() or b"resumed" in out_b.lower(), out_b.decode()
```

Ghi chú: nếu `main.py` chưa có flag `--once`/`--task-id` cho single-shot invocation, đây LÀ một gap thật cần thêm (không phải placeholder — thêm flag CLI tối thiểu vào `apps/cosa/worker/main.py` trong Step 2b dưới, TDD: viết test trước, thấy fail vì thiếu flag, rồi thêm flag).

- [ ] **Step 2b (nếu cần): Thêm CLI single-shot mode vào `apps/cosa/worker/main.py`**

Chỉ thêm nếu Step 2 fail vì thiếu flag — đọc code hiện tại của `main.py` trước để biết vòng lặp dispatch hiện có hình dạng gì (`while True` polling hay event-driven), thêm nhánh `--once` chạy đúng 1 vòng `dispatch_one_task`/tương đương rồi thoát, không đổi hành vi vòng lặp production mặc định.

- [ ] **Step 3: Fixture `postgres_dsn` — trỏ vào `cosa_postgres` thật (không phải pglite/sqlite)**

Thêm vào `tests/apps/cosa/worker/test_crash_recovery_subprocess.py` hoặc `tests/apps/cosa/worker_test_helpers.py`:

```python
import os
import pytest


@pytest.fixture
def postgres_dsn():
    dsn = os.environ.get("CONTROL_PLANE_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not dsn:
        pytest.skip("CONTROL_PLANE_DATABASE_URL/DATABASE_URL không set — cần Postgres thật")
    return dsn
```

- [ ] **Step 4: Chạy test, xác nhận PASS với process thật**

```bash
cd /Volumes/SSD/javis-saas
python3.11 -m pytest tests/apps/cosa/worker/test_crash_recovery_subprocess.py -v -m integration
```

- [ ] **Step 5: Thêm stuck-task sweeper (gap #2 của Phase 4)**

Đọc `apps/cosa/worker/handlers.py` và `packages/agent_core/coordination/control_plane_scheduler_client.py` để tìm cột lease hiện có (`leased_until`/`heartbeat_at` tương tự). Thêm hàm `sweep_stuck_tasks(dsn, stale_after_seconds: int) -> int` trong `packages/agent_core/coordination/control_plane_scheduler_client.py` — reset task về `pending` nếu `status = 'processing'` và lease quá hạn không renew. Viết test trước (`tests/agent_core/coordination/test_control_plane_scheduler_client.py`, thêm case): insert task "processing" với lease hết hạn giả lập bằng cách set timestamp trong quá khứ, gọi `sweep_stuck_tasks`, assert task quay lại `pending`.

- [ ] **Step 6: Chạy toàn bộ test worker + coordination**

```bash
python3.11 -m pytest tests/apps/cosa/worker/ tests/agent_core/coordination/ -v
```
Expected: PASS toàn bộ, không skip do thiếu DSN.

- [ ] **Step 7: Commit**

```bash
git add tests/apps/cosa/worker/test_crash_recovery_subprocess.py tests/apps/cosa/worker_test_helpers.py \
  apps/cosa/worker/main.py packages/agent_core/coordination/control_plane_scheduler_client.py \
  tests/agent_core/coordination/test_control_plane_scheduler_client.py
git commit -m "test(worker): cross-process crash-recovery thật qua Postgres + stuck-task sweeper"
```

---

### Task 4: SSE E2E reconnect thật (`Last-Event-ID` sau khi API process restart)

**Files:**
- Create: `tests/apps/cosa/test_sse_reconnect_e2e.py`
- Read: `apps/cosa/api/event_stream.py`, `packages/agent_core/runs/stream_events.py`

**Interfaces:**
- Consumes: `apps/cosa/api/event_stream.py` phải expose FastAPI app khởi động qua uvicorn CLI thật (kiểm tra `apps/cosa/api/routes.py` hoặc composition root để biết đúng module path, ví dụ `apps.cosa.api.main:app`).

- [ ] **Step 1: Xác nhận entrypoint uvicorn thật**

```bash
grep -rn "uvicorn\|FastAPI(" apps/cosa/api/ apps/cosa/composition/ | grep -v test
```

- [ ] **Step 2: Viết test khởi uvicorn subprocess thật, gửi event, kill, restart, reconnect bằng `Last-Event-ID`**

```python
import os
import signal
import subprocess
import sys
import time

import httpx
import pytest


@pytest.mark.integration
def test_sse_reconnect_survives_process_restart(postgres_dsn, run_id_with_events):
    env = {**os.environ, "DATABASE_URL": postgres_dsn}
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "apps.cosa.api.main:app", "--port", "8091"],
        env=env,
    )
    try:
        time.sleep(2.0)
        with httpx.Client(timeout=5.0) as client:
            with client.stream("GET", f"http://127.0.0.1:8091/runs/{run_id_with_events}/events") as r:
                first_events = []
                for line in r.iter_lines():
                    if line.startswith("id:"):
                        last_id = line.split(":", 1)[1].strip()
                        first_events.append(last_id)
                    if len(first_events) >= 2:
                        break
    finally:
        proc.send_signal(signal.SIGKILL)
        proc.wait(timeout=5)

    proc2 = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "apps.cosa.api.main:app", "--port", "8091"],
        env=env,
    )
    try:
        time.sleep(2.0)
        with httpx.Client(timeout=5.0) as client:
            headers = {"Last-Event-ID": first_events[-1]}
            with client.stream("GET", f"http://127.0.0.1:8091/runs/{run_id_with_events}/events", headers=headers) as r:
                resumed_ids = []
                for line in r.iter_lines():
                    if line.startswith("id:"):
                        resumed_ids.append(line.split(":", 1)[1].strip())
                    if len(resumed_ids) >= 1:
                        break
        assert int(resumed_ids[0]) > int(first_events[-1])
    finally:
        proc2.send_signal(signal.SIGKILL)
        proc2.wait(timeout=5)
```

Ghi chú: `run_id_with_events` là fixture cần viết — dùng `packages/agent_core/runs/stream_events.py` để insert trực tiếp 3-4 event test vào `agent_conversation.run_stream_events` trước khi start server, đảm bảo có dữ liệu để replay (đọc `stream_events.py` để lấy đúng tên hàm insert/tên bảng/cột trước khi viết fixture — không đoán tên).

- [ ] **Step 3: Chạy test**

```bash
python3.11 -m pytest tests/apps/cosa/test_sse_reconnect_e2e.py -v -m integration
```

- [ ] **Step 4: Cập nhật `COSA_FINAL_INTEGRATION_EXECUTION_STATUS_2026-08-25.md` Phase 5**

Xóa dòng "Chưa làm: E2E-4 thật..." → xác nhận đã verify.

- [ ] **Step 5: Commit**

```bash
git add tests/apps/cosa/test_sse_reconnect_e2e.py COSA_FINAL_INTEGRATION_EXECUTION_STATUS_2026-08-25.md
git commit -m "test(sse): E2E reconnect Last-Event-ID qua API process restart thật"
```

---

### Task 5: DeepSeek conformance + checkpoint-resume thật (Phase 7)

**Files:**
- Create: `tests/agent_core/kernel/test_deepseek_conformance.py`
- Read: `packages/agent_core/kernel/openai_agents_kernel.py`

**Interfaces:**
- Consumes: `DEEPSEEK_API_KEY`/`DEEPSEEK_BASE_URL`/`DEEPSEEK_DEFAULT_MODEL` từ `.env` (đã có giá trị thật trong môi trường này).

- [ ] **Step 1: Đọc `openai_agents_kernel.py` để xác định cách gọi provider + checkpoint API thật (tên hàm `run`/`resume`, tên tham số checkpoint)**

```bash
grep -n "def run\|def resume\|checkpoint\|class.*Kernel" packages/agent_core/kernel/openai_agents_kernel.py
```

- [ ] **Step 2: Viết test gọi model DeepSeek thật cho 1 turn đơn giản (chi phí thấp — prompt ngắn)**

```python
import os

import pytest

from packages.agent_core.kernel.openai_agents_kernel import OpenAIAgentsKernel  # tên lớp thật lấy từ Step 1


@pytest.mark.integration
@pytest.mark.skipif(not os.environ.get("DEEPSEEK_API_KEY"), reason="cần DEEPSEEK_API_KEY thật")
class TestDeepseekConformance:
    def test_single_turn_completes_with_real_deepseek(self):
        kernel = OpenAIAgentsKernel(provider="deepseek")  # điều chỉnh theo constructor thật
        result = kernel.run(input="Trả lời đúng 1 từ: 'ok'", metadata={})
        assert result is not None
        assert "ok" in str(result).lower()

    def test_checkpoint_resume_with_real_deepseek(self):
        kernel = OpenAIAgentsKernel(provider="deepseek")
        checkpoint = kernel.run_until_checkpoint(input="...", metadata={})  # tên hàm thật lấy từ Step 1
        resumed = kernel.resume(checkpoint_ref=checkpoint.ref, approval={"approved": True})
        assert resumed.status == "completed"
```

Ghi chú: các tên hàm/tham số ở trên là placeholder có chủ đích lấy từ Step 1 (đọc code thật) — TRƯỚC khi viết Step 2 thật, phải copy đúng chữ ký hàm từ `openai_agents_kernel.py`, không giữ nguyên tên đoán trong plan này.

- [ ] **Step 3: Chạy test, xác nhận gọi API thật thành công (không mock)**

```bash
python3.11 -m pytest tests/agent_core/kernel/test_deepseek_conformance.py -v -m integration
```

- [ ] **Step 4: Cập nhật Phase 7 trong `COSA_FINAL_INTEGRATION_EXECUTION_STATUS_2026-08-25.md`**

- [ ] **Step 5: Commit**

```bash
git add tests/agent_core/kernel/test_deepseek_conformance.py COSA_FINAL_INTEGRATION_EXECUTION_STATUS_2026-08-25.md
git commit -m "test(kernel): conformance + checkpoint-resume thật với DeepSeek API"
```

---

### Task 6: Deployment cutover có kiểm soát — thêm service Python mới song song, KHÔNG xóa legacy trong task này

**Files:**
- Create: `apps/cosa/Dockerfile.api`, `apps/cosa/Dockerfile.worker`
- Modify: `docker-compose.yml` (thêm service mới, KHÔNG sửa/xóa 4 service legacy hiện có)

**Interfaces:**
- Produces: service `cosa-api` (port khác `brain-api`, ví dụ `8001`) và `cosa-worker` chạy song song với `brain-api`/`agent-worker` legacy để so sánh hành vi trước khi cutover thật (cutover thật — xóa legacy — là một thay đổi riêng, KHÔNG nằm trong task này, cần xác nhận người dùng trước khi thực hiện theo CLAUDE.md #10).

- [ ] **Step 1: Viết `apps/cosa/Dockerfile.api`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY apps/cosa/requirements.txt /app/apps/cosa/requirements.txt
RUN pip install --no-cache-dir -r /app/apps/cosa/requirements.txt
COPY packages/agent_core /app/packages/agent_core
COPY apps/cosa /app/apps/cosa
ENV PYTHONPATH=/app
CMD ["python", "-m", "uvicorn", "apps.cosa.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

(Điều chỉnh entrypoint module theo kết quả xác nhận thật ở Task 4 Step 1.)

- [ ] **Step 2: Viết `apps/cosa/Dockerfile.worker`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY apps/cosa/requirements.txt /app/apps/cosa/requirements.txt
RUN pip install --no-cache-dir -r /app/apps/cosa/requirements.txt
COPY packages/agent_core /app/packages/agent_core
COPY apps/cosa /app/apps/cosa
ENV PYTHONPATH=/app
CMD ["python", "-m", "apps.cosa.worker.main"]
```

- [ ] **Step 3: Thêm service mới vào `docker-compose.yml`, profile `cosa` (mới, tách khỏi `legacy`)**

Thêm sau block `agent-worker` (dòng ~213), trước `opensandbox`:

```yaml
  cosa-api:
    build:
      context: .
      dockerfile: apps/cosa/Dockerfile.api
    container_name: cosa_api
    ports:
      - "127.0.0.1:8001:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL:-postgresql://javis_app:change-me-javis-app@postgres:5432/javis}
      - CONTROL_PLANE_DATABASE_URL=${CONTROL_PLANE_DATABASE_URL:-postgresql://cosa_control_plane_app:change-me-control-plane-app@postgres:5432/cosa_control_plane}
    depends_on:
      postgres:
        condition: service_healthy
    profiles:
      - cosa
    restart: unless-stopped

  cosa-worker:
    build:
      context: .
      dockerfile: apps/cosa/Dockerfile.worker
    container_name: cosa_worker
    environment:
      - DATABASE_URL=${DATABASE_URL:-postgresql://javis_app:change-me-javis-app@postgres:5432/javis}
      - CONTROL_PLANE_DATABASE_URL=${CONTROL_PLANE_DATABASE_URL:-postgresql://cosa_control_plane_app:change-me-control-plane-app@postgres:5432/cosa_control_plane}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:-}
      - DEEPSEEK_BASE_URL=${DEEPSEEK_BASE_URL:-https://api.deepseek.com}
      - DEEPSEEK_DEFAULT_MODEL=${DEEPSEEK_DEFAULT_MODEL:-deepseek-chat}
    depends_on:
      postgres:
        condition: service_healthy
      cosa-api:
        condition: service_started
    profiles:
      - cosa
    restart: unless-stopped
```

- [ ] **Step 4: Build + start, xác nhận health thật**

```bash
docker compose --profile cosa build cosa-api cosa-worker
docker compose --profile cosa up -d cosa-api cosa-worker
sleep 5
curl -s http://127.0.0.1:8001/healthz || curl -s http://127.0.0.1:8001/
docker compose logs cosa-worker --tail 30
```
Expected: `cosa-api` trả HTTP 200 (hoặc route thật tương đương), `cosa-worker` log không crash-loop.

- [ ] **Step 5: So sánh hành vi song song với legacy — chạy 1 request thật qua cả 2 service, xác nhận kết quả tương đương**

Không viết test tự động cho bước này (là bước vận hành thủ công một lần) — ghi kết quả quan sát vào `COSA_FINAL_INTEGRATION_EXECUTION_STATUS_2026-08-25.md` Phase 8.

- [ ] **Step 6: `docker compose --profile cosa down`, cập nhật tài liệu**

Cập nhật `COSA_FINAL_INTEGRATION_EXECUTION_STATUS_2026-08-25.md`: Phase 8 giờ có service Python mới chạy song song, verified equivalence — nhưng vẫn ghi rõ "CHƯA xóa mount `legacy/backend` khỏi 4 service cũ, cần xác nhận riêng với người dùng trước khi làm bước cutover thật (xóa legacy service khỏi compose)".

- [ ] **Step 7: Commit**

```bash
git add apps/cosa/Dockerfile.api apps/cosa/Dockerfile.worker docker-compose.yml \
  COSA_FINAL_INTEGRATION_EXECUTION_STATUS_2026-08-25.md
git commit -m "feat(deploy): thêm service cosa-api/cosa-worker song song legacy, chưa cutover"
```

**KHÔNG làm trong task này (cần xác nhận người dùng riêng, xem CLAUDE.md #10):**
- Xóa 4 service legacy (`migrate`, `migrate-control-plane`, `brain-api`, `agent-worker`) khỏi `docker-compose.yml`.
- Đổi `make deploy-control-plane` để không phụ thuộc `migrate-control-plane` (Alembic).

---

### Task 7: Legacy-exit prep (Phase 10 vẫn KHÔNG chạy — chỉ chuẩn bị điều kiện)

**Files:**
- Modify: `COSA_FINAL_INTEGRATION_EXECUTION_STATUS_2026-08-25.md` (mục 2, checklist Phase 10)
- Create: `docs/operations/rollback_pre_cutover.md`

**Interfaces:**
- Consumes: kết quả Task 1-6 (tất cả phải PASS/VERIFIED trước khi bắt đầu task này có ý nghĩa).

- [ ] **Step 1: Audit behavior inventory L1-L5 (tài liệu gốc §23) — đọc lại danh sách, đối chiếu từng dòng với code thật hiện tại**

```bash
grep -n "L1\|L2\|L3\|L4\|L5" COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md | head -60
```
Với mỗi dòng L1-L5, xác nhận hành vi tương ứng đã có trong `apps/cosa`/`packages/agent_core` (không phải chỉ legacy) — ghi kết quả PASS/GAP vào file trạng thái.

- [ ] **Step 2: Viết `docs/operations/rollback_pre_cutover.md`**

Nội dung tối thiểu: cách revert `docker-compose.yml` về chỉ dùng legacy service (`git revert` commit Task 6, hoặc `docker compose --profile legacy up -d` song song), cách restore DB nếu migration Task 1 cần rollback (`.down.sql` nếu có, hoặc snapshot `pg_dump` trước Task 1 — thêm bước `pg_dump` vào đầu quy trình này cho lần chạy thật tiếp theo).

- [ ] **Step 3: Tạo git tag `pre-cutover` tại commit hiện tại (SAU khi Task 1-6 đã merge, TRƯỚC khi bất kỳ ai xóa `legacy/`)**

```bash
git tag -a pre-cutover -m "Trạng thái trước khi xóa legacy/ — rollback point, xem docs/operations/rollback_pre_cutover.md"
```
KHÔNG `git push --tags` trong task này — hỏi người dùng trước khi push tag lên remote (thay đổi visible cho người khác, theo nguyên tắc executing-actions-with-care).

- [ ] **Step 4: Cập nhật `COSA_FINAL_INTEGRATION_EXECUTION_STATUS_2026-08-25.md` mục "Phase 10"**

Đánh dấu các mục checklist đã đạt (Zero Docker mount vẫn CHƯA đạt — Task 6 cố ý giữ song song, không xóa). Ghi rõ Phase 10 (xóa `legacy/` thật) vẫn KHÔNG thực hiện trong plan này — cần quyết định riêng của người dùng sau khi xem kết quả song song ở Task 6 Step 5 đủ lâu (đề xuất tối thiểu vài ngày vận hành thật trước khi xóa).

- [ ] **Step 5: Commit**

```bash
git add COSA_FINAL_INTEGRATION_EXECUTION_STATUS_2026-08-25.md docs/operations/rollback_pre_cutover.md
git commit -m "docs: chuẩn bị điều kiện Phase 10 (rollback proc, tag pre-cutover cục bộ, audit L1-L5) — chưa xóa legacy/"
```

---

## Self-Review Notes

- Task 3/4/5 dùng chữ ký hàm "đoán" có chủ đích ghi rõ ràng — bắt buộc đọc code thật ở Step 1 của từng task trước khi copy vào test, không phải placeholder mơ hồ kiểu "viết test phù hợp".
- Task 6 KHÔNG xóa legacy — khớp với rủi ro CLAUDE.md #10 và chính tài liệu gốc đã tự flag "không tự ý làm".
- Task 7 KHÔNG chạy Phase 10 thật (xóa `legacy/`) — chỉ chuẩn bị. Đúng với "Trạng thái: KHÔNG ĐẠT điều kiện, đúng theo thiết kế" trong tài liệu gốc.
- Mỗi task kết thúc bằng cập nhật `COSA_FINAL_INTEGRATION_EXECUTION_STATUS_2026-08-25.md` — giữ tài liệu này là nguồn sự thật cập nhật theo CLAUDE.md.

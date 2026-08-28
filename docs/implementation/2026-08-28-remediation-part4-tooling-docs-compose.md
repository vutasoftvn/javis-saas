# PHẦN 4 — Tooling / docs / compose residual

**Ngày:** 2026-08-28
**Phần của:** [dev-readiness-remediation-remaining](./2026-08-28-dev-readiness-remediation-remaining.md) · doc gốc §9
**Nhánh đề xuất:** `remediation/part4-tooling-docs-compose`
**Phụ thuộc:** không

## Context

Commit `1c6fffde` (P2b) + `683d8ea1` đã làm: landing eslint config + job CI `landing`
(lint+build), `.github/workflows/quality.yml` (frontend, tenancy-check, services typecheck+test,
quality-unit skillpack-validate, quality-integration, realtime-agent), `scripts/check-dev-preflight.sh`
(nạp `.env` có chủ đích, check required vars, `docker compose config`, health, JWT claims không
in token), README link fix.

PHẦN 4 đóng các mục §9 **còn lại**.

## Thay đổi

### 4.1 — Python runtime thống nhất `.venv/bin/python`

- `Makefile:3` đã có `PYTHON ?= .venv/bin/python || python3`. Nhưng còn target dùng `python`
  trần: dòng ~119, ~148, ~204, ~222, ~238, ~240, ~279 (`python -m packages.agent_core.scripts.migrate`,
  `python -m apps.cosa.*`). Đổi hết sang `$(PYTHON)`.
- `boundary-check` (`Makefile:49`): xác nhận gọi `$(PYTHON)`, không phải `python`/`python3` hệ thống.
- README / `docs/` hướng dẫn setup: mọi lệnh Python ví dụ dùng `.venv/bin/python` (hoặc một
  bootstrap `uv` duy nhất). Một nguồn hướng dẫn, không hai lối.

### 4.2 — Bootstrap `.env` local

- `scripts/check-dev-preflight.sh::load_env_file` đã đúng nguyên tắc (biến export sẵn thắng `.env`).
- Tách phần `load_env_file` thành `scripts/load-dev-env.sh` (source được), để Makefile targets
  chạy local cũng nạp `.env` cùng cách; CI không source file này (tiếp tục cấp env trực tiếp).
- README: một mục "Local env bootstrap" duy nhất, trỏ script này.

### 4.3 — CI link-check README / docs canonical

- Job mới trong `.github/workflows/quality.yml` (hoặc workflow riêng `docs.yml`):
  chạy link-checker (vd `lychee` action hoặc script `grep` + kiểm tồn tại file) trên `README.md`
  và các doc canonical liệt kê trong CLAUDE.md (mục "Nguồn sự thật kiến trúc").
- Fail nếu có link nội bộ trỏ file không tồn tại. Sửa/again archive link chết còn lại.

### 4.4 — Pin image `latest` → tag/digest

- Quét `docker-compose.yml`, `services/docker-compose.yml`, `deploy/**`:
  `grep -rn ":latest" docker-compose.yml services/ deploy/`.
- Pin ít nhất: MinIO, LiveKit, OpenSandbox → tag phiên bản cụ thể (ưu tiên digest `@sha256:`).
- Ghi lại version đã pin trong comment cạnh image.

### 4.5 — Production compose fail-closed

- Thêm `deploy/**/docker-compose.prod.yml` (hoặc kiểm file prod hiện có): biến bắt buộc dùng
  `${VAR:?msg}` để `docker compose config` **fail** khi thiếu.
- Test: `docs`/script kiểm
  ```text
  docker compose -f <prod compose> config      # thiếu biến → exit != 0, in tên biến
  docker compose config                        # local + .env → exit 0
  ```
- Mẫu env prod dùng placeholder không đăng nhập được.

### 4.6 — Coverage threshold ban đầu

- Đo baseline thực cho: auth (`services/company/identity`), tenant scope (PHẦN 1 test),
  workflow engine (`packages/agent_core/workflows`), API contract (PHẦN 3 test).
- Đặt ngưỡng = baseline đo được (không đặt số tùy ý để xanh giả). Wire vào CI job tương ứng
  (`pytest --cov --cov-fail-under=<baseline>` cho Python; `vitest`/`c8` hoặc `encore test` coverage
  cho TS nếu hỗ trợ).
- Ghi baseline + ngày + commit vào `docs/implementation/coverage-baseline-2026-08-28.md`.

### 4.7 — Chuẩn báo cáo readiness

- Thêm mục vào `docs/` (hoặc CONTRIBUTING): mọi report readiness phải ghi **scope + lệnh kiểm
  tra + ngày + commit**; cấm "done/green" chung chung.
- Rà các report hiện có mâu thuẫn static check (doc gốc §2 "Đã xác minh là lỗi/gap" hàng "Tài
  liệu") — thêm ghi chú "trạng thái tính đến <commit>".

## Verify

```text
make boundary-check              # từ clone sạch + bootstrap, không cần Python hệ thống
make verify                      # boundary-check, skillpacks-validate, tenancy-check, *-test, frontend
docker compose config            # local hợp lệ khi .env nạp
docker compose -f <prod compose> config   # fail khi thiếu biến bắt buộc
grep -rn ":latest" docker-compose.yml services/ deploy/   # rỗng cho MinIO/LiveKit/OpenSandbox
```

CI: job link-check xanh; job coverage không tụt dưới ngưỡng baseline.

## Definition of Done (ánh xạ doc gốc §9)

- [ ] Makefile / script / README gọi cùng một Python runtime (`.venv/bin/python` hoặc `uv` bootstrap).
- [ ] `make boundary-check` chạy được từ clone mới + bootstrap documented, không cài nhầm Python hệ thống.
- [ ] Có entry CI cho: `make boundary-check`, skillpack validation, Company/COSA typecheck,
      Flutter test/analyze, landing lint/build (bổ sung cái còn thiếu).
- [ ] `docker compose config` hợp lệ khi nạp cấu hình local; production compose fail nếu thiếu biến bắt buộc.
- [ ] Không còn image `latest` cho MinIO, LiveKit, OpenSandbox.
- [ ] CI link-check README/docs canonical; không còn link canonical chết.
- [ ] Coverage threshold ban đầu cho auth, tenant scope, workflow engine, API contract —
      ngưỡng = baseline thực đo, ghi lại kèm commit.
- [ ] Có chuẩn viết report readiness (scope + lệnh + ngày + commit).

# Part 1A — Python quality gate

**Master:** [`2026-08-28-test-prod-readiness.md`](./2026-08-28-test-prod-readiness.md)
**Phụ thuộc:** Part 0
**Ước lượng:** 1–1.5 ngày
**Nhánh:** `tpr/part1a-python-quality-gate`

## Mục tiêu

Repo hiện **không có** lint/format/type gate cho Python. Thiết lập một quality gate fail-closed cho `packages/agent_core`, `apps/cosa`, `packages/agent_integrations`, chạy được từ máy sạch và trong CI, không "xanh giả".

## Trạng thái hiện tại (verify bằng code)

- Không có `pyproject.toml`, `ruff.toml`, `mypy.ini`, `.pre-commit-config.yaml` ở repo root (`ls` xác nhận).
- `pytest.ini` tối giản: `pythonpath`, `testpaths`, `asyncio_mode = strict`, 2 marker (`integration`, `live_provider`).
- Không có `pytest-cov` trong `packages/agent_core/requirements.txt` / `apps/cosa/requirements.txt`.
- Makefile đã ưu tiên `.venv/bin/python`: `PYTHON ?= $(shell test -x $(CURDIR)/.venv/bin/python && echo … || echo python3)` — dùng biến này cho target mới.
- CI `.github/workflows/quality.yml` có `quality-unit`, `quality-integration` (có Postgres + Encore CLI), `quality-live-provider`, `boundaries` — **chưa có** job lint/type.
- TS: `services/*` chỉ `npm run typecheck` (`tsc --noEmit`, `strict: true`), không eslint/biome.

## Thay đổi cụ thể

### 1. `pyproject.toml` (root, mới)

```toml
[tool.ruff]
target-version = "py311"
line-length = 100
extend-exclude = [".venv", ".venv_verify", "node_modules", "legacy", "**/migrations/**"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "PL", "RUF"]
ignore = ["PLR0913", "PLR2004"]  # nới ban đầu, siết dần

[tool.ruff.format]
quote-style = "double"

[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true      # lenient giai đoạn 1
disallow_untyped_defs = false
warn_unused_ignores = true
warn_redundant_casts = true
files = ["packages/agent_core", "apps/cosa", "packages/agent_integrations"]
exclude = "(migrations|tests|\\.venv)"

[tool.pytest.ini_options]
# migrate nguyên trạng từ pytest.ini
pythonpath = [".", "packages", "apps"]
testpaths = ["tests/agent_core", "tests/apps", "tests/desktop_worker", "packages/agent_testkit"]
asyncio_mode = "strict"
markers = [
  "integration: cần DB thật",
  "live_provider: gọi API model thật",
  "durability: test qua nhiều OS process (Part 1C)",
]

[tool.coverage.run]
source = ["packages/agent_core", "apps/cosa"]
omit = ["*/migrations/*", "*/tests/*"]

[tool.coverage.report]
show_missing = true
```

Xoá `pytest.ini` sau khi xác nhận `[tool.pytest.ini_options]` tương đương.

### 2. Dependencies

Thêm vào `packages/agent_core/requirements.txt` (hoặc file dev-requirements chung mới `requirements-dev.txt`): `ruff==<pin>`, `mypy==<pin>`, `pytest-cov==<pin>`, `pre-commit==<pin>`.

### 3. `.pre-commit-config.yaml` (root, mới)

Hooks: `ruff` (`--fix`), `ruff-format`, `check-yaml`, `check-merge-conflict`, `end-of-file-fixer`, `trailing-whitespace`. Loại trừ `legacy/`, `migrations/`.

### 4. Coverage floor (ratchet)

- Chạy `pytest --cov --cov-report=term-missing` để đo baseline thực tế theo package, ghi vào `docs/implementation/coverage-baseline-2026-08-28.md` (mục mới "measured %").
- Đặt `--cov-fail-under` **theo path** trong Makefile target (không global). Ví dụ khởi đầu: `packages/agent_core` ≥ số đo hiện tại − 2%, `apps/cosa` ≥ số đo − 2%. Ghi chú ratchet: mỗi part sau nâng floor.

### 5. Makefile

```make
lint:            ## ruff check + format check
	$(PYTHON) -m ruff check packages/agent_core apps/cosa packages/agent_integrations
	$(PYTHON) -m ruff format --check packages/agent_core apps/cosa packages/agent_integrations

lint-fix:
	$(PYTHON) -m ruff check --fix packages/agent_core apps/cosa packages/agent_integrations
	$(PYTHON) -m ruff format packages/agent_core apps/cosa packages/agent_integrations

typecheck-py:
	$(PYTHON) -m mypy
```

Thêm `lint typecheck-py` vào `verify` và `verify-local`.

### 6. CI job `python-lint` (`.github/workflows/quality.yml`)

```yaml
  python-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11', cache: pip }
      - run: pip install ruff mypy -r packages/agent_core/requirements.txt -r apps/cosa/requirements.txt
      - run: ruff check packages/agent_core apps/cosa packages/agent_integrations
      - run: ruff format --check packages/agent_core apps/cosa packages/agent_integrations
      - run: mypy
```

Thêm `--cov --cov-report=xml --cov-fail-under` vào các bước `pytest` của `quality-unit` / `quality-integration`; upload `coverage.xml` artifact.

### 6b. Fix `services/company` typecheck đỏ (cổng merge — Part 0)

Part 0 phát hiện `services/company npm run typecheck` fail **4 lỗi** ở `task-events.service.ts` / `task.service.ts`. Đây là điều kiện (a) của cổng merge nhánh → `main`.

- Chạy `cd services/company && npm run typecheck`, đọc 4 lỗi.
- Sửa tại chỗ (nhiều khả năng: kiểu event payload / Drizzle inference / import). Không nới `tsconfig` (`strict: true` giữ nguyên).
- Thêm/điều chỉnh test vitest nếu lỗi lộ ra hành vi sai, không chỉ kiểu.
- Verify: `npm run typecheck` = 0 lỗi; `encore test` (services/company) xanh.

### 7. (Tuỳ chọn, ưu tiên thấp) Biome cho `services/*`

Nếu làm: `biome.json` tối giản (formatter + `noUnusedVariables`), thêm `npm run lint` vào job `services` matrix. Không bắt buộc cho milestone này.

## Reuse

- `PYTHON` macro trong Makefile.
- Marker + testpaths hiện có trong `pytest.ini`.
- Job skeleton `quality-unit` trong `quality.yml` để copy structure.

## Test / verify

- `make lint` và `make typecheck-py` chạy sạch từ `.venv` mới (`python -m venv` + `pip install -r`).
- `make verify` local xanh, có dòng coverage %.
- Push nhánh → CI job `python-lint` xanh; `coverage.xml` xuất hiện trong artifacts.
- Cố tình thêm 1 dòng `import os` thừa → `ruff check` fail (chứng minh gate thật).

## Definition of Done

- [ ] `pyproject.toml` + `.pre-commit-config.yaml` committed; `pytest.ini` xoá.
- [ ] `ruff check` + `ruff format --check` + `mypy` xanh trên 3 package.
- [ ] Coverage baseline đo được, ghi vào doc, `--cov-fail-under` theo path bật trong CI.
- [ ] CI job `python-lint` bắt buộc (branch protection) — ghi chú trong PR.
- [ ] `make verify` / `verify-local` bao gồm lint + typecheck.

## Rủi ro

- `ruff check` lần đầu có thể ra hàng trăm lỗi → chạy `ruff check --fix` + `ruff format` trong 1 commit "format sweep" riêng, review kỹ diff, tách khỏi commit cấu hình.
- `mypy` với codebase lớn chưa từng gate → giữ lenient (`ignore_missing_imports`, `disallow_untyped_defs=false`) giai đoạn 1; siết theo module ở part sau.
- Coverage fail-under quá cao → chọn floor = số đo − 2%, tăng dần.

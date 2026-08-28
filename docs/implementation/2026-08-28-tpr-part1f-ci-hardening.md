# Part 1F — CI hardening

**Master:** [`2026-08-28-test-prod-readiness.md`](./2026-08-28-test-prod-readiness.md)
**Phụ thuộc:** Part 0
**Ước lượng:** 1–1.5 ngày
**Nhánh:** `tpr/part1f-ci-hardening`

## Mục tiêu

Đóng các residual CI/tooling: doc link-check trong CI, thống nhất Python runtime, và **Migration Gate D — schema fingerprint** để bắt schema drift sau `migrate-all`.

## Trạng thái hiện tại (verify bằng code)

- `scripts/check_doc_links.py` + `scripts/check-doc-links.sh` **đã tồn tại** (commit `1c6fffde`/`adff857b`) — `make check-docs` gọi nó, có trong `verify`/`verify-local`, nhưng **chưa có job CI riêng** trong `.github/workflows/quality.yml`.
- Makefile `PYTHON ?= $(shell test -x $(CURDIR)/.venv/bin/python && ...)` — đã ưu tiên `.venv`; cần rà các target còn gọi `python`/`pytest` trần (không qua `$(PYTHON)`/`$(PYTEST)`).
- `docs/operations/migrations.md` §29.6: schema fingerprint auto-verify = "design only, no code" (Gate D). Gate E (`.down.sql`) và Gate G (prod run) cũng chưa — E/G thuộc Part 2A/2D.
- Migration: `packages/agent_core/migrations/*.sql` (11), `services/cosa/migrations/*.up.sql` (17), `services/company/*/migrations/*.up.sql` (32). `make migrate-all` chạy thứ tự Agent Core → COSA → Company.

## Thay đổi cụ thể

### 1F.0 Sửa 3 link hỏng còn lại (điều kiện bật CI job)

Sau khi bộ doc TPR đủ 14 file, `make check-docs` còn **3 link hỏng có sẵn** (không liên quan TPR):
- `docs/superpowers/plans/2026-08-28-event-driven-agent-operating-model-local-first.md:11` → path tuyệt đối `/Users/mivacorp/Downloads/...pdf` (sửa thành ghi chú nguồn, bỏ link cục bộ).
- `skillpacks/research/deep-research/SKILL.md:63,67` → literal `URL` (placeholder template — sửa hoặc thêm allowlist trong `check_doc_links.py`).

Fix 3 chỗ này trước, rồi mới bật job (job đỏ ngay từ đầu sẽ bị bỏ qua).

### 1F.1 CI job `doc-links`

```yaml
  doc-links:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: python scripts/check_doc_links.py
```
Bắt buộc cho merge. (Rẻ, nhanh — luôn chạy mọi push.)

### 1F.2 Thống nhất Python runtime

- `grep -nE "(^|[^v/])python3? |[^-]pytest " Makefile` → chuyển mọi lệnh còn trần sang `$(PYTHON)` / `$(PYTEST)`.
- Rà `scripts/*.sh` gọi `python` → dùng `${PYTHON:-python3}` hoặc `.venv/bin/python` khi có.
- Ghi chú trong `Makefile` header: "Mọi target Python phải qua `$(PYTHON)`".

### 1F.3 Migration Gate D — schema fingerprint

`scripts/schema-fingerprint.mjs` (mới, Node — cùng runtime với `migrate.mjs`):

- Sau `migrate-all` trên 1 Postgres sạch, với mỗi database/schema group: query `information_schema` (tables, columns, types, nullability, defaults, PK/FK, indexes, check constraints, enums) → chuẩn hoá (sort ổn định, bỏ thứ tự OID) → SHA-256.
- `--check`: so với golden đã commit `deploy/schema/fingerprints.json`; khác → exit 1, in diff (tên object thêm/bớt/đổi).
- `--write`: cập nhật golden (chạy tay khi migration mới, review trong PR).

Makefile:
```make
schema-fingerprint-check: ## So schema thực với golden
	node scripts/schema-fingerprint.mjs --check
schema-fingerprint-write:
	node scripts/schema-fingerprint.mjs --write
```

CI job `schema-fingerprint`:
```yaml
  schema-fingerprint:
    runs-on: ubuntu-latest
    services:
      postgres: { image: pgvector/pgvector:pg16, env: {...}, ports: ["5432:5432"], options: "--health-cmd ..." }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11', cache: pip }
      - uses: actions/setup-node@v4
        with: { node-version: '22' }
      - run: pip install -r packages/agent_core/requirements.txt
      - run: make migrate-all
        env: { ...DB env... }
      - run: node scripts/schema-fingerprint.mjs --check
```
Fail khi ai đó đổi migration mà quên cập nhật golden → buộc review chủ đích.

### 1F.4 (Gộp nhỏ) coverage.xml + junit tổng hợp

Bảo đảm mọi job pytest xuất `--junitxml` + (từ 1A) `--cov-report=xml`; thêm 1 step `if: always()` upload để CI summary có dữ liệu.

## Reuse

- `scripts/check_doc_links.py` (đã có).
- `scripts/migrate.mjs` (pattern kết nối + chạy tuần tự) làm khung cho `schema-fingerprint.mjs`.
- Postgres service block + `make migrate-all` (đã có).
- `PYTHON`/`PYTEST` macro Makefile.

## Test / verify

- `python scripts/check_doc_links.py` xanh local; thêm 1 link hỏng → đỏ.
- `make migrate-all && make schema-fingerprint-write` tạo `deploy/schema/fingerprints.json`; commit.
- Sửa 1 migration (thêm cột) không cập nhật golden → `schema-fingerprint-check` đỏ; `--write` + commit → xanh lại.
- `grep` Makefile: 0 lệnh Python trần ngoài `$(PYTHON)`.

## Definition of Done

- [ ] CI job `doc-links` + `schema-fingerprint` tồn tại, bắt buộc.
- [ ] `deploy/schema/fingerprints.json` golden committed.
- [ ] Makefile: mọi target Python qua `$(PYTHON)`/`$(PYTEST)`; header ghi rõ quy ước.
- [ ] `docs/operations/migrations.md` §29.6 cập nhật: Gate D = IMPLEMENTED, kèm tên job.

## Rủi ro

- Fingerprint quá nhạy (bắt cả thay đổi vô hại như comment/OID) → chuẩn hoá kỹ, chỉ lấy field ngữ nghĩa.
- `migrate-all` cần cả Node deps của `services/*` → job phải `npm ci` cho `services/cosa` + `services/company` trước (giống `quality-integration`).
- Golden drift giữa dev machines (Postgres minor version khác) → pin `pg16` trong CI là nguồn sự thật; dev chỉ tham khảo.

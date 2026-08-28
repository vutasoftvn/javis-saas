# COSA Local-First Event-Driven Agent Operating Model — P2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chốt một evidence-based gate cho quyết định broker: không cài Kafka/Redpanda/NATS mặc định; chỉ đánh giá lại khi số đo vận hành thật của Postgres outbox relay chứng minh không đáp ứng — và khi đó broker là profile *per Workspace Runtime Node*, không phải điểm đến VPS trung tâm.

**Architecture:** Không có code runtime mới. P2 hoàn thiện `ADR-LOCAL-EVENT-BACKBONE-001` (khung đã tạo ở P0 Task 1) thành decision record đầy đủ với: catalogue số đo đo được + nguồn, ngưỡng SLO khởi điểm, ba outcome khả dĩ, tiền điều kiện adoption, bất biến migration; một tài liệu capacity review chạy hằng quý; cập nhật runbook; và một test guard chặn Kafka/VPS-centralized lọt vào manifest hoặc ADR bị rút ruột.

**Tech Stack:** Markdown (ADR + runbook + capacity review). Python 3.11 + pytest cho test guard. Không migration, không service code.

**Spec:** `docs/superpowers/specs/2026-08-28-event-driven-agent-operating-model-design.md` (commit `cb080b77`). Plan này phủ **P2** = spec Task 9. Đi sau **P0** (cần `ADR-LOCAL-EVENT-BACKBONE-001` stub từ P0 Task 1 + `event-driven-agent-runtime-runbook.md` từ P0 Task 5 + tên metric từ P0 Task 5) và, để có số đo thật, sau khi P0 đã chạy pilot/production một khoảng.

## Global Constraints

- **TDD**: test guard đỏ → xác nhận đỏ → viết doc → xác nhận xanh → commit.
- **An toàn working tree** (CLAUDE.md #10): `git status` trước; không `--force`/`--no-verify`; không tự xoá/archive file khác. Commit chỉ pathspec của plan này (`git commit <path> -m ...`) để không gom nhầm thay đổi đang staged của tiến trình khác.
- **Không cài broker.** P2 không được thêm `kafka`/`redpanda`/`nats` vào bất kỳ `docker-compose*.yml`, manifest deploy, hay dependency file nào. Test `test_no_broker_in_deployment_manifests` (P0 Task 1) phải vẫn xanh.
- **`ADR-LOCAL-EVENT-BACKBONE-001` chỉ chuyển sang `ACCEPTED` khi có ≥1 chu kỳ capacity review với dữ liệu thật.** Cho tới đó giữ `PROPOSED`.
- **Số đo phải sanitize** trước khi rời local node (ADR-LOCAL-FIRST-001 §Data residency): chỉ aggregate/histogram, không raw payload, không workspace business content. Capacity review dùng số đo tổng hợp.
- **DoD P2** (spec §7 #9): capacity review phải diễn ra trước khi Kafka/Redpanda/NATS vào bất kỳ deployment manifest.
- **Comment/nội dung tiếng Việt cho phần why**; giữ nguyên cụm khoá tiếng Anh (metric names, SLO terms).

---

## Dependencies vào các plan khác

| Cần | Nguồn | Vì sao |
| --- | --- | --- |
| `docs/architecture/adr/ADR-LOCAL-EVENT-BACKBONE-001.md` (khung: `## Status`, `## Decision inputs`, `## Candidate outcomes`, `## Migration invariants`) | P0 Task 1 Step 4 | P2 điền thân, không tạo lại. `tests/architecture/test_adr_local_first_references.py::test_backbone_adr_stub_exists` đang assert `## Decision inputs` — không đổi tên heading đó. |
| `docs/operations/event-driven-agent-runtime-runbook.md` | P0 Task 5 Step 7 | P2 thêm section "Capacity review & broker gate" + link 2 chiều với ADR. |
| Tên metric: `event_delivery_latency_seconds`, `event_retry_total`, `event_dlq_total`, `event_dedupe_total`, `trigger_denied_total`, `trigger_no_rule_total`, `event_run_outcome_total` | P0 Task 5 Step 2/4 | Capacity catalogue map từng decision input tới metric có sẵn; nêu rõ metric nào còn thiếu (chỉ *đề xuất* thêm gauge, không implement ở P2). |
| Dữ liệu vận hành thật (≥1 quý pilot/production) | Vận hành P0 | Không có số thật thì capacity review chỉ ghi "insufficient data — keep Postgres outbox relay". |

---

## File Structure

| File | Trách nhiệm sau khi implement |
| --- | --- |
| `docs/architecture/adr/ADR-LOCAL-EVENT-BACKBONE-001.md` | Decision record đầy đủ: 8 decision input + nguồn + ngưỡng SLO khởi điểm; 3 outcome; 3 tiền điều kiện adoption; bất biến migration; điều kiện chuyển `PROPOSED → ACCEPTED`. |
| `docs/operations/event-backbone-capacity-review.md` | Template + log các chu kỳ review hằng quý: bảng số đo quan sát vs SLO, verdict, người ký, ngày. Chu kỳ đầu điền "insufficient data / keep Postgres outbox relay". |
| `docs/operations/event-driven-agent-runtime-runbook.md` | Thêm section "Capacity review & broker gate": cách kéo số đo, khi nào mở review sớm (ngoài lịch quý), ai ký verdict, link ADR. |
| `tests/architecture/test_event_backbone_adr_references.py` | Guard: ADR liệt kê đủ 8 decision input + 3 outcome + 3 precondition; capacity review doc tồn tại + có bảng metric; runbook link ADR; không broker trong manifest (tái dùng assertion P0). |

---

### Task 1: Capacity metrics catalogue + quarterly review log

**Files:**
- Create: `docs/operations/event-backbone-capacity-review.md`
- Modify: `docs/operations/event-driven-agent-runtime-runbook.md` (thêm 1 section)
- Test: `tests/architecture/test_event_backbone_adr_references.py` (phần capacity-review, viết cùng Task 2 nhưng assertion cho file này ở đây)

**Interfaces:**
- Consumes: tên metric P0 Task 5; runbook P0 Task 5.
- Produces: `docs/operations/event-backbone-capacity-review.md` với 2 phần cố định — `## How to run a review` và `## Review log` (bảng append-only). Mỗi entry review có cột: `Quarter`, `Data window`, `p95 delivery latency`, `Sustained outbox backlog`, `Consumer fan-out`, `Replay window`, `Node resource`, `Operator MTTR`, `Storage cost`, `Verdict`, `Signed-off by`, `Date`.

- [ ] **Step 1: Viết `event-backbone-capacity-review.md`**

Create the file with these sections (nội dung tiếng Việt cho giải thích, giữ term tiếng Anh):

- `# Event backbone capacity review` — mục đích: cung cấp dữ liệu đo được cho `ADR-LOCAL-EVENT-BACKBONE-001`; chạy **hằng quý** hoặc **sớm hơn** nếu một SLO bị vi phạm liên tục > 15 phút trong production.
- `## Decision inputs & sources` — bảng:

  | Decision input | Nguồn số đo | SLO khởi điểm (review lại mỗi quý) |
  | --- | --- | --- |
  | p95 delivery latency (outbox append → inbox recorded) | `event_delivery_latency_seconds` histogram (P0 Task 5) | p95 ≤ 5s steady, ≤ 30s under retry |
  | Sustained outbox backlog | `event_outbox_backlog` gauge *(chưa có — xem "Metric gaps")* + query `SELECT count(*) FROM integration.event_outbox WHERE status='pending'` | age p95 của `pending` ≤ 60s; count < 1000 sustained |
  | Consumer fan-out | Số `consumer_name` phân biệt trong `event_inbox` theo `event_type` | ≤ 5 consumer/event type với thiết kế single-relay hiện tại |
  | Replay window | Thời gian replay 24h outbox (đo thủ công khi drill) | ≤ 10 phút cho một ngày |
  | Node resource use | Host metrics (CPU%, RSS) của process relay + Postgres outbox load | relay < 10% CPU node, < 500MB RSS |
  | Operator recovery time | Incident log MTTR cho sự cố "relay stuck" | ≤ 15 phút với runbook |
  | Data-residency requirement | Chính sách hiện hành (ADR-LOCAL-FIRST-001) | Business payload không rời local node — bất kỳ broker nào cũng phải giữ ràng buộc này |
  | Storage cost | Kích thước `integration.event_outbox` sau retention 30d, theo workspace | < 2 GB/workspace ở tải dự kiến |

- `## Metric gaps` — liệt kê metric còn thiếu để review đầy đủ (chỉ *đề xuất*, không implement ở P2): `event_outbox_backlog` gauge (số `pending` + tuổi row cũ nhất), `event_replay_duration_seconds` (đo trong drill). Ticket để thêm khi mở review thật đầu tiên.
- `## How to run a review` — 5 bước: (1) chọn data window (quý gần nhất, tối thiểu 30 ngày production); (2) kéo từng số đo ở bảng trên; (3) so với SLO; (4) áp `## Adoption preconditions` của ADR — cả ba phải thoả mới cân nhắc PoC broker; (5) ghi verdict vào `## Review log`, ký tên (owner event runtime + một reviewer độc lập).
- `## Review log` — bảng append-only (cột như Interfaces). Điền **entry đầu tiên** ngay: `Quarter = <quý hiện tại>`, `Data window = N/A`, mọi cột số đo = `insufficient data`, `Verdict = keep Postgres outbox relay (no broker)`, `Signed-off by = <để trống cho người chạy điền>`, `Date = <ngày tạo>`.

- [ ] **Step 2: Thêm section vào runbook**

Trong `docs/operations/event-driven-agent-runtime-runbook.md`, thêm `## Capacity review & broker gate`:
- Link tới `docs/operations/event-backbone-capacity-review.md` và `docs/architecture/adr/ADR-LOCAL-EVENT-BACKBONE-001.md`.
- "Broker KHÔNG được cài mặc định. Trước khi bất kỳ ai thêm `kafka`/`redpanda`/`nats` vào manifest: phải có một entry `## Review log` với verdict cho phép PoC và cả ba `## Adoption preconditions` được đánh dấu thoả."
- Khi nào mở review sớm ngoài lịch quý: SLO `p95 delivery latency` hoặc `sustained outbox backlog` bị vi phạm liên tục > 15 phút trong production (alert từ metric P0 Task 5).
- Ai ký verdict: owner event runtime + một reviewer độc lập.

- [ ] **Step 3: (assertion cho file này — chạy cùng Task 2 Step 3)**

Không có lệnh riêng ở bước này; `tests/architecture/test_event_backbone_adr_references.py` (Task 2) chứa `test_capacity_review_doc_lists_all_inputs` và `test_capacity_review_has_log_table`.

- [ ] **Step 4: Commit**

```bash
git status                     # xác nhận không có gì lạ đang staged
git add docs/operations/event-backbone-capacity-review.md docs/operations/event-driven-agent-runtime-runbook.md
git commit docs/operations/event-backbone-capacity-review.md docs/operations/event-driven-agent-runtime-runbook.md \
  -m "docs(ops): event backbone capacity review template + runbook broker gate"
```

---

### Task 2: Fill ADR-LOCAL-EVENT-BACKBONE-001 + reference guard

**Files:**
- Modify: `docs/architecture/adr/ADR-LOCAL-EVENT-BACKBONE-001.md` (điền thân, giữ heading stub)
- Create: `tests/architecture/test_event_backbone_adr_references.py`

**Interfaces:**
- Consumes: ADR stub (P0 Task 1 Step 4) — heading `## Status`, `## Decision inputs`, `## Candidate outcomes`, `## Migration invariants` đã có; P2 giữ tên, thêm nội dung + thêm heading `## Adoption preconditions` và `## Promotion of this ADR`.
- Produces: ADR đầy đủ + `tests/architecture/test_event_backbone_adr_references.py` với các test: `test_adr_lists_all_decision_inputs`, `test_adr_lists_three_candidate_outcomes`, `test_adr_lists_three_adoption_preconditions`, `test_adr_status_is_proposed_until_review`, `test_runbook_links_backbone_adr`, `test_capacity_review_doc_lists_all_inputs`, `test_capacity_review_has_log_table`, `test_no_broker_in_deployment_manifests` (tái dùng logic P0).

- [ ] **Step 1: Viết test guard đỏ**

Create `tests/architecture/test_event_backbone_adr_references.py`:

```python
"""Guard: quyết định broker phải dựa capacity review có số đo, không phải
sở thích vendor; và không có broker nào lọt vào manifest trước review."""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADR = REPO / "docs/architecture/adr/ADR-LOCAL-EVENT-BACKBONE-001.md"
CAPACITY = REPO / "docs/operations/event-backbone-capacity-review.md"
RUNBOOK = REPO / "docs/operations/event-driven-agent-runtime-runbook.md"

DECISION_INPUTS = [
    "p95 delivery latency", "sustained outbox backlog", "consumer fan-out",
    "replay window", "node resource", "operator recovery time",
    "data-residency", "cost",
]
OUTCOMES = [
    "keep Postgres outbox relay",
    "local optional broker profile",
    "reject broker",
]
PRECONDITIONS = [
    "unmet documented Postgres outbox SLO",
    "independently scalable fan-out/replay",
    "operator-approved local deployment/backup model",
]


def _norm(p: Path) -> str:
    return p.read_text(encoding="utf-8").lower()


def test_adr_lists_all_decision_inputs() -> None:
    text = _norm(ADR)
    missing = [k for k in DECISION_INPUTS if k.lower() not in text]
    assert not missing, f"ADR missing decision inputs: {missing}"


def test_adr_lists_three_candidate_outcomes() -> None:
    text = _norm(ADR)
    missing = [k for k in OUTCOMES if k.lower() not in text]
    assert not missing, f"ADR missing outcomes: {missing}"


def test_adr_lists_three_adoption_preconditions() -> None:
    text = _norm(ADR)
    missing = [k for k in PRECONDITIONS if k.lower() not in text]
    assert not missing, f"ADR missing adoption preconditions: {missing}"


def test_adr_status_is_proposed_until_review() -> None:
    # Chưa có chu kỳ review với dữ liệu thật → Status phải là PROPOSED.
    m = re.search(r"^##\s*Status\s*\n+(.+)$", ADR.read_text("utf-8"), re.MULTILINE)
    assert m and "proposed" in m.group(1).lower(), "ADR Status must stay PROPOSED until a real review"


def test_runbook_links_backbone_adr() -> None:
    assert "ADR-LOCAL-EVENT-BACKBONE-001" in RUNBOOK.read_text("utf-8")


def test_capacity_review_doc_lists_all_inputs() -> None:
    text = _norm(CAPACITY)
    missing = [k for k in DECISION_INPUTS if k.lower() not in text]
    assert not missing, f"capacity review missing inputs: {missing}"


def test_capacity_review_has_log_table() -> None:
    text = CAPACITY.read_text("utf-8")
    assert "## Review log" in text
    assert "keep Postgres outbox relay (no broker)" in text  # entry đầu tiên


def test_no_broker_in_deployment_manifests() -> None:
    pattern = re.compile(r"\b(kafka|redpanda|nats)\b", re.IGNORECASE)
    hits: list[str] = []
    for g in ["deploy/**/*.y*ml", "docker-compose*.y*ml", "**/k8s/**/*.y*ml", "infra/**/*.y*ml"]:
        for path in REPO.glob(g):
            if "node_modules" in path.parts:
                continue
            if pattern.search(path.read_text("utf-8", errors="ignore")):
                hits.append(str(path.relative_to(REPO)))
    assert not hits, f"broker reference in deployment manifest(s): {hits}"
```

- [ ] **Step 2: Chạy — xác nhận đỏ**

Run: `PYTHONPATH=. .venv/bin/pytest tests/architecture/test_event_backbone_adr_references.py -q`
Expected: FAIL — ADR stub chưa có decision inputs / outcomes / preconditions dưới dạng text; `test_capacity_review_*` FAIL nếu Task 1 chưa xong (chạy Task 1 trước).

- [ ] **Step 3: Điền `ADR-LOCAL-EVENT-BACKBONE-001.md`**

Giữ nguyên các heading stub, thêm nội dung:

- `## Status` — `PROPOSED — awaiting first capacity review with production/pilot data`. Ghi: chuyển `ACCEPTED` chỉ khi `## Promotion of this ADR` thoả.
- `## Context` — Postgres transactional outbox relay là backbone P0/P1 (ADR-LOCAL-FIRST-001). Có áp lực định kỳ đề xuất Kafka "cho scale"; ADR này đặt gate dựa số đo, không sở thích vendor. Business payload không rời local node — ràng buộc này áp cho mọi backbone kể cả broker.
- `## Decision inputs` — 8 dòng, mỗi dòng nêu input + nguồn số đo + SLO khởi điểm (copy bảng từ `event-backbone-capacity-review.md` §"Decision inputs & sources"; hai file phải khớp). Bắt buộc chứa nguyên văn 8 cụm: `p95 delivery latency`, `sustained outbox backlog`, `consumer fan-out`, `replay window`, `node resource use`, `operator recovery time`, `data-residency requirement`, `cost`.
- `## Candidate outcomes` — đúng 3, mô tả mỗi cái:
  1. **keep Postgres outbox relay** — mặc định; không thay đổi hạ tầng.
  2. **add a local optional broker profile** — broker (Kafka/Redpanda/NATS) chạy **per Workspace Runtime Node**, nhận **cùng** `BusinessEventEnvelope` + inbox idempotency contract; **không bao giờ** là điểm đến VPS trung tâm cho business event; opt-in per node.
  3. **reject broker** — kết luận outbox relay đủ; đóng đề xuất trong chu kỳ này.
- `## Adoption preconditions` — cả ba PHẢI thoả trước bất kỳ PoC broker:
  1. Ít nhất một **unmet documented Postgres outbox SLO** (có entry trong `## Review log` với số đo vi phạm).
  2. Một workload thực sự cần **independently scalable fan-out/replay** mà single-relay không đáp ứng (fan-out > 5 consumer/event type, hoặc replay 24h > 10 phút).
  3. Một **operator-approved local deployment/backup model** cho broker trên Workspace Runtime Node (không tăng bề mặt vận hành ngoài tầm kiểm soát; giữ được data residency).
- `## Migration invariants` — nếu adopt broker: giữ nguyên `BusinessEventEnvelope` (schema JSON dùng chung) và inbox idempotency key `(workspace_id, event_id, consumer_name)`; outbox vẫn là điểm ghi trong domain transaction (broker là transport phía sau relay, không thay outbox); relay đổi target từ HTTP intake sang broker publish nhưng at-least-once + post-condition verification không đổi.
- `## Promotion of this ADR` — `Status` chuyển `ACCEPTED` khi: có ≥1 entry `## Review log` với `Data window` ≥ 30 ngày production data VÀ verdict được ký bởi owner event runtime + một reviewer độc lập. Trước đó giữ `PROPOSED`.
- `## Relates` — `ADR-LOCAL-FIRST-001` (§Event backbone).

- [ ] **Step 4: Chạy — xác nhận xanh**

Run: `PYTHONPATH=. .venv/bin/pytest tests/architecture/ -q`
Expected: PASS toàn bộ (`test_adr_local_first_references.py` từ P0 vẫn xanh + `test_event_backbone_adr_references.py` mới xanh).

- [ ] **Step 5: Commit**

```bash
git status
git add docs/architecture/adr/ADR-LOCAL-EVENT-BACKBONE-001.md tests/architecture/test_event_backbone_adr_references.py
git commit docs/architecture/adr/ADR-LOCAL-EVENT-BACKBONE-001.md tests/architecture/test_event_backbone_adr_references.py \
  -m "docs(adr): fill event backbone capacity gate + reference guard test"
```

---

## Self-Review

**Spec coverage (P2 = spec Task 9):**

| Spec requirement | Plan task |
| --- | --- |
| Evidence-based decision record với 3 outcome (keep Postgres / add local broker profile / reject) | Task 2 Step 3 `## Candidate outcomes` |
| Broker (nếu duyệt) deploy per Workspace Runtime Node, cùng envelope/inbox contract, không bao giờ default VPS destination | Task 2 Step 3 outcome #2 + `## Migration invariants` |
| Collected metrics: p95 delivery latency, sustained outbox backlog, consumer fan-out, replay window, node resource use, operator recovery time, data-residency requirement, cost | Task 1 Step 1 bảng "Decision inputs & sources" + Task 2 Step 3 `## Decision inputs` (khớp nhau) |
| Quarterly capacity review dùng dữ liệu production/pilot thật | Task 1 Step 1 `## How to run a review` + `## Review log` (append-only, entry đầu = insufficient data) |
| Adoption criteria: ≥1 unmet documented Postgres outbox SLO + workload cần fan-out/replay scale độc lập + operator-approved local deploy/backup model | Task 2 Step 3 `## Adoption preconditions` |
| Migration invariants: giữ outbox envelope + inbox idempotency | Task 2 Step 3 `## Migration invariants` |
| ADR/runbook references chặn deploy Kafka/VPS centralized chưa review | Task 2 Step 1 `test_no_broker_in_deployment_manifests` + `test_runbook_links_backbone_adr` + Task 1 Step 2 runbook section |
| DoD #9 — capacity review phải diễn ra trước khi Kafka/Redpanda/NATS vào manifest | Runbook section (Task 1 Step 2) + test guard (Task 2 Step 1) + ADR `## Adoption preconditions` |

**Placeholder scan:** Không "TBD"/"handle edge cases". SLO khởi điểm là số cụ thể (5s / 1000 rows / 5 consumers / 10 phút / 10% CPU / 15 phút MTTR / 2 GB) — đánh dấu rõ "review lại mỗi quý", không phải placeholder. `## Review log` entry đầu điền sẵn verdict "keep Postgres outbox relay (no broker)". Chỗ duy nhất để trống có chủ đích: `Signed-off by` của entry đầu (người chạy plan điền tên thật) — đây là dữ liệu vận hành, không phải nội dung plan.

**Internal consistency:** Bảng 8 decision input xuất hiện ở cả `event-backbone-capacity-review.md` (Task 1) và `ADR-LOCAL-EVENT-BACKBONE-001.md` (Task 2) — Task 2 Step 3 ghi rõ "copy bảng, hai file phải khớp"; test `test_adr_lists_all_decision_inputs` + `test_capacity_review_doc_lists_all_inputs` dùng chung list `DECISION_INPUTS` nên lệch sẽ fail. `## Status = PROPOSED` được test `test_adr_status_is_proposed_until_review` khoá — khớp với constraint "chỉ ACCEPTED sau ≥1 review thật".

**Type/name consistency:** Heading stub từ P0 Task 1 (`## Status`, `## Decision inputs`, `## Candidate outcomes`, `## Migration invariants`) giữ nguyên; P0 test `test_backbone_adr_stub_exists` assert `## Decision inputs` — không đổi. Metric names khớp P0 Task 5 (`event_delivery_latency_seconds` v.v.).

---

## Verification (end-to-end, sau Task 2)

```
PYTHONPATH=. .venv/bin/pytest tests/architecture -q
```
Expected: PASS — `test_adr_local_first_references.py` (P0) + `test_event_backbone_adr_references.py` (P2) đều xanh.

**Manual:**
1. Mở `docs/architecture/adr/ADR-LOCAL-EVENT-BACKBONE-001.md` → `## Status` = `PROPOSED`; có đủ 8 decision input, 3 outcome, 3 adoption precondition, `## Migration invariants`, `## Promotion of this ADR`.
2. Mở `docs/operations/event-backbone-capacity-review.md` → có `## How to run a review` (5 bước) + `## Review log` với 1 entry verdict "keep Postgres outbox relay (no broker)".
3. `grep -rniE 'kafka|redpanda|nats' deploy/ docker-compose*.yml infra/ 2>/dev/null` → 0 kết quả.
4. Runbook có section `## Capacity review & broker gate` link tới cả ADR và capacity review doc.
5. Thử thêm `kafka:` vào một `docker-compose*.yml` tạm → `pytest tests/architecture -q` FAIL (`test_no_broker_in_deployment_manifests`) → revert.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-28-event-driven-agent-operating-model-p2.md`. Thực thi **sau P0**; lý tưởng là sau khi P0 đã chạy production/pilot ≥30 ngày để `## Review log` entry đầu có số đo thật thay vì "insufficient data". Hai lựa chọn:

1. **Subagent-Driven** — subagent riêng mỗi task.
2. **Inline Execution** — executing-plans; P2 nhỏ, 2 task, phù hợp chạy inline.

Which approach?

Plan này không thêm code runtime, không migration, không cài broker, không cho phép deploy VPS hay xoá dữ liệu. Đây là plan cuối của bộ (P0 → P1 → P2) cho spec `2026-08-28-event-driven-agent-operating-model-design.md`.

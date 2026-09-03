# Điều chỉnh theo khuyến nghị (05-khuyen-nghi.md) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Triển khai các mục sửa-ngay-được trong
`docs/architecture/overview/05-khuyen-nghi.md`: fix vi phạm rule #7 (B2),
hợp nhất `frontend/lib/features/` vào `modules/` (B4), hoàn thiện wiring
`services/company/academy/` từ in-memory sang Encore + Drizzle thật (B1),
và sửa 3 chỗ doc-drift (C1-C3).

**Architecture:** Không đổi kiến trúc tổng thể — chỉ vá nợ kỹ thuật cục bộ
trong 3 vùng độc lập (Python agent runtime, Flutter frontend, Encore/TS
company service) theo đúng pattern đã có trong từng vùng, không phát minh
pattern mới.

**Tech Stack:** Python 3.11 + pytest + Pydantic (Task 1); Flutter/Dart +
`flutter_test` (Task 2); TypeScript + Encore.ts + Drizzle ORM + vitest
(Task 3-6); Markdown (Task 7).

## Global Constraints

- Toàn bộ comment/docstring mới viết bằng tiếng Việt cho phần giải thích ý
  nghĩa; định danh/route/log giữ tiếng Anh (CLAUDE.md).
- Handler Encore (`*.handler.ts`) KHÔNG được import `drizzle-orm`,
  `models/db`, `db.ts`, hay schema trực tiếp — chỉ gọi vào `services/*.ts`
  (Encore Guardrail #1, kiểm bởi `scripts/check_encore_handler_boundaries.mjs`).
- Lỗi từ API công khai dùng `APIError` (`invalidArgument`/`notFound`/
  `internal`...), không `throw new Error` trần trong lớp service/handler
  (Encore Guardrail #3) — riêng `contracts.ts` giữ nguyên `throw new
  Error` vì đây là lớp cô lập domain-level, không phải handler.
- ID mới cho bảng academy dùng `generateSnowflake()` (bigint), không dùng
  chuỗi tự chế kiểu `enr_${Date.now()}...` (ADR-ID-MODEL-001).
- Migration chỉ Expand ở release này — không đổi schema `academy.ts`/SQL
  đã có, chỉ đăng ký để nó chạy được.
- Mỗi task 1 commit riêng, không gộp nhiều task vào 1 commit.
- Không tự ý sửa `services/cosa` company RPC hay bất cứ gì thuộc Nhóm A/B3
  trong 05-khuyen-nghi.md — nằm ngoài phạm vi plan này.

---

## Task 1: Structured state cho PromotionGate (B2)

**Files:**
- Modify: `packages/agent/evals/promotion_gate.py`
- Modify: `apps/cosa/events/trigger_promotion.py:41-42`
- Modify: `tests/agent/evals/test_promotion_gate.py`
- Test (không đổi logic, chỉ chạy lại): `tests/apps/cosa/test_event_trigger_promotion.py`

**Interfaces:**
- Produces: `PromotionIssueCode` (enum, `packages/agent/evals/promotion_gate.py`)
  với 4 member: `POLICY_VERSION_MISMATCH`, `NO_EVAL_RUN`, `CHECKS_NOT_PASSED`,
  `EVIDENCE_STALE`; `PromotionGateResult.blocking_issue_codes: list[PromotionIssueCode]`
  (field mới, additive — `blocking_issues: list[str]` giữ nguyên).

- [ ] **Step 1: Viết test mới cho `blocking_issue_codes` (RED)**

Sửa `tests/agent/evals/test_promotion_gate.py`, thêm import và cập nhật 4
test case đang reject để assert thêm trên code:

```python
from agent.evals.promotion_gate import PromotionGate, PromotionIssueCode
```

Sửa `test_promotion_gate_rejects_stale_evidence`:

```python
def test_promotion_gate_rejects_stale_evidence():
    gate = PromotionGate(policy_version="1")

    result = gate.check(_valid_evidence(), current_fingerprints={"cofounder": "c" * 64})

    assert result.approved is False
    assert any("stale" in issue.lower() for issue in result.blocking_issues)
    assert PromotionIssueCode.EVIDENCE_STALE in result.blocking_issue_codes
```

Sửa `test_promotion_gate_rejects_when_policy_checks_not_passed`:

```python
def test_promotion_gate_rejects_when_policy_checks_not_passed():
    evidence = _valid_evidence().model_copy(update={"policy_checks_passed": False})
    gate = PromotionGate(policy_version="1")

    result = gate.check(evidence, current_fingerprints={"cofounder": "a" * 64})

    assert result.approved is False
    assert any("chưa pass" in issue for issue in result.blocking_issues)
    assert PromotionIssueCode.CHECKS_NOT_PASSED in result.blocking_issue_codes
```

Sửa `test_promotion_gate_rejects_when_no_eval_run_ids`:

```python
def test_promotion_gate_rejects_when_no_eval_run_ids():
    evidence = _valid_evidence().model_copy(update={"required_eval_run_ids": []})
    gate = PromotionGate(policy_version="1")

    result = gate.check(evidence, current_fingerprints={"cofounder": "a" * 64})

    assert result.approved is False
    assert PromotionIssueCode.NO_EVAL_RUN in result.blocking_issue_codes
```

Sửa `test_promotion_gate_rejects_when_policy_version_mismatches`:

```python
def test_promotion_gate_rejects_when_policy_version_mismatches():
    gate = PromotionGate(policy_version="2")

    result = gate.check(_valid_evidence(), current_fingerprints={"cofounder": "a" * 64})

    assert result.approved is False
    assert any("policy_version" in issue for issue in result.blocking_issues)
    assert PromotionIssueCode.POLICY_VERSION_MISMATCH in result.blocking_issue_codes
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `.venv/bin/python -m pytest tests/agent/evals/test_promotion_gate.py -v`
Expected: FAIL — `ImportError: cannot import name 'PromotionIssueCode'`.

- [ ] **Step 3: Thêm `PromotionIssueCode` + `blocking_issue_codes` vào `promotion_gate.py`**

Thay toàn bộ `packages/agent/evals/promotion_gate.py` bằng:

```python
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from agent.evals.promotion import PromotionEvidence
from agent.governance.contracts import PinnedSpecIdentity

__all__ = ["PromotionGate", "PromotionGateResult", "PromotionIssueCode"]


class PromotionIssueCode(str, Enum):
    """Reason code có cấu trúc cho từng lý do reject — dùng để caller (vd.
    apps/cosa/events/trigger_promotion.py) rẽ nhánh theo code thay vì
    string-match trên `blocking_issues` (message tiếng Việt tự do, chỉ để
    hiển thị người dùng, không dùng để suy diễn logic)."""

    POLICY_VERSION_MISMATCH = "policy_version_mismatch"
    NO_EVAL_RUN = "no_eval_run"
    CHECKS_NOT_PASSED = "checks_not_passed"
    EVIDENCE_STALE = "evidence_stale"


class PromotionGateResult(BaseModel):
    """Kết quả kiểm tra — CHỈ là dữ liệu, không có side effect. Caller
    (services/cosa) tự quyết định làm gì với `approved`/`blocking_issues`."""

    approved: bool
    blocking_issues: list[str] = Field(default_factory=list)
    blocking_issue_codes: list[PromotionIssueCode] = Field(default_factory=list)
    target_ref: PinnedSpecIdentity
    evidence_id: str


class PromotionGate:
    """Kiểm tra PromotionEvidence có đủ điều kiện promote hay không — CHỈ
    trả kết quả kiểm tra, KHÔNG tự activate/promote gì. Quyền quyết định
    cuối cùng (PromotionDecision) thuộc services/cosa, xem
    docs/implementation/M4_PROMOTION_CONTROL_PLANE_BOUNDARY.md."""

    def __init__(self, policy_version: str) -> None:
        self._policy_version = policy_version

    def check(
        self, evidence: PromotionEvidence, current_fingerprints: dict[str, str]
    ) -> PromotionGateResult:
        issues: list[str] = []
        codes: list[PromotionIssueCode] = []

        if evidence.policy_version != self._policy_version:
            issues.append(
                f"Evidence dùng policy_version '{evidence.policy_version}', "
                f"gate hiện yêu cầu '{self._policy_version}'"
            )
            codes.append(PromotionIssueCode.POLICY_VERSION_MISMATCH)
        if not evidence.required_eval_run_ids:
            issues.append("Evidence không có eval_run_id nào — chưa từng eval")
            codes.append(PromotionIssueCode.NO_EVAL_RUN)
        if not evidence.policy_checks_passed:
            issues.append("Eval checks trong evidence chưa pass (policy_checks_passed=False)")
            codes.append(PromotionIssueCode.CHECKS_NOT_PASSED)
        if evidence.is_stale(current_fingerprints):
            issues.append(
                "Evidence stale — fingerprint (target hoặc dependency) đã đổi kể từ khi tạo evidence"
            )
            codes.append(PromotionIssueCode.EVIDENCE_STALE)

        return PromotionGateResult(
            approved=len(issues) == 0,
            blocking_issues=issues,
            blocking_issue_codes=codes,
            target_ref=evidence.target_ref,
            evidence_id=evidence.evidence_id,
        )
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `.venv/bin/python -m pytest tests/agent/evals/test_promotion_gate.py -v`
Expected: PASS toàn bộ.

- [ ] **Step 5: Sửa `trigger_promotion.py` dùng code thay string-match**

Sửa `apps/cosa/events/trigger_promotion.py`:

```python
from agent.evals.promotion import PromotionEvidence
from agent.evals.promotion_gate import PromotionGate, PromotionIssueCode
```

Thay dòng 41-42:

```python
    gate = PromotionGate(policy_version=policy_version).check(evidence, current_fingerprints)
    if not gate.approved:
        stale = PromotionIssueCode.EVIDENCE_STALE in gate.blocking_issue_codes
        return GateResult(False, "stale_evidence" if stale else "checks_failed")
```

- [ ] **Step 6: Chạy lại test cũ của trigger_promotion, xác nhận không vỡ**

Run: `.venv/bin/python -m pytest tests/apps/cosa/test_event_trigger_promotion.py tests/agent/evals/test_promotion_gate.py -v`
Expected: PASS toàn bộ (10 test trigger_promotion + 6 test promotion_gate).

- [ ] **Step 7: Commit**

```bash
git add packages/agent/evals/promotion_gate.py apps/cosa/events/trigger_promotion.py tests/agent/evals/test_promotion_gate.py
git commit -m "fix(agent): dùng PromotionIssueCode thay string-match cho stale evidence

Nguyên tắc bắt buộc #7 (CLAUDE.md) cấm suy diễn trạng thái từ text tự do.
trigger_promotion.py trước đó match \"stale\" in issue.lower() trên message
tiếng Việt tự do — dễ vỡ nếu câu chữ đổi. Thêm PromotionIssueCode enum,
giữ nguyên blocking_issues (text) để hiển thị, thêm blocking_issue_codes
(structured) để logic dựa vào.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: Frontend — di dời `features/_shared` sang `shared/`, xoá `features/` (B4)

**Files:**
- Move: `frontend/lib/features/_shared/presentation/async_feature_state.dart` → `frontend/lib/shared/state/async_feature_state.dart`
- Move: `frontend/lib/features/_shared/presentation/feature_state_view.dart` → `frontend/lib/shared/widgets/feature_state_view.dart`
- Move: `frontend/test/features/shared/async_feature_state_test.dart` → `frontend/test/shared/state/async_feature_state_test.dart`
- Modify: `frontend/lib/modules/approvals/controllers/approvals_controller.dart:8`
- Modify: `frontend/lib/modules/approvals/views/approvals_view.dart:4`
- Modify: `frontend/test/modules/approvals/approvals_controller_test.dart:12`
- Delete: `frontend/lib/features/` (toàn bộ 7 thư mục con), `frontend/test/features/`

**Interfaces:**
- Consumes: không có (di dời file thuần, không đổi API public của
  `AsyncFeatureState<T>`/`FeatureStateView<T>`).
- Produces: `package:frontend/shared/state/async_feature_state.dart`
  (export `AsyncFeatureState`, `FeatureInitial`, `FeatureLoading`,
  `FeatureData`, `FeatureFailure`, `FeatureNotObserved`) và
  `package:frontend/shared/widgets/feature_state_view.dart` (export
  `FeatureStateView<T>`) — thay thế hoàn toàn 2 file cũ dưới `features/`.

Đã xác nhận qua khảo sát: 6 thư mục `features/{settings,strategy,vault,
workforce,workspace_runtime,marketing}` chỉ chứa facade 2 dòng, KHÔNG được
import bởi bất kỳ file nào trong `lib/` — xoá thẳng, không cần di dời gì.

- [ ] **Step 1: Tạo thư mục đích và di dời 2 file thật bằng `git mv`**

```bash
mkdir -p frontend/lib/shared/state frontend/lib/shared/widgets frontend/test/shared/state
git mv frontend/lib/features/_shared/presentation/async_feature_state.dart frontend/lib/shared/state/async_feature_state.dart
git mv frontend/lib/features/_shared/presentation/feature_state_view.dart frontend/lib/shared/widgets/feature_state_view.dart
git mv frontend/test/features/shared/async_feature_state_test.dart frontend/test/shared/state/async_feature_state_test.dart
```

- [ ] **Step 2: Sửa import nội bộ trong `feature_state_view.dart`**

File `frontend/lib/shared/widgets/feature_state_view.dart` dòng 1-4 hiện là:

```dart
import 'package:flutter/material.dart';

import '../../../core/network/api_result.dart';
import 'async_feature_state.dart';
```

Sửa thành (đường dẫn tương đối đổi vì đã chuyển thư mục):

```dart
import 'package:flutter/material.dart';

import '../../core/network/api_result.dart';
import '../state/async_feature_state.dart';
```

- [ ] **Step 3: Sửa 2 import consumer trong `modules/approvals/`**

`frontend/lib/modules/approvals/controllers/approvals_controller.dart` dòng 8:

```dart
// Trước:
import '../../../features/_shared/presentation/async_feature_state.dart';
// Sau:
import '../../../shared/state/async_feature_state.dart';
```

`frontend/lib/modules/approvals/views/approvals_view.dart` dòng 4:

```dart
// Trước:
import '../../../features/_shared/presentation/feature_state_view.dart';
// Sau:
import '../../../shared/widgets/feature_state_view.dart';
```

- [ ] **Step 4: Sửa import trong 2 test file**

`frontend/test/modules/approvals/approvals_controller_test.dart` dòng 12:

```dart
// Trước:
import 'package:frontend/features/_shared/presentation/async_feature_state.dart';
// Sau:
import 'package:frontend/shared/state/async_feature_state.dart';
```

`frontend/test/shared/state/async_feature_state_test.dart` (file vừa `git mv`
ở Step 1) dòng 2 hiện là:

```dart
import 'package:frontend/features/_shared/public.dart';
```

Sửa thành (facade `public.dart` sẽ bị xoá ở Step 6, nên import trực tiếp cả
2 nguồn nó từng re-export):

```dart
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/shared/state/async_feature_state.dart';
```

- [ ] **Step 5: Chạy test, xác nhận PASS trước khi xoá `features/`**

Run: `cd frontend && flutter test test/shared/state/async_feature_state_test.dart test/modules/approvals/approvals_controller_test.dart`
Expected: PASS toàn bộ (không còn lỗi import).

- [ ] **Step 6: Xoá toàn bộ `features/` (đã hết người dùng)**

```bash
git rm -r frontend/lib/features frontend/test/features
```

- [ ] **Step 7: `flutter analyze` toàn bộ frontend, xác nhận không phát sinh lỗi import**

Run: `cd frontend && flutter analyze`
Expected: không có lỗi mới liên quan `features/` hay `shared/state`/`shared/widgets`
(cảnh báo có sẵn từ trước, nếu có, không tính).

- [ ] **Step 8: Commit**

```bash
git add -A frontend/lib/shared frontend/lib/modules/approvals frontend/test/shared frontend/test/modules/approvals
git add frontend/lib/features frontend/test/features
git commit -m "refactor(frontend): hợp nhất features/_shared vào shared/, xoá features/

features/{settings,strategy,vault,workforce,workspace_runtime,marketing}
chỉ là facade 2 dòng không được import ở đâu — xoá thẳng. Nội dung thật
duy nhất (AsyncFeatureState/FeatureStateView) chuyển sang
lib/shared/{state,widgets}/, cập nhật 2 import consumer trong
modules/approvals/ và 2 test liên quan.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: Academy — hạ tầng DB (encore.service.ts, db.ts, models/, đăng ký migration)

**Files:**
- Create: `services/company/academy/encore.service.ts`
- Create: `services/company/academy/db.ts`
- Create: `services/company/academy/models/db.ts`
- Create: `services/company/academy/models/index.ts`
- Modify: `services/company/scripts/migrate.mjs`

**Interfaces:**
- Produces: `db` (Drizzle client, `NodePgDatabase`), `schema` (đối tượng
  chứa 7 export từ `academy.ts`: `academyPrograms`, `academyModules`,
  `academyLessons`, `academyEnrollments`, `academyLessonAttempts`,
  `academySimulationRuns`, `academyTemplateExports`) — import qua
  `import { db, schema } from "../models/db"` (Task 4, 5 dùng).

- [ ] **Step 1: Tạo `encore.service.ts`**

```ts
import { Service } from "encore.dev/service";

export default new Service("academy");
```

- [ ] **Step 2: Tạo `db.ts`**

```ts
import { createDrizzleClient, DEFAULT_WORKSPACE_DB_URL } from "../shared/db/client";
import * as academySchema from "../shared/db/schema/academy";

const schema = { ...academySchema };
const conn = process.env.WORKSPACE_DATABASE_URL || DEFAULT_WORKSPACE_DB_URL;
export const db = createDrizzleClient(conn, schema);
export { schema };
```

- [ ] **Step 3: Tạo `models/db.ts` và `models/index.ts`**

`services/company/academy/models/db.ts`:

```ts
export { db, schema } from "../db";
```

`services/company/academy/models/index.ts`:

```ts
export * from "./db";
```

- [ ] **Step 4: Đăng ký migration academy vào `migrate.mjs`**

Sửa `services/company/scripts/migrate.mjs`, thêm vào mảng `MIGRATION_DIRS`
(sau dòng `operations`):

```js
const MIGRATION_DIRS = [
  { service: "commercial", dir: join(__dirname, "../commercial/migrations") },
  { service: "finance-legal", dir: join(__dirname, "../finance-legal/migrations") },
  { service: "identity", dir: join(__dirname, "../identity/migrations") },
  { service: "operations", dir: join(__dirname, "../operations/migrations") },
  { service: "academy", dir: join(__dirname, "../academy/migrations") },
];
```

- [ ] **Step 5: Chạy migration thật, xác nhận schema `academy.*` được tạo**

Run: `cd services/company && node scripts/migrate.mjs`
Expected: log hiển thị áp dụng `academy/1_academy_programs` (hoặc
`001_academy_programs` tuỳ cách script chuẩn hoá tên) thành công, không lỗi.
Nếu DB dev đã có schema `academy` từ trước (migration từng chạy tay), script
phải báo "already applied" chứ không lỗi trùng — nếu lỗi trùng, kiểm tra
bảng ghi migration đã áp dụng (`_migrations` hoặc tương đương) trước khi
tiếp tục.

- [ ] **Step 6: Commit**

```bash
git add services/company/academy/encore.service.ts services/company/academy/db.ts services/company/academy/models services/company/scripts/migrate.mjs
git commit -m "feat(company): đăng ký service + DB client cho academy

academy/ trước đây không có encore.service.ts/db.ts nên không phải Encore
service thật, và migration 001_academy_programs chưa từng chạy được vì
thiếu trong MIGRATION_DIRS của migrate.mjs. Thêm cả hai, theo đúng pattern
services/company/identity/.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: Academy — `program.service.ts` + `program.handler.ts` (endpoint thật) + rewrite `academy-progress.test.ts`

**Files:**
- Create: `services/company/academy/services/program.service.ts`
- Modify: `services/company/academy/handlers/program.handler.ts`
- Modify: `services/company/academy/tests/academy-progress.test.ts`

**Interfaces:**
- Consumes: `db, schema` từ `../models/db` (Task 3).
- Produces (dùng bởi Task 6 — `api.ts` barrel):
  `getAcademyPrograms(): Promise<AcademyProgram[]>`,
  `getAcademyProgram(id: string): Promise<AcademyProgram>`,
  `enrollLearner(params: EnrollLearnerParams): Promise<AcademyEnrollment>`,
  `getEnrollment(id: string): Promise<AcademyEnrollment>`,
  `completeLesson(params: CompleteLessonParams): Promise<CompleteLessonResult>`
  — tất cả export từ `services/program.service.ts`; handler chỉ wrap thành
  `api()` endpoint, không thêm logic.

- [ ] **Step 1: Viết lại test trước (RED) — `academy-progress.test.ts`**

Thay toàn bộ nội dung file bằng bản seed qua DB thật (theo pattern
`identity/tests/helpers/test-session.ts` — insert trực tiếp qua
`db`/`schema`, ID qua `generateSnowflake()`):

```ts
/**
 * Academy progress tests — DB-backed (Task 4, kế tục Task 2 cũ).
 *
 * Verifies:
 * - Enrollment creation là cô lập với live project (không có field lifecycle)
 * - Lesson completion tăng completedLessons
 * - Lesson completion KHÔNG đổi project stage, KHÔNG tạo evidence
 * - Attempt payload chứa field production bị reject
 */
import { describe, it, expect, beforeEach } from "vitest";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import {
  enrollLearner,
  getEnrollment,
  completeLesson,
  assertAttemptPayloadIsolated,
} from "../services/program.service";

const { academyPrograms } = schema;

async function seedProgram(): Promise<string> {
  const id = generateSnowflake();
  await db.insert(academyPrograms).values({
    id,
    slug: `test-program-${id}`,
    title: "Test Program",
    version: "1.0.0",
  });
  return id.toString();
}

describe("Academy Progress: enrollment and lesson completion (DB-backed)", () => {
  let programId: string;

  beforeEach(async () => {
    programId = await seedProgram();
  });

  it("enrolls a learner and returns an enrollment with no lifecycle fields", async () => {
    const enrollment = await enrollLearner({
      workspaceId: generateSnowflake().toString(),
      accountId: generateSnowflake().toString(),
      programId,
    });

    expect(enrollment.id).toBeDefined();
    expect(enrollment.status).toBe("NOT_STARTED");
    expect(enrollment.completedLessons).toBe(0);

    expect(enrollment).not.toHaveProperty("lifecycleStage");
    expect(enrollment).not.toHaveProperty("projectId");
    expect(enrollment).not.toHaveProperty("evidenceId");
    expect(enrollment).not.toHaveProperty("gateEvaluationId");
  });

  it("completing a lesson increments completedLessons and preserves isolation", async () => {
    const enrollment = await enrollLearner({
      workspaceId: generateSnowflake().toString(),
      accountId: generateSnowflake().toString(),
      programId,
    });

    const result = await completeLesson({
      enrollmentId: enrollment.id,
      lessonId: generateSnowflake().toString(),
      reflection: "Tôi hiểu rõ hơn về giai đoạn Discovery",
    });

    expect(result.attempt.synthetic).toBe(true);
    expect(result.attempt.completedAt).toBeDefined();
    expect(result.enrollment.completedLessons).toBe(1);
    expect(result.enrollment.status).toBe("IN_PROGRESS");
    expect(result.projectStageChanged).toBe(false);
    expect(result.evidenceCreated).toBe(false);
  });

  it("getEnrollment reflects updated completedLessons after two lesson completions", async () => {
    const enrollment = await enrollLearner({
      workspaceId: generateSnowflake().toString(),
      accountId: generateSnowflake().toString(),
      programId,
    });

    await completeLesson({ enrollmentId: enrollment.id, lessonId: generateSnowflake().toString() });
    await completeLesson({ enrollmentId: enrollment.id, lessonId: generateSnowflake().toString() });

    const updated = await getEnrollment(enrollment.id);
    expect(updated.completedLessons).toBe(2);
  });

  it("rejects attempt payload containing gateEvaluationId (forbidden production field)", () => {
    expect(() =>
      assertAttemptPayloadIsolated({ reflection: "Good learning", gateEvaluationId: "gate-123" })
    ).toThrowError(/gateEvaluationId/);
  });

  it("rejects attempt payload containing lifecycleStage", () => {
    expect(() =>
      assertAttemptPayloadIsolated({ reflection: "Learning complete", lifecycleStage: "P3_PILOT" })
    ).toThrowError(/lifecycleStage/);
  });

  it("rejects attempt payload containing evidenceId", () => {
    expect(() =>
      assertAttemptPayloadIsolated({ reflection: "Done", evidenceId: "ev-456" })
    ).toThrowError(/evidenceId/);
  });

  it("accepts attempt payload with only allowed fields", () => {
    expect(() =>
      assertAttemptPayloadIsolated({ reflection: "Great session", score: 85 })
    ).not.toThrow();
  });
});
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd services/company && npx vitest run academy/tests/academy-progress.test.ts`
Expected: FAIL — `Cannot find module '../services/program.service'`.

- [ ] **Step 3: Viết `services/program.service.ts`**

```ts
import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { academyPrograms, academyEnrollments, academyLessonAttempts } = schema;

export interface AcademyProgram {
  id: string;
  slug: string;
  title: string;
  description: string | null;
  version: string;
  moduleCount: number;
  lessonCount: number;
  published: boolean;
  createdAt: string;
}

export interface AcademyEnrollment {
  id: string;
  workspaceId: string;
  accountId: string;
  programId: string;
  completedLessons: number;
  status: "NOT_STARTED" | "IN_PROGRESS" | "COMPLETED";
  enrolledAt: string;
  completedAt: string | null;
  // INVARIANT: không có lifecycleStage, projectId, gateEvaluationId, evidenceId
}

export interface AcademyLessonAttempt {
  id: string;
  enrollmentId: string;
  lessonId: string;
  status: "NOT_STARTED" | "IN_PROGRESS" | "COMPLETED";
  reflection: string | null;
  score: number | null;
  /** Luôn true — đây là điểm rubric học tập, không phải metric PMF/maturity. */
  synthetic: true;
  attemptedAt: string;
  completedAt: string | null;
}

export interface CompleteLessonResult {
  attempt: AcademyLessonAttempt;
  enrollment: AcademyEnrollment;
  /** INVARIANT: luôn false — hoàn thành bài học không bao giờ đổi project stage thật. */
  projectStageChanged: false;
  /** INVARIANT: luôn false — hoàn thành bài học không bao giờ tạo evidence thật. */
  evidenceCreated: false;
}

const PROGRAM_VIEW_COLUMNS = {
  id: academyPrograms.id,
  slug: academyPrograms.slug,
  title: academyPrograms.title,
  description: academyPrograms.description,
  version: academyPrograms.version,
  moduleCount: academyPrograms.moduleCount,
  lessonCount: academyPrograms.lessonCount,
  published: academyPrograms.published,
  createdAt: academyPrograms.createdAt,
} as const;

type ProgramRow = Pick<typeof academyPrograms.$inferSelect, keyof typeof PROGRAM_VIEW_COLUMNS>;

function mapProgramRow(row: ProgramRow): AcademyProgram {
  return {
    id: row.id.toString(),
    slug: row.slug,
    title: row.title,
    description: row.description ?? null,
    version: row.version,
    moduleCount: row.moduleCount,
    lessonCount: row.lessonCount,
    published: row.published,
    createdAt: row.createdAt.toISOString(),
  };
}

const ENROLLMENT_VIEW_COLUMNS = {
  id: academyEnrollments.id,
  workspaceId: academyEnrollments.workspaceId,
  accountId: academyEnrollments.accountId,
  programId: academyEnrollments.programId,
  completedLessons: academyEnrollments.completedLessons,
  status: academyEnrollments.status,
  enrolledAt: academyEnrollments.enrolledAt,
  completedAt: academyEnrollments.completedAt,
} as const;

type EnrollmentRow = Pick<typeof academyEnrollments.$inferSelect, keyof typeof ENROLLMENT_VIEW_COLUMNS>;

function mapEnrollmentRow(row: EnrollmentRow): AcademyEnrollment {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    accountId: row.accountId.toString(),
    programId: row.programId.toString(),
    completedLessons: row.completedLessons,
    status: row.status as AcademyEnrollment["status"],
    enrolledAt: row.enrolledAt.toISOString(),
    completedAt: row.completedAt ? row.completedAt.toISOString() : null,
  };
}

function mapAttemptRow(row: typeof academyLessonAttempts.$inferSelect): AcademyLessonAttempt {
  return {
    id: row.id.toString(),
    enrollmentId: row.enrollmentId.toString(),
    lessonId: row.lessonId.toString(),
    status: row.status as AcademyLessonAttempt["status"],
    reflection: row.reflection ?? null,
    score: row.score ?? null,
    synthetic: true,
    attemptedAt: row.attemptedAt.toISOString(),
    completedAt: row.completedAt ? row.completedAt.toISOString() : null,
  };
}

export async function getAcademyPrograms(): Promise<AcademyProgram[]> {
  const rows = await db.select(PROGRAM_VIEW_COLUMNS).from(academyPrograms);
  return rows.map(mapProgramRow);
}

export async function getAcademyProgram(id: string): Promise<AcademyProgram> {
  const [row] = await db
    .select(PROGRAM_VIEW_COLUMNS)
    .from(academyPrograms)
    .where(eq(academyPrograms.id, BigInt(id)))
    .limit(1);
  if (!row) throw APIError.notFound(`academy program ${id} not found`);
  return mapProgramRow(row);
}

export interface EnrollLearnerParams {
  workspaceId: string;
  accountId: string;
  programId: string;
}

export async function enrollLearner(params: EnrollLearnerParams): Promise<AcademyEnrollment> {
  const [row] = await db
    .insert(academyEnrollments)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(params.workspaceId),
      accountId: BigInt(params.accountId),
      programId: BigInt(params.programId),
    })
    .returning(ENROLLMENT_VIEW_COLUMNS);
  if (!row) throw APIError.internal("failed to create academy enrollment");
  return mapEnrollmentRow(row);
}

export async function getEnrollment(enrollmentId: string): Promise<AcademyEnrollment> {
  const [row] = await db
    .select(ENROLLMENT_VIEW_COLUMNS)
    .from(academyEnrollments)
    .where(eq(academyEnrollments.id, BigInt(enrollmentId)))
    .limit(1);
  if (!row) throw APIError.notFound(`academy enrollment ${enrollmentId} not found`);
  return mapEnrollmentRow(row);
}

export interface CompleteLessonParams {
  enrollmentId: string;
  lessonId: string;
  reflection?: string;
  score?: number;
}

export async function completeLesson(params: CompleteLessonParams): Promise<CompleteLessonResult> {
  const enrollment = await getEnrollment(params.enrollmentId);

  const [attemptRow] = await db
    .insert(academyLessonAttempts)
    .values({
      id: generateSnowflake(),
      enrollmentId: BigInt(params.enrollmentId),
      lessonId: BigInt(params.lessonId),
      status: "COMPLETED",
      reflection: params.reflection ?? null,
      score: params.score ?? null,
      synthetic: true,
      completedAt: new Date(),
    })
    .returning();
  if (!attemptRow) throw APIError.internal("failed to record lesson attempt");

  const [updatedRow] = await db
    .update(academyEnrollments)
    .set({
      completedLessons: enrollment.completedLessons + 1,
      status: "IN_PROGRESS",
    })
    .where(eq(academyEnrollments.id, BigInt(params.enrollmentId)))
    .returning(ENROLLMENT_VIEW_COLUMNS);
  if (!updatedRow) throw APIError.internal("failed to update academy enrollment");

  return {
    attempt: mapAttemptRow(attemptRow),
    enrollment: mapEnrollmentRow(updatedRow),
    projectStageChanged: false,
    evidenceCreated: false,
  };
}

/**
 * Validates that an attempt payload does NOT contain forbidden production fields.
 * Call before persisting any attempt payload.
 */
export function assertAttemptPayloadIsolated(payload: Record<string, unknown>): void {
  const forbidden = ["gateEvaluationId", "lifecycleStage", "evidenceId", "projectId", "pilotId", "metricContractId"];
  for (const field of forbidden) {
    if (field in payload) {
      throw new Error(
        `Academy lesson attempt payload contains forbidden production field: '${field}'. ` +
        `Academy is isolated from live project, evidence, and gate state.`
      );
    }
  }
}
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `cd services/company && npx vitest run academy/tests/academy-progress.test.ts`
Expected: PASS toàn bộ 7 test.

- [ ] **Step 5: Viết lại `handlers/program.handler.ts` — chỉ còn type + `api()` endpoint**

```ts
/**
 * Academy program, enrollment, and progress handlers.
 *
 * ISOLATION RULE: This file MUST NOT import any module from:
 * - `operations/strategy` handlers or services
 * - `operations/handlers` (project, task, etc.)
 * - `commercial` or `finance-legal` handlers
 *
 * Academy is a separate bounded context.
 */
import { api } from "encore.dev/api";
import {
  getAcademyPrograms,
  getAcademyProgram,
  enrollLearner,
  getEnrollment,
  completeLesson,
} from "../services/program.service";
import type {
  AcademyProgram,
  AcademyEnrollment,
  CompleteLessonResult,
  EnrollLearnerParams,
  CompleteLessonParams,
} from "../services/program.service";

export type { AcademyProgram, AcademyEnrollment, CompleteLessonResult, EnrollLearnerParams, CompleteLessonParams };

export const listAcademyPrograms = api(
  { method: "GET", path: "/academy/programs", expose: true },
  async (): Promise<{ programs: AcademyProgram[] }> => ({ programs: await getAcademyPrograms() })
);

export const getAcademyProgramEndpoint = api(
  { method: "GET", path: "/academy/programs/:id", expose: true },
  async ({ id }: { id: string }): Promise<AcademyProgram> => getAcademyProgram(id)
);

export const enrollLearnerEndpoint = api(
  { method: "POST", path: "/academy/enrollments", expose: true },
  async (params: EnrollLearnerParams): Promise<AcademyEnrollment> => enrollLearner(params)
);

export const getEnrollmentEndpoint = api(
  { method: "GET", path: "/academy/enrollments/:id", expose: true },
  async ({ id }: { id: string }): Promise<AcademyEnrollment> => getEnrollment(id)
);

export const completeLessonEndpoint = api(
  { method: "POST", path: "/academy/enrollments/:enrollmentId/complete-lesson", expose: true },
  async (params: { enrollmentId: string } & Omit<CompleteLessonParams, "enrollmentId">): Promise<CompleteLessonResult> =>
    completeLesson({ ...params, enrollmentId: params.enrollmentId })
);
```

(`assertAttemptPayloadIsolated` không cần expose qua `api()` — nó chỉ dùng
nội bộ trước khi persist, giữ nguyên export dạng hàm thuần từ
`program.service.ts` cho việc khác trong service gọi trực tiếp nếu cần.)

- [ ] **Step 6: Chạy toàn bộ test academy để xác nhận không vỡ isolation test**

Run: `cd services/company && npx vitest run academy/tests/academy-boundary.test.ts academy/tests/academy-progress.test.ts`
Expected: PASS toàn bộ.

- [ ] **Step 7: Commit**

```bash
git add services/company/academy/services/program.service.ts services/company/academy/handlers/program.handler.ts services/company/academy/tests/academy-progress.test.ts
git commit -m "feat(company): academy program/enrollment DB-backed thay in-memory

program.handler.ts trước đây dùng 3 Map trong bộ nhớ, không có api()
endpoint nào — dữ liệu mất khi restart process và không gọi được từ
frontend. Chuyển logic sang program.service.ts (Drizzle, generateSnowflake
bigint ID), handler giờ chỉ còn 5 api() endpoint mỏng.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 5: Academy — `template_export.service.ts` + `template-export.handler.ts` + cập nhật `academy-production-contract.test.ts`

**Files:**
- Create: `services/company/academy/services/template_export.service.ts`
- Modify: `services/company/academy/handlers/template-export.handler.ts`
- Modify: `services/company/academy/tests/academy-production-contract.test.ts`

**Interfaces:**
- Consumes: `db, schema` từ `../models/db` (Task 3); `ACADEMY_ARTIFACT_SCHEME`,
  `ACADEMY_TEMPLATE_DRAFT_KIND` từ `../contracts` (không đổi).
- Produces: `exportTemplate(params: ExportTemplateParams): Promise<AcademyTemplateExport>`,
  `getTemplateExport(id: string): Promise<AcademyTemplateExport>` — export
  từ `services/template_export.service.ts`.

- [ ] **Step 1: Sửa test trước (RED) — chỉ đổi 2 chỗ dùng `exportTemplate`
  thành `await`, bỏ `_resetTemplateExportStore` (không còn ý nghĩa với DB
  thật — mỗi test tự tạo dữ liệu mới bằng `academyAttemptId` ngẫu nhiên nên
  không đụng dữ liệu nhau)**

Trong `academy-production-contract.test.ts`, đổi import (dòng 15):

```ts
// Trước:
import { exportTemplate, _resetTemplateExportStore } from "../handlers/template-export.handler";
// Sau:
import { exportTemplate } from "../handlers/template-export.handler";
```

Đổi test `"exportTemplate requires explicit human confirmation..."` (dòng 89-116):

```ts
  it("exportTemplate requires explicit human confirmation and always labels the draft (Task 4)", async () => {
    await expect(
      exportTemplate({
        workspaceId: "1",
        accountId: "1",
        academyAttemptId: "att-1",
        templateKind: "interview-script",
        body: { question: "What is the biggest problem?" },
        confirmedByAccountId: "",
      })
    ).rejects.toThrow(/confirmation/i);

    const record = await exportTemplate({
      workspaceId: "1",
      accountId: "1",
      academyAttemptId: "att-1",
      templateKind: "interview-script",
      body: { question: "What is the biggest problem?", score: 0.9, synthetic: true },
      confirmedByAccountId: "1",
    });

    expect(record.liveArtifactKind).toBe(ACADEMY_TEMPLATE_DRAFT_KIND);
    expect(record.academySourceRef.startsWith("academy-artifact://")).toBe(true);
    expect(record.body).not.toHaveProperty("score");
    expect(record.body).not.toHaveProperty("synthetic");
  });
```

(Lưu ý: `workspaceId`/`accountId`/`confirmedByAccountId` giờ phải là chuỗi
số hợp lệ để `BigInt(...)` không ném lỗi — dùng `"1"` cố định là đủ vì bảng
`academyTemplateExports` không có FK ràng buộc các cột này.)

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd services/company && npx vitest run academy/tests/academy-production-contract.test.ts`
Expected: FAIL — `exportTemplate is not a function` hoặc lỗi sync/async
mismatch, vì handler cũ vẫn đồng bộ.

- [ ] **Step 3: Viết `services/template_export.service.ts`**

```ts
import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { ACADEMY_ARTIFACT_SCHEME, ACADEMY_TEMPLATE_DRAFT_KIND } from "../contracts";

const { academyTemplateExports } = schema;

export interface AcademyTemplateExport {
  id: string;
  workspaceId: string;
  accountId: string;
  templateKind: string;
  body: Record<string, unknown>;
  academySourceRef: string;
  disclaimer: string;
  liveArtifactKind: typeof ACADEMY_TEMPLATE_DRAFT_KIND;
  exportedAt: string;
  confirmedByAccountId: string;
}

export interface ExportTemplateParams {
  workspaceId: string;
  accountId: string;
  academyAttemptId: string;
  templateKind: string;
  body: Record<string, unknown>;
  /** Phải là tài khoản người xác nhận rõ ràng — không export nền tự động. */
  confirmedByAccountId: string;
}

const ACADEMY_DISCLAIMER =
  "Template học tập từ Academy — không phải evidence sản xuất. " +
  "Cần con người thay thế bằng nguồn thực tế độc lập trước khi dùng làm evidence.";

const FORBIDDEN_BODY_FIELDS = ["score", "synthetic", "modelFeedback", "feedback"];

function stripSimulationArtifacts(body: Record<string, unknown>): Record<string, unknown> {
  const cleaned: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(body)) {
    if (FORBIDDEN_BODY_FIELDS.includes(key)) continue;
    cleaned[key] = value;
  }
  return cleaned;
}

function mapRow(row: typeof academyTemplateExports.$inferSelect): AcademyTemplateExport {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    accountId: row.accountId.toString(),
    templateKind: row.templateKind,
    body: row.body as Record<string, unknown>,
    academySourceRef: row.academySourceRef,
    disclaimer: row.disclaimer,
    liveArtifactKind: row.liveArtifactKind as typeof ACADEMY_TEMPLATE_DRAFT_KIND,
    exportedAt: row.exportedAt.toISOString(),
    confirmedByAccountId: row.confirmedByAccountId.toString(),
  };
}

/**
 * Exports a labelled template draft into a workspace.
 * Requires explicit human confirmation (`confirmedByAccountId`); no background
 * export runs on lesson/simulation completion.
 */
export async function exportTemplate(params: ExportTemplateParams): Promise<AcademyTemplateExport> {
  if (!params.confirmedByAccountId) {
    throw APIError.invalidArgument(
      "Template export requires an explicit human confirmation (confirmedByAccountId)"
    );
  }
  if (!params.academyAttemptId) {
    throw APIError.invalidArgument("Template export requires academyAttemptId");
  }

  const academySourceRef = `${ACADEMY_ARTIFACT_SCHEME}attempt/${params.academyAttemptId}`;

  const [row] = await db
    .insert(academyTemplateExports)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(params.workspaceId),
      accountId: BigInt(params.accountId),
      templateKind: params.templateKind,
      body: stripSimulationArtifacts(params.body),
      academySourceRef,
      disclaimer: ACADEMY_DISCLAIMER,
      liveArtifactKind: ACADEMY_TEMPLATE_DRAFT_KIND,
      confirmedByAccountId: BigInt(params.confirmedByAccountId),
    })
    .returning();

  if (!row) throw APIError.internal("failed to create academy template export");
  return mapRow(row);
}

export async function getTemplateExport(id: string): Promise<AcademyTemplateExport> {
  const [row] = await db
    .select()
    .from(academyTemplateExports)
    .where(eq(academyTemplateExports.id, BigInt(id)))
    .limit(1);
  if (!row) throw APIError.notFound(`academy template export ${id} not found`);
  return mapRow(row);
}
```

- [ ] **Step 4: Viết lại `handlers/template-export.handler.ts`**

```ts
/**
 * Academy template export handler.
 *
 * ISOLATION RULE: This file MUST NOT import any module from:
 * - `operations/strategy` handlers or services
 * - `operations/handlers` (project, task, etc.)
 * - `commercial` or `finance-legal` handlers
 *
 * A template export is the ONLY sanctioned one-way path from Academy to a
 * live workspace. It never produces Evidence, a source-ingestion record, a
 * gate input, a metric snapshot, or a task.
 */
import { api } from "encore.dev/api";
import { exportTemplate, getTemplateExport } from "../services/template_export.service";
import type { AcademyTemplateExport, ExportTemplateParams } from "../services/template_export.service";

export type { AcademyTemplateExport, ExportTemplateParams };

export const exportTemplateEndpoint = api(
  { method: "POST", path: "/academy/template-exports", expose: true },
  async (params: ExportTemplateParams): Promise<AcademyTemplateExport> => exportTemplate(params)
);

export const getTemplateExportEndpoint = api(
  { method: "GET", path: "/academy/template-exports/:id", expose: true },
  async ({ id }: { id: string }): Promise<AcademyTemplateExport> => getTemplateExport(id)
);
```

- [ ] **Step 5: Chạy test, xác nhận PASS**

Run: `cd services/company && npx vitest run academy/tests/academy-production-contract.test.ts academy/tests/academy-boundary.test.ts`
Expected: PASS toàn bộ (bao gồm test cross-domain `recordEvidence rejects
academy_template_draft` — không đổi vì không đụng tới `contracts.ts`).

- [ ] **Step 6: Commit**

```bash
git add services/company/academy/services/template_export.service.ts services/company/academy/handlers/template-export.handler.ts services/company/academy/tests/academy-production-contract.test.ts
git commit -m "feat(company): academy template export DB-backed thay in-memory

Cùng lý do với program.service.ts (Task 4) — template-export.handler.ts
dùng chung migration 001_academy_programs nên phải wire cùng lúc, tránh
để lại nửa stub nửa thật.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 6: Academy — barrel `api.ts` + guardrail check

**Files:**
- Create: `services/company/academy/api.ts`

**Interfaces:**
- Produces: barrel export toàn bộ public surface của academy service
  (theo đúng pattern `identity/api.ts`).

- [ ] **Step 1: Tạo `api.ts`**

```ts
export * from "./handlers";
export * from "./services";
export * from "./models";
```

Vì `handlers/` và `services/` chưa có file `index.ts` (identity có, academy
thì mỗi handler/service chỉ 1-2 file) — tạo thêm 2 barrel nhỏ:

`services/company/academy/handlers/index.ts`:
```ts
export * from "./program.handler";
export * from "./template-export.handler";
```

`services/company/academy/services/index.ts`:
```ts
export * from "./program.service";
export * from "./template_export.service";
```

- [ ] **Step 2: Chạy Encore handler boundary check**

Run: `make encore-handler-boundary-check`
Expected: PASS — `program.handler.ts`/`template-export.handler.ts` không
import `drizzle-orm`/`models/db`/`db`/`shared/db/schema` trực tiếp (đã đảm
bảo ở Task 4-5, chỉ import từ `../services/*`).

- [ ] **Step 3: Chạy company boundary check + typecheck**

Run: `make company-boundary-check`
Run: `cd services/company && npx tsc --noEmit`
Expected: cả hai PASS, không lỗi type (chú ý: `academyEnrollments.status`
là `varchar` không phải enum ở tầng DB — ép kiểu qua `as
AcademyEnrollment["status"]` ở `mapEnrollmentRow`/`mapAttemptRow` đã xử lý
việc này, không cần sửa schema).

- [ ] **Step 4: Commit**

```bash
git add services/company/academy/api.ts services/company/academy/handlers/index.ts services/company/academy/services/index.ts
git commit -m "feat(company): thêm barrel api.ts cho academy service

Hoàn tất pattern chuẩn (encore.service.ts + db.ts + models/ + handlers/ +
services/ + api.ts) khớp với identity/. Academy giờ là Encore service thật,
không còn stub.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 7: Doc-drift nhỏ (C1-C3)

**Files:**
- Modify: `services/realtime_agent/README.md`
- Create: `docs/architecture/generated/COMPANY_SCHEMA_INVENTORY.md`
- Modify: `docs/architecture/cookbook/README.md`
- Modify: `docs/architecture/overview/05-khuyen-nghi.md` (mục C2)

- [ ] **Step 1: Sửa `services/realtime_agent/README.md`**

Dòng 3-19 hiện tại (sơ đồ ASCII + "backend/app"):

```
LiveKit Agents worker that carries the actual realtime voice loop for mCOSA's
Hologram Hub (mCOSA V12.1/V12.2 §7 Voice Agent Runtime). This is a
**standalone process**, not part of `backend/app`/`brain-api` — long-lived
audio handling must never run inside a FastAPI request handler (spec §90.3).

```
Flutter (livekit_client)
      │
      ▼
LiveKit (Cloud today; Local later, see DEPLOYMENT.md)
      │
      ▼
services/realtime_agent  ◄── this process
      │
      ├── Gemini Live (livekit-plugins-google)
      └── Tool Bridge ──► backend/app (direct SessionLocal(), no HTTP hop)
```

`backend/app/modules/realtime` (`/api/v1/realtime`) only handles the Control
Plane side: creating a `RealtimeSession` row, minting a LiveKit join token,
and recording session status/events. It never touches the audio stream
itself.
```

Sửa thành:

```
LiveKit Agents worker that carries the actual realtime voice loop for mCOSA's
Hologram Hub. This is a **standalone process**, not part of `apps/cosa` —
long-lived audio handling must never run inside a FastAPI request handler.

Runs as TWO containers in `docker-compose.yml` (see there for exact env):
`realtime-agent` registers against the self-hosted local LiveKit server
(desktop voice rooms), `realtime-agent-cloud` registers against LiveKit
Cloud (mobile/web voice rooms) — both must run concurrently, each only
receives dispatch from the LiveKit server it registered with.

```
Flutter (livekit_client, desktop)         Flutter (livekit_client, mobile/web)
      │                                          │
      ▼                                          ▼
LiveKit local (docker-compose: livekit:7880)   LiveKit Cloud
      │                                          │
      ▼                                          ▼
realtime-agent (this dir, local)     realtime-agent-cloud (this dir, cloud)
      │                                          │
      ├── Gemini Live (livekit-plugins-google) ──┘
      └── Tool Bridge ──► apps/cosa/api (HTTP, see services_client.py)
```

`apps/cosa/api` handles the Control Plane side: creating a `RealtimeSession`
row, minting a LiveKit join token, and recording session status/events. It
never touches the audio stream itself.
```

- [ ] **Step 2: Tạo `docs/architecture/generated/COMPANY_SCHEMA_INVENTORY.md`**

```markdown
# COMPANY_SCHEMA_INVENTORY.json — ghi chú trạng thái

`COMPANY_SCHEMA_INVENTORY.json` trong thư mục này là **ảnh chụp lịch sử
đóng băng** (frozen one-time snapshot) cho epic DB-FINAL-CUTOVER, sinh ngày
2026-08-24 bởi một script phân tích tĩnh **không được commit vào repo**
(đọc `_meta.purpose` trong chính file JSON để biết chi tiết cách sinh).

Script đó đọc từ `legacy/backend/alembic/versions/*.py` — thư mục `legacy/`
đã bị xoá hẳn khỏi repo ngày 2026-08-25 (xem `ADR-CUTOVER-001`). Vì vậy:

- **Không thể "regenerate" file này** — script sinh không còn tồn tại và
  nguồn dữ liệu đầu vào (`legacy/`) cũng đã bị xoá.
- File chỉ có giá trị làm bằng chứng lịch sử cho việc đối chiếu
  legacy → canonical schema đã hoàn tất, không phải nguồn tham chiếu cho
  trạng thái schema hiện tại.
- Muốn biết trạng thái schema `services/company` hiện tại, đọc trực tiếp
  `services/company/shared/db/schema/*.ts` hoặc chạy
  `make schema-fingerprint-check`.

Xem thêm: `docs/architecture/overview/05-khuyen-nghi.md` mục C2.
```

- [ ] **Step 3: Sửa `docs/architecture/cookbook/README.md`**

Thêm 1 dòng ngay dưới heading `## Recipes`:

```markdown
## Recipes

**Trạng thái:** 1/6 recipe đã hoàn thành, 5 recipe còn lại đang xây dựng.

1. [How to add a Native Tool](./ADD_NATIVE_TOOL.md)
2. How to add a Skill (coming soon)
3. How to add a Workflow Node & UI Renderer (coming soon)
4. How to add an MCP Connector (coming soon)
5. How to add an Executor Provider (coming soon)
6. How to add an Event Projection (coming soon)
```

- [ ] **Step 4: Cập nhật mục C2 trong `05-khuyen-nghi.md`**

Sửa nội dung mục `### C2. ...` thành:

```markdown
### C2. `COMPANY_SCHEMA_INVENTORY.json` là snapshot đóng băng, không thể regenerate

- **Phát hiện:** file tự ghi trong `_meta.purpose` rằng nó được sinh bởi
  "a temporary, non-committed static-analysis script" đọc từ
  `legacy/backend/alembic/versions/*.py` — `legacy/` đã bị xoá hẳn
  2026-08-25 và không có script generator nào còn tồn tại trong repo (đã
  grep xác nhận). Đề xuất "regenerate" ban đầu (phiên trước) là sai — không
  thể thực hiện.
- **Đề xuất:** đã thêm `docs/architecture/generated/COMPANY_SCHEMA_INVENTORY.md`
  ghi rõ trạng thái đóng băng, tránh người đọc sau tưởng nhầm có thể chạy
  lại.
- **Mức ưu tiên:** Thấp — đã xử lý xong (xem file ghi chú kèm theo).
```

- [ ] **Step 5: Commit**

```bash
git add services/realtime_agent/README.md docs/architecture/generated/COMPANY_SCHEMA_INVENTORY.md docs/architecture/cookbook/README.md docs/architecture/overview/05-khuyen-nghi.md
git commit -m "docs: sửa doc-drift realtime_agent README, schema inventory, cookbook

realtime_agent/README.md vẫn trỏ backend/app đã xoá và mô tả sai voice là
1-worker (thực tế 2 worker local+cloud trong docker-compose.yml).
COMPANY_SCHEMA_INVENTORY.json không thể regenerate (nguồn legacy/ đã xoá,
script sinh không commit) — thêm ghi chú thay vì đề xuất sai. Cookbook
thêm dòng trạng thái 1/6 recipe.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 8: Verification cuối cùng (toàn bộ plan)

- [ ] **Step 1: Guardrail Encore + TS**

```bash
make company-boundary-check
make encore-handler-boundary-check
make ts-suppression-check
```
Expected: cả 3 PASS.

- [ ] **Step 2: Company usage inventory không tự ý lệch**

```bash
node scripts/company_usage_inventory.py --check
```
Expected: PASS (không thêm reference mới vào nhóm REVIEW ngoài dự kiến —
academy giờ có `api()` thật lần đầu, có thể xuất hiện entry mới trong
inventory; nếu `--check` fail vì entry mới hợp lệ, chạy
`node scripts/company_usage_inventory.py` để regenerate rồi commit riêng).

- [ ] **Step 3: Toàn bộ test Python liên quan Task 1**

```bash
.venv/bin/python -m pytest tests/agent/evals/test_promotion_gate.py tests/apps/cosa/test_event_trigger_promotion.py -v
```
Expected: PASS toàn bộ.

- [ ] **Step 4: Toàn bộ test academy (Task 3-6)**

```bash
cd services/company && npx vitest run academy/
```
Expected: PASS toàn bộ 3 file test.

- [ ] **Step 5: Flutter analyze + test approvals (Task 2)**

```bash
cd frontend && flutter analyze
cd frontend && flutter test test/shared/state/async_feature_state_test.dart test/modules/approvals/approvals_controller_test.dart
```
Expected: cả hai PASS, không có lỗi/warning mới.

- [ ] **Step 6: Migration academy chạy lại idempotent (không lỗi lần 2)**

```bash
cd services/company && node scripts/migrate.mjs
```
Expected: báo "no pending migrations" hoặc tương đương cho `academy`, không
lỗi.

Không commit gì ở Task 8 — đây là cổng xác minh, nếu phát hiện lỗi thì quay
lại đúng Task tương ứng để sửa và tạo commit fix riêng.

## Self-Review Notes

- **Spec coverage:** B2→Task 1, B4→Task 2, B1→Task 3-6, C1-C3→Task 7. Nhóm
  A và B3 cố ý không có task (ngoài phạm vi, cần quyết định của team).
- **Placeholder scan:** không còn "TBD"/"tương tự Task N" — mọi step có code
  đầy đủ.
- **Type consistency đã kiểm tra:** `AcademyEnrollment.status` dùng cùng
  union `"NOT_STARTED" | "IN_PROGRESS" | "COMPLETED"` xuyên suốt
  `program.service.ts`, test, và design cũ; `CompleteLessonResult` giữ đúng
  2 field literal `false` như bản gốc; tên hàm export từ `program.service.ts`
  khớp chính xác với import ở `program.handler.ts` và test Task 4.

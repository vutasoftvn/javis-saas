# Implementation Audit Phase 1 — Authority Enforcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đóng 2 lỗ hổng phân quyền P1 nêu ở `docs/architecture/overview/09-implementation-audit-2026-09-06.md` (IA01, IA17) và sửa 9 lỗi typecheck đang FAIL ở `services/company`, để `make verify`/`make company-boundary-check` phản ánh đúng trạng thái thay vì bị che bởi lỗi fixture không liên quan.

**Architecture:** Không đổi kiến trúc. Cả hai lỗ hổng đều là "handler/service quên gọi lớp authority đã tồn tại" (`requireFounderCommand` ở `identity/services/command-authority.service.ts`, `authorizeBusinessAction` ở `identity/services/business-authorization.service.ts`) — pattern đã dùng đúng ở các endpoint khác trong cùng file (`execution-plan.service.ts:467` cho accept, `ai-compliance-governance.handler.ts:66/102` cho create/approve). Chỉ thêm lời gọi còn thiếu + lấy `workspaceId` từ `ctx` thay vì tham số client gửi lên.

**Tech Stack:** Encore.ts (TypeScript), Drizzle ORM, Vitest (chạy qua `encore test`), Postgres thật tại `WORKSPACE_DATABASE_URL` (không mock DB).

## Global Constraints

- Không dùng `any`/`@ts-ignore`/`@ts-expect-error` để né lỗi type (Encore Guardrail #5).
- Lỗi trả cho client qua `APIError`, không throw `Error` trần.
- Test phải chạy qua `encore test` với Postgres thật (không mock service/DB) — môi trường này đã xác nhận chạy được sau khi migrate (`set -a && source .env && set +a && cd services/company && node scripts/migrate.mjs`, sau đó `encore test <file>`).
- Sau mỗi task: `cd services/company && npx tsc --noEmit` phải sạch phần liên quan (không nhất thiết toàn bộ 0 lỗi nếu có lỗi tồn tại từ trước không liên quan, nhưng 2 task dưới đây dọn đúng 9 lỗi đã biết).
- Không sửa hành vi của `suspendAiDeployment`/`ai-incident-response.service.ts`/`ai-compliance-e2e-seed.service.ts` — các caller này gọi không có `ctx` một cách có chủ đích (auto-suspend an toàn, seed nội bộ), giữ nguyên.

---

### Task 1: Sửa 9 lỗi typecheck ở fixture test (schema mismatch)

**Files:**
- Modify: `services/company/finance-legal/tests/deployment-authority.test.ts:169-176,256-262,279-285`
- Modify: `services/company/finance-legal/tests/legal-applicability-integrity.test.ts:34-50,89-101,182`
- Modify: `services/company/finance-legal/tests/legal-obligation-lifecycle.test.ts:97-104`
- Reference (không sửa): `services/company/shared/db/schema/legal.ts:42-54` (bảng `legal_entity_profiles` — không có cột `legalName`), `services/company/shared/types/tenant_context.ts` (`TenantContext` bắt buộc `permissions`, `correlationId`)

**Interfaces:**
- Không đổi signature nào — chỉ sửa test fixtures cho khớp `legalEntityProfiles` schema thật (`id, workspaceId, entityType, status, registrationNumber?, taxId?, verifiedByMemberId?, verifiedAt?`) và `TenantContext` thật.

- [ ] **Step 1: Xác nhận lỗi hiện tại**

Run: `cd services/company && npx tsc --noEmit 2>&1 | head -20`
Expected: 9 lỗi ở 3 file trên (đã xác nhận lúc audit).

- [ ] **Step 2: Xoá field `legalName` không tồn tại trong schema**

Trong `deployment-authority.test.ts` dòng insert `legalEntityProfiles` (quanh dòng 169-176), xoá dòng `legalName: "Solo Venture",`.

Trong `legal-applicability-integrity.test.ts`, xoá `legalName: "Entity A Corp",` (dòng ~37) và `legalName: "Entity B Co",` (dòng ~47).

Trong `legal-obligation-lifecycle.test.ts`, xoá `legalName: "Lifecycle Test LLC",` (dòng ~101).

- [ ] **Step 3: Bổ sung field bắt buộc còn thiếu trong `TenantContext` literal**

Trong `deployment-authority.test.ts`, sửa hai literal:

```ts
const ctxUnauthorized: TenantContext = {
  workspaceId: wsId,
  userId: memberWithoutPermId,
  workforceMemberId: memberWithoutPermId,
  membershipRole: "member",
  permissions: [],
  correlationId: "test-resume-unauthorized",
};
```

```ts
const ctxFounder: TenantContext = {
  workspaceId: wsId,
  userId: founderId,
  workforceMemberId: founderId,
  membershipRole: "founder",
  permissions: [],
  correlationId: "test-resume-founder",
};
```

- [ ] **Step 4: Sửa `bigint` truyền vào tham số kiểu `string`**

Trong `legal-applicability-integrity.test.ts`:
- Dòng gọi `evaluateEntityApplicability({ workspaceId: wsId }, ...)` (2 chỗ, quanh dòng 90 và 99) → đổi thành `{ workspaceId: String(wsId) }`.
- Dòng gọi `listOpenObligations({ workspaceId: wsId })` (quanh dòng 182) → đổi thành `listOpenObligations({ workspaceId: String(wsId) })`.

- [ ] **Step 5: Chạy lại typecheck, xác nhận 0 lỗi ở 3 file này**

Run: `cd services/company && npx tsc --noEmit`
Expected: không còn lỗi tại `deployment-authority.test.ts`, `legal-applicability-integrity.test.ts`, `legal-obligation-lifecycle.test.ts`.

- [ ] **Step 6: Chạy lại 3 test file bằng Postgres thật, xác nhận vẫn pass**

Run: `set -a && source ../../.env && set +a && encore test finance-legal/tests/deployment-authority.test.ts finance-legal/tests/legal-applicability-integrity.test.ts finance-legal/tests/legal-obligation-lifecycle.test.ts` (chạy từ `services/company`)
Expected: tất cả PASS (đây là test hành vi cũ, sửa fixture không được đổi kết quả).

- [ ] **Step 7: Commit**

```bash
git add services/company/finance-legal/tests/deployment-authority.test.ts \
        services/company/finance-legal/tests/legal-applicability-integrity.test.ts \
        services/company/finance-legal/tests/legal-obligation-lifecycle.test.ts
git commit -m "fix(company): sửa fixture test lệch schema legal_entity_profiles/TenantContext"
```

---

### Task 2: IA01 — `setCapabilityPolicyService` phải bắt buộc quyền founder và lấy workspace từ ctx

**Files:**
- Modify: `services/company/operations/services/execution-plan.service.ts:690-729` (hàm `setCapabilityPolicyService`)
- Test: `services/company/operations/tests/execution-plan-crud.test.ts` (thêm test case mới vào cuối `describe("WGA #3 — workspace_capability_policy override at classification"` hoặc file test riêng cùng thư mục)

**Interfaces:**
- Consumes: `requireFounderCommand(ctx: TenantContext, action: string): void` (đã import sẵn ở dòng 15 của file, từ `../../shared/auth/workspace-access`).
- Không đổi signature `setCapabilityPolicyService(p, ctx)` — vẫn nhận `p: { workspaceId, capabilityId, decision }` và `ctx: TenantContext`, vẫn trả `CapabilityPolicyEntry[]`.

- [ ] **Step 1: Viết test thất bại — auditor (member thường) không được set capability policy**

Thêm vào `operations/tests/execution-plan-crud.test.ts`:

```ts
it("rejects setCapabilityPolicy from a non-founder member (IA01)", async () => {
  const wsId = String(generateSnowflake());
  const auditorId = String(generateSnowflake());
  const auditorCtx: TenantContext = {
    workspaceId: wsId,
    userId: auditorId,
    workforceMemberId: auditorId,
    membershipRole: "member",
    permissions: [],
    correlationId: "test-ia01-auditor",
  };

  await expect(
    setCapabilityPolicyService(
      { workspaceId: wsId, capabilityId: "some.capability", decision: "ALLOW" },
      auditorCtx
    )
  ).rejects.toMatchObject({ code: "permission_denied" });

  const rows = await listCapabilityPolicyService(wsId, undefined);
  expect(rows.find((r) => r.capabilityId === "some.capability")).toBeUndefined();
});

it("uses ctx.workspaceId, not the request body workspaceId, as the write target (IA01)", async () => {
  const realWsId = String(generateSnowflake());
  const spoofedWsId = String(generateSnowflake());
  const founderId = String(generateSnowflake());
  const founderCtx: TenantContext = {
    workspaceId: realWsId,
    userId: founderId,
    workforceMemberId: founderId,
    membershipRole: "founder",
    permissions: [],
    correlationId: "test-ia01-workspace-binding",
  };

  await setCapabilityPolicyService(
    { workspaceId: spoofedWsId, capabilityId: "some.capability", decision: "ALLOW" },
    founderCtx
  );

  const spoofedRows = await listCapabilityPolicyService(spoofedWsId, undefined);
  expect(spoofedRows.find((r) => r.capabilityId === "some.capability")).toBeUndefined();

  const realRows = await listCapabilityPolicyService(realWsId, undefined);
  expect(realRows.find((r) => r.capabilityId === "some.capability")?.decision).toBe("ALLOW");
});
```

Đảm bảo `TenantContext` và `generateSnowflake` đã được import ở đầu file test (nếu chưa có, thêm `import type { TenantContext } from "../../shared/types/tenant_context";` và `import { generateSnowflake } from "../../shared/services/snowflake.service";`).

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run (từ `services/company`): `set -a && source ../../.env && set +a && encore test operations/tests/execution-plan-crud.test.ts`
Expected: 2 test mới FAIL — test đầu vì auditor hiện vẫn ghi được (không có lỗi permission_denied); test thứ hai FAIL vì code hiện dùng `p.workspaceId` (spoofed) làm target ghi thay vì `ctx.workspaceId`.

- [ ] **Step 3: Sửa `setCapabilityPolicyService`**

Trong `services/company/operations/services/execution-plan.service.ts`, sửa hàm (dòng 690-729):

```ts
export async function setCapabilityPolicyService(
  p: { workspaceId: string; capabilityId: string; decision: TenantPolicyDecision | null },
  ctx: TenantContext
): Promise<CapabilityPolicyEntry[]> {
  requireFounderCommand(ctx, "operations.capability_policy.set");

  const wsId = BigInt(ctx.workspaceId);
  const cap = p.capabilityId?.trim();
  if (!cap) throw APIError.invalidArgument("capabilityId không được rỗng");

  if (p.decision === null) {
    await db
      .delete(workspaceCapabilityPolicy)
      .where(
        and(
          eq(workspaceCapabilityPolicy.workspaceId, wsId),
          eq(workspaceCapabilityPolicy.capabilityId, cap)
        )
      );
  } else {
    if (!["ALLOW", "REQUIRE_APPROVAL", "DENY"].includes(p.decision)) {
      throw APIError.invalidArgument("decision phải là ALLOW | REQUIRE_APPROVAL | DENY | null");
    }
    await db
      .insert(workspaceCapabilityPolicy)
      .values({
        workspaceId: wsId,
        capabilityId: cap,
        decision: p.decision,
        updatedBy: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
        updatedAt: new Date(),
      })
      .onConflictDoUpdate({
        target: [workspaceCapabilityPolicy.workspaceId, workspaceCapabilityPolicy.capabilityId],
        set: {
          decision: p.decision,
          updatedBy: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
          updatedAt: new Date(),
        },
      });
  }
  const rows = await db
```

(Giữ nguyên phần còn lại của hàm sau dòng `const rows = await db` — chỉ thêm dòng `requireFounderCommand` ở đầu và đổi `BigInt(p.workspaceId)` thành `BigInt(ctx.workspaceId)`.)

Kiểm tra: `p.workspaceId` không còn dùng trong thân hàm sau khi sửa — nếu `tsc` báo "declared but never read" thì đổi tham số `p` bỏ `workspaceId` khỏi type, và sửa 2 chỗ gọi (`execution-plan.handler.ts:203` và test) bớt field đó. Ưu tiên giữ field trong request type để không phá `POST /operations/capability-policy` request shape hiện tại (client vẫn gửi `workspaceId` trong body/header như cũ) — chỉ ngừng tin nó khi ghi DB.

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `set -a && source ../../.env && set +a && encore test operations/tests/execution-plan-crud.test.ts`
Expected: toàn bộ PASS, bao gồm 2 test mới.

- [ ] **Step 5: Chạy lại toàn bộ suite operations liên quan + typecheck**

Run: `cd services/company && npx tsc --noEmit && set -a && source ../.env && set +a && encore test operations/`
Expected: PASS, không regress test cũ dùng `setCapabilityPolicyService`/`setCapabilityPolicy` handler.

- [ ] **Step 6: Commit**

```bash
git add services/company/operations/services/execution-plan.service.ts \
        services/company/operations/tests/execution-plan-crud.test.ts
git commit -m "fix(company): bắt buộc quyền founder và bind workspace theo ctx khi set capability policy (IA01)"
```

---

### Task 3: IA17 — Resume AI deployment phải đi qua kiểm tra quyền hiện tại, không chỉ so approvedByMemberId lưu sẵn

**Files:**
- Modify: `services/company/finance-legal/handlers/ai-compliance-governance.handler.ts:129-141` (`resumeAiDeploymentApi`)
- Test: `services/company/finance-legal/tests/ai-compliance-governance.test.ts` (thêm case revocation)

**Interfaces:**
- Consumes: `resumeAiDeployment(input: ResumeAiDeploymentInput, ctx?: TenantContext)` (đã tồn tại ở `ai-compliance-governance.service.ts:436` — khi có `ctx`, gọi `authorizeBusinessAction(ctx, "ai.deployment.approve", {...})`; khi không có `ctx`, dùng fallback so `resumedByMemberId` với `founderMemberId`/`approvedByMemberId` lưu trong DB — **fallback này giữ nguyên** cho các caller nội bộ không qua HTTP (không có trong scope IA17, không đổi).
- Consumes: `requireCommandAuthority(ctx, action, scope?, facts?)` từ `../../identity/services/command-authority.service` (đã import sẵn ở dòng 4 của handler, dùng cho create/approve).
- Produces: hành vi endpoint `POST /finance-legal/ai-compliance/deployments/:deploymentId/resume` — không đổi request/response shape.

- [ ] **Step 1: Viết test thất bại — thành viên từng approve, sau đó mất quyền, không thể resume**

Thêm vào `services/company/finance-legal/tests/ai-compliance-governance.test.ts`:

```ts
import type { TenantContext } from "../../shared/types/tenant_context";
```

(thêm vào đầu file cùng các import khác)

```ts
it("denies resume when the ctx no longer holds ai.deployment.approve, even for the original approver (IA17)", async () => {
  const ws3 = String(generateSnowflake());
  const founder3 = String(generateSnowflake());

  const { versionId } = await seedCatalogAndVersion();
  const deployment = await createAiDeployment({
    workspaceId: ws3,
    systemVersionId: versionId,
    mode: "ADVISORY_ONLY",
    founderMemberId: founder3,
    technicalOwnerMemberId: founder3,
  });

  const assessment = await submitAiAssessment({
    workspaceId: ws3,
    deploymentId: deployment.id,
    classification: "OUT_OF_CATALOG",
    intendedPurpose: "private-business advisory",
    controls: ["HUMAN_CONFIRMATION"],
    expiresAt: "2027-01-01T00:00:00Z",
  });

  await seedApprovedProviderAndDataProfile(ws3, deployment.id);

  const evidenceId = generateSnowflake();
  await db.insert(aiComplianceEvidence).values({
    id: evidenceId,
    workspaceId: BigInt(ws3),
    assessmentId: BigInt(assessment.id),
    evidenceType: "POLICY_GATE",
    uriReference: "vault://evidence/policy-ia17",
    contentHash: "sha256:ia17",
    reviewerMemberId: BigInt(founder3),
  });

  await approveAiAssessment({
    workspaceId: ws3,
    deploymentId: deployment.id,
    assessmentId: assessment.id,
    approvedByMemberId: founder3,
    rationale: "Founder approves deployment",
    expiresAt: "2027-01-01T00:00:00Z",
  });

  await suspendAiDeployment({
    workspaceId: ws3,
    deploymentId: deployment.id,
    rationale: "Routine audit",
    suspendedByMemberId: founder3,
  });

  // founder3 bị hạ quyền: ctx hiện tại của họ không còn membershipRole founder
  // và không có role assignment nào cấp ai.deployment.approve — mô phỏng
  // "quyền approve đã bị thu hồi" dù họ vẫn đứng tên approvedByMemberId trong DB.
  const revokedCtx: TenantContext = {
    workspaceId: ws3,
    userId: founder3,
    workforceMemberId: founder3,
    membershipRole: "member",
    permissions: [],
    correlationId: "test-ia17-revoked",
  };

  await expect(
    resumeAiDeployment(
      {
        workspaceId: ws3,
        deploymentId: deployment.id,
        rationale: "Trying to resume after revocation",
        resumedByMemberId: founder3,
      },
      revokedCtx
    )
  ).rejects.toMatchObject({ code: "PERMISSION_DENIED" });

  const reloaded = await getDeployment(ws3, deployment.id);
  expect(reloaded.status).toBe("SUSPENDED");
});
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run (từ `services/company`): `set -a && source ../../.env && set +a && encore test finance-legal/tests/ai-compliance-governance.test.ts`
Expected: FAIL — vì test này gọi thẳng `resumeAiDeployment(input, revokedCtx)` ở service layer, và service đã hỗ trợ `ctx` nên thực ra bước này sẽ PASS ở mức service. **Đây là điểm mấu chốt:** lỗ hổng thật nằm ở handler không truyền `ctx`, nên bước 2 thật sự cần kiểm ở handler, không phải service. Sửa lại: nếu Step 1 pass ngay (service đã đúng), nghĩa là bug chỉ ở handler — chuyển sang viết test tái hiện qua handler thay vì service. Xem Step 2b.

- [ ] **Step 2b: Nếu Step 1 pass ngay ở service layer, xác nhận lỗ hổng thật ở handler bằng cách đọc lại `resumeAiDeploymentApi`**

Đọc `services/company/finance-legal/handlers/ai-compliance-governance.handler.ts:129-141` — xác nhận `resumeAiDeployment(...)` được gọi **không có** `ctx` (chỉ có object input), khác với `approveAiAssessmentApi` (dòng 104-111) truyền `ctx` làm tham số thứ hai. Đây chính là gap: mọi request HTTP thật đi qua handler này sẽ luôn rơi vào fallback (so `resumedByMemberId` với DB), bất kể ctx hiện tại có quyền hay không. Test ở Step 1 đã đúng chứng minh service hỗ trợ ctx nhưng **không được handler dùng** — giữ test đó lại (nó bảo vệ hành vi service), và bổ sung fix ở handler tại Step 3.

- [ ] **Step 3: Sửa `resumeAiDeploymentApi` để bắt buộc dùng ctx**

Trong `services/company/finance-legal/handlers/ai-compliance-governance.handler.ts`:

```ts
export const resumeAiDeploymentApi = api(
  { method: "POST", path: "/finance-legal/ai-compliance/deployments/:deploymentId/resume", expose: true },
  async (req: ResumeAiDeploymentRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    await requireCommandAuthority(ctx, "ai.deployment.approve", { workspaceId: String(ctx.workspaceId) });
    const memberId = ctx.workforceMemberId || ctx.userId;
    return resumeAiDeployment(
      {
        workspaceId: ctx.workspaceId,
        deploymentId: req.deploymentId,
        rationale: req.rationale,
        resumedByMemberId: memberId,
      },
      ctx
    );
  }
);
```

Lưu ý: thêm `requireCommandAuthority(...)` trước khi gọi service là phòng thủ ở lớp handler (nhất quán với `approveAiAssessmentApi`), còn việc truyền `ctx` vào `resumeAiDeployment(...)` mới là chỗ đóng lỗ hổng chính (service tự re-evaluate quyền theo `ctx` thay vì tin `resumedByMemberId` client gửi lên).

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `set -a && source ../../.env && set +a && encore test finance-legal/tests/ai-compliance-governance.test.ts`
Expected: PASS toàn bộ, bao gồm test lifecycle cũ ("handles suspend and resume lifecycle transitions" — vẫn dùng fallback vì gọi service trực tiếp không qua handler, không bị ảnh hưởng) và test mới IA17.

- [ ] **Step 5: Chạy toàn bộ suite finance-legal liên quan ai-compliance + typecheck**

Run: `cd services/company && npx tsc --noEmit && set -a && source ../.env && set +a && encore test finance-legal/tests/ai-compliance-governance.test.ts finance-legal/tests/ai-compliance-workspace-access.test.ts finance-legal/tests/ai-compliance-private-contract.test.ts finance-legal/tests/deployment-authority.test.ts`
Expected: PASS toàn bộ, không regress (`suspendAiDeployment`/`ai-incident-response.service.ts`/`ai-compliance-e2e-seed.service.ts` không đổi, vẫn gọi không có `ctx`).

- [ ] **Step 6: Commit**

```bash
git add services/company/finance-legal/handlers/ai-compliance-governance.handler.ts \
        services/company/finance-legal/tests/ai-compliance-governance.test.ts
git commit -m "fix(company): resume AI deployment phải re-check quyền hiện tại qua ctx, không tin DB cũ (IA17)"
```

---

## Ngoài phạm vi batch này (để lại cho phase kế tiếp, không tự mở rộng)

- IA02 (business policy runtime wiring vào gateway Python↔TS) — kiến trúc lớn hơn, cần plan riêng.
- IA18/IA19/IA20 và các mục S1-S5/R1-R4/F-series — theo đúng thứ tự đề xuất ở mục 5 của audit, xử lý ở các plan kế tiếp sau khi batch này merge.

# Seed dữ liệu mẫu + Golden-path E2E test cho services/company — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tạo một script seed dữ liệu mẫu (chủ đề "Quốc Gia Khởi Nghiệp") chạy qua API thật của `services/company`, và một test tự động end-to-end tái hiện đúng luồng đó, để vừa có dữ liệu demo vừa có test suite bền vững.

**Architecture:** Hai file độc lập, cùng nội dung nghiệp vụ (1 workspace → 1 organization → OKR/operations → commercial → finance-legal), khác cơ chế gọi: `scripts/seed-demo.mjs` gọi qua HTTP tới `encore run` đang chạy ở `localhost:4000` (dùng để demo/xem dữ liệu thật trong DB); `shared/tests/golden-path.e2e.test.ts` gọi trực tiếp các hàm handler trong cùng process qua `encore test` (đúng pattern 28 test hiện có trong repo — xem `identity/tests/register.test.ts`). Không dùng chung code gọi API vì hai cơ chế (HTTP fetch vs in-process handler call) không tương thích nhau trong Encore; nội dung nghiệp vụ (tên workspace, thứ tự bước) được giữ nhất quán thủ công giữa 2 file.

**Tech Stack:** Node.js (fetch built-in, ESM `.mjs`), TypeScript + vitest (qua `encore test`), Encore.ts handlers hiện có (không tạo handler mới).

## Global Constraints

- Không insert thẳng DB — mọi dữ liệu mẫu phải đi qua handler/API thật (đúng nguyên tắc #1 CLAUDE.md: business truth thuộc services/*).
- Không tạo migration mới, không thêm handler mới — chỉ dùng endpoint hiện có.
- Giao dịch tài chính dùng direction `"IN"` để được `AUTO_APPROVED` — role mặc định khi đăng ký là `"admin"` (`["read","write"]`), không có quyền `"*"` (founder/co-founder) cần để duyệt giao dịch `OUT` vượt ngưỡng 10,000,000 VND (xem `finance-legal/services/financial-transaction.service.ts:140-155`). Không có endpoint nào đổi role thành founder — đây là giới hạn thật của hệ thống, không phải workaround.
- `Header<"Authorization">` trong Encore: khi gọi qua HTTP phải set HTTP header `Authorization: Bearer <token>`; khi gọi trực tiếp hàm handler (trong test) thì truyền `authorization: "Bearer <token>"` như một field bình thường trong object params (đúng pattern các test hiện có).
- Không tuyên bố hoàn thành khi `make services-test-company` chưa xanh (quy tắc #11 CLAUDE.md).

---

### Task 1: Xác nhận baseline test suite hiện tại

**Files:** không sửa file nào — chỉ chạy lệnh.

- [ ] **Step 1: Chạy toàn bộ suite hiện có**

Run: `cd /Volumes/SSD/javis-saas && make services-test-company`

- [ ] **Step 2: Ghi nhận kết quả**

Nếu tất cả 28 test hiện có PASS: tiếp tục Task 2.
Nếu có test FAIL: dừng lại, báo cáo chính xác test nào fail + thông điệp lỗi cho người dùng trước khi viết thêm code mới — không tự ý sửa hành vi ngoài phạm vi seed/e2e của plan này trừ khi được xác nhận.

---

### Task 2: Script seed dữ liệu mẫu qua HTTP (`seed-demo.mjs`)

**Files:**
- Create: `services/company/scripts/seed-demo.mjs`

**Interfaces:**
- Không phụ thuộc task khác. Chạy độc lập, yêu cầu `encore run --port=4000` (hoặc `make services-dev-company`) đang sống.
- Produces: workspace "Quốc Gia Khởi Nghiệp" với dữ liệu mẫu xuyên suốt 4 module, in ra id từng bước ra stdout.

- [ ] **Step 1: Viết script**

```js
#!/usr/bin/env node
// services/company/scripts/seed-demo.mjs
// Seed dữ liệu mẫu chủ đề "Quốc Gia Khởi Nghiệp" qua API thật của services/company.
// Yêu cầu: encore run đang chạy tại COMPANY_API_URL (mặc định http://127.0.0.1:4000).

const BASE_URL = process.env.COMPANY_API_URL || "http://127.0.0.1:4000";

async function call(method, path, body, token) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let json;
  try {
    json = text ? JSON.parse(text) : {};
  } catch {
    json = { raw: text };
  }
  if (!res.ok) {
    throw new Error(`${method} ${path} -> HTTP ${res.status}: ${text}`);
  }
  return json;
}

async function main() {
  console.log(`Seeding demo data at ${BASE_URL} ...\n`);

  // ── 1. Identity ──────────────────────────────────────────
  const email = `founder-${Date.now()}@quocgiakhoinghiep.vn`;
  const register = await call("POST", "/identity/register", {
    email,
    password: "StartupNation#2026",
    displayName: "Founder Quốc Gia Khởi Nghiệp",
  });
  const token = register.accessToken;
  const workspaceId = register.workspaceId;
  console.log(`✓ register: userId=${register.userId} workspaceId=${workspaceId}`);

  const organization = await call(
    "POST",
    "/identity/organizations",
    { workspaceId, name: "Quốc Gia Khởi Nghiệp" },
    token
  );
  console.log(`✓ organization: id=${organization.id}`);

  const coFounder = await call(
    "POST",
    "/identity/workforce-members",
    { organizationId: organization.id, memberType: "HUMAN", roleTitle: "Co-founder / COO" },
    token
  );
  console.log(`✓ workforce member (human): id=${coFounder.id}`);

  const aiMember = await call(
    "POST",
    "/identity/workforce-members",
    {
      organizationId: organization.id,
      memberType: "AI_AGENT",
      roleTitle: "AI Ops Copilot",
      agentProfileId: "cosa-ops-copilot",
    },
    token
  );
  console.log(`✓ workforce member (AI agent): id=${aiMember.id}`);

  // ── 2. Operations ────────────────────────────────────────
  const okrCycle = await call(
    "POST",
    "/operations/okr-cycles",
    { workspaceId, name: "Q1 2026 - Launch nền tảng Quốc Gia Khởi Nghiệp" },
    token
  );
  console.log(`✓ okr cycle: id=${okrCycle.id}`);

  const objective = await call(
    "POST",
    "/operations/objectives",
    {
      workspaceId,
      cycleId: okrCycle.id,
      title: "Trở thành nền tảng vận hành số 1 cho startup Việt Nam",
      why: "Giúp founder tập trung xây sản phẩm thay vì vận hành",
    },
    token
  );
  console.log(`✓ objective: id=${objective.id}`);

  const keyResult = await call(
    "POST",
    `/operations/objectives/${objective.id}/key-results`,
    { objectiveId: objective.id, title: "100 startup onboard nền tảng", targetValue: 100, unit: "startups" },
    token
  );
  console.log(`✓ key result: id=${keyResult.id}`);

  const initiative = await call(
    "POST",
    "/operations/initiatives",
    { workspaceId, title: "Ra mắt COSA Agent Platform bản beta" },
    token
  );
  console.log(`✓ initiative: id=${initiative.id}`);

  const project = await call(
    "POST",
    "/operations/projects",
    {
      workspaceId,
      title: "COSA Beta Launch",
      description: "Triển khai bản beta cho 100 startup đầu tiên",
      phase: "execution",
    },
    token
  );
  console.log(`✓ project: id=${project.id}`);

  const task1 = await call(
    "POST",
    "/operations/tasks",
    { workspaceId, title: "Hoàn thiện luồng onboarding founder", priority: "high", initiativeId: initiative.id },
    token
  );
  console.log(`✓ task: id=${task1.id}`);

  const task2 = await call(
    "POST",
    "/operations/tasks",
    { workspaceId, title: "Demo sản phẩm cho 10 startup thí điểm", priority: "medium", initiativeId: initiative.id },
    token
  );
  console.log(`✓ task: id=${task2.id}`);

  await call(
    "POST",
    "/operations/task-dependencies",
    { taskId: task2.id, dependsOnTaskId: task1.id, dependencyType: "BLOCKS" },
    token
  );
  console.log(`✓ task dependency: ${task2.id} depends on ${task1.id}`);

  const cycle12w = await call(
    "POST",
    "/operations/cycles",
    {
      workspaceId,
      visionStatement: "12 tuần đưa COSA ra thị trường quốc gia khởi nghiệp",
      stageAtStart: "S1_PROBLEM_VALIDATION",
    },
    token
  );
  console.log(`✓ 12-week cycle: id=${cycle12w.id}`);

  const weeklyPlan = await call(
    "POST",
    "/operations/weekly-plans",
    { workspaceId, cycleId: cycle12w.id, weekNo: 1, focus: "Onboarding + demo sản phẩm" },
    token
  );
  console.log(`✓ weekly plan: id=${weeklyPlan.id}`);

  await call(
    "POST",
    "/operations/weekly-commitments",
    { workspaceId, weeklyPlanId: weeklyPlan.id, title: "Demo sản phẩm cho 10 startup thí điểm" },
    token
  );
  console.log(`✓ weekly commitment created`);

  // ── 3. Commercial ────────────────────────────────────────
  const lead = await call(
    "POST",
    "/commercial/leads",
    { workspaceId, name: "Startup Xanh", company: "Startup Xanh JSC", source: "landing-page" },
    token
  );
  console.log(`✓ lead: id=${lead.id}`);

  const account = await call(
    "POST",
    "/commercial/accounts",
    { workspaceId, name: "Startup Xanh JSC", industry: "AgriTech", country: "VN" },
    token
  );
  console.log(`✓ account: id=${account.id}`);

  const contact = await call(
    "POST",
    "/commercial/contacts",
    { workspaceId, accountId: account.id, name: "Nguyễn Văn A", title: "CEO", email: "ceo@startupxanh.vn" },
    token
  );
  console.log(`✓ contact: id=${contact.id}`);

  const opportunity = await call(
    "POST",
    "/commercial/opportunities",
    {
      workspaceId,
      accountId: account.id,
      primaryContactId: contact.id,
      sourceLeadId: lead.id,
      product: "COSA Agent Platform",
      estimatedValue: 120000000,
    },
    token
  );
  console.log(`✓ opportunity: id=${opportunity.id}`);

  const customer = await call(
    "POST",
    "/commercial/customers",
    { workspaceId, accountId: account.id, acquiredFromOpportunityId: opportunity.id },
    token
  );
  console.log(`✓ customer: id=${customer.id}`);

  const campaign = await call(
    "POST",
    "/commercial/campaigns",
    {
      workspaceId,
      name: "Ra mắt Quốc Gia Khởi Nghiệp 2026",
      funnelStage: "awareness",
      channels: ["facebook", "email"],
      budget: 50000000,
    },
    token
  );
  console.log(`✓ campaign: id=${campaign.id}`);

  const invoice = await call(
    "POST",
    "/commercial/invoices",
    { workspaceId, customerId: customer.id, invoiceNumber: `INV-${Date.now()}`, amount: 12000000, currency: "VND" },
    token
  );
  console.log(`✓ invoice: id=${invoice.id}`);

  const subscription = await call(
    "POST",
    "/commercial/subscriptions",
    { workspaceId, customerId: customer.id, planName: "COSA Growth", price: 4000000, currency: "VND" },
    token
  );
  console.log(`✓ subscription: id=${subscription.id}`);

  // ── 4. Finance-Legal ─────────────────────────────────────
  const accountingProfile = await call(
    "POST",
    "/finance-legal/accounting-profiles",
    { workspaceId },
    token
  );
  console.log(`✓ accounting profile: id=${accountingProfile.id}`);

  const fiscalProfile = await call(
    "POST",
    "/finance-legal/fiscal-profiles",
    { workspaceId, fiscalYear: 2026, regulationCode: "VN_GAAP" },
    token
  );
  console.log(`✓ fiscal profile: id=${fiscalProfile.id}`);

  const period = await call(
    "POST",
    "/finance-legal/accounting-periods",
    { workspaceId, startDate: "2026-01-01", endDate: "2026-01-31" },
    token
  );
  console.log(`✓ accounting period: id=${period.id}`);

  const transaction = await call(
    "POST",
    "/finance-legal/transactions",
    {
      workspaceId,
      transactionDate: "2026-01-15",
      description: "Thu phí subscription COSA Growth từ Startup Xanh JSC",
      amount: "4000000",
      direction: "IN",
      category: "revenue",
    },
    token
  );
  console.log(`✓ financial transaction: id=${transaction.id} status=${transaction.approvalStatus}`);

  const obligation = await call(
    "POST",
    "/finance-legal/obligations",
    { workspaceId, title: "Nộp báo cáo thuế GTGT tháng 1/2026", dueAt: "2026-02-20" },
    token
  );
  console.log(`✓ legal obligation: id=${obligation.id}`);

  await call("POST", `/finance-legal/obligations/${obligation.id}/fulfill`, {}, token);
  console.log(`✓ obligation fulfilled`);

  const checklistItem = await call(
    "POST",
    "/finance-legal/checklist-items",
    { workspaceId, title: "Đăng ký giấy phép kinh doanh ngành công nghệ" },
    token
  );
  console.log(`✓ checklist item: id=${checklistItem.id}`);

  await call("POST", `/finance-legal/checklist-items/${checklistItem.id}/complete`, {}, token);
  console.log(`✓ checklist item completed`);

  const snapshot = await call(
    "POST",
    "/finance-legal/snapshots",
    { workspaceId, asOf: "2026-01-31", cash: "500000000", burn: "80000000", revenue: "16000000", expenses: "80000000" },
    token
  );
  console.log(`✓ finance snapshot: id=${snapshot.id}`);

  const hypothesis = await call(
    "POST",
    "/finance-legal/hypotheses",
    {
      workspaceId,
      title: "Startup sẵn sàng trả phí cho nền tảng vận hành hợp nhất",
      statement: "Nếu COSA giảm 50% thời gian vận hành, founder sẽ trả subscription hàng tháng",
    },
    token
  );
  console.log(`✓ hypothesis: id=${hypothesis.id}`);

  const experiment = await call(
    "POST",
    "/finance-legal/experiments",
    { workspaceId, hypothesisId: hypothesis.id, title: "Pilot 10 startup dùng thử 30 ngày", experimentType: "pilot" },
    token
  );
  console.log(`✓ experiment: id=${experiment.id}`);

  await call(
    "POST",
    "/finance-legal/evidence",
    {
      workspaceId,
      experimentId: experiment.id,
      title: "8/10 startup pilot đồng ý trả phí sau 30 ngày",
      content: "80% conversion rate trong nhóm pilot, phản hồi tích cực về tính năng OKR + tài chính hợp nhất",
      strengthScore: 0.8,
    },
    token
  );
  console.log(`✓ evidence item created`);

  console.log(`\n✅ Seed hoàn tất. workspaceId=${workspaceId} founderEmail=${email}`);
}

main().catch((err) => {
  console.error(`\n❌ Seed thất bại: ${err.message}`);
  process.exit(1);
});
```

- [ ] **Step 2: Đảm bảo có instance Encore đang chạy**

Run (terminal riêng, để chạy nền): `cd services/company && encore run --port=4000`
Đợi tới khi log báo `Encore development server running`.

- [ ] **Step 3: Chạy thử script**

Run: `cd services/company && node scripts/seed-demo.mjs`
Expected: log in ra đủ ~30 dòng `✓ ...`, kết thúc bằng `✅ Seed hoàn tất.` — không có dòng `❌`.

- [ ] **Step 4: Xác nhận dữ liệu thật trong DB**

Run: `docker exec -it company_db psql -U postgres -d company -c "select id, name from identity_workspaces order by id desc limit 1;"` (điều chỉnh tên user/db nếu khác — kiểm tra qua `docker inspect company_db` hoặc `services/docker-compose.yml` nếu lệnh trên báo lỗi credential).
Expected: có 1 row tên "Quốc Gia Khởi Nghiệp"-liên-quan (workspace name do `registerUserService` tự đặt là `Workspace của Founder Quốc Gia Khởi Nghiệp`).

- [ ] **Step 5: Commit**

```bash
git add services/company/scripts/seed-demo.mjs
git commit -m "feat(company): thêm script seed dữ liệu mẫu qua API — chủ đề Quốc Gia Khởi Nghiệp"
```

---

### Task 3: Golden-path integration test (`golden-path.e2e.test.ts`)

**Files:**
- Create: `services/company/shared/tests/golden-path.e2e.test.ts`

**Interfaces:**
- Consumes (import trực tiếp, gọi in-process — không qua HTTP):
  - `services/company/identity/handlers/auth.handler.ts`: `registerUser(params: RegisterParams): Promise<RegisterResult>`
  - `services/company/identity/handlers/organization.handler.ts`: `createOrganization`, `hireWorkforceMember`
  - `services/company/operations/handlers/okr.handler.ts`: `createOkrCycle`, `createObjective`, `addKeyResult`
  - `services/company/operations/handlers/initiative.handler.ts`: `createInitiative`
  - `services/company/operations/handlers/project.handler.ts`: `createProject`
  - `services/company/operations/handlers/task.handler.ts`: `createTask`
  - `services/company/operations/handlers/task-dependency.handler.ts`: `createTaskDependency`
  - `services/company/operations/handlers/twelve-week-year.handler.ts`: `createCycle`, `createWeeklyPlan`, `createWeeklyCommitment`
  - `services/company/commercial/handlers/lead.handler.ts`: `createSalesLead`
  - `services/company/commercial/handlers/account.handler.ts`: `createAccount`
  - `services/company/commercial/handlers/contact.handler.ts`: `createContact`
  - `services/company/commercial/handlers/opportunity.handler.ts`: `createSalesOpportunity`
  - `services/company/commercial/handlers/customer.handler.ts`: `createCustomer`
  - `services/company/commercial/handlers/marketing.handler.ts`: `createCampaign`
  - `services/company/commercial/handlers/billing.handler.ts`: `createInvoice`, `createSubscription`
  - `services/company/finance-legal/handlers/accounting-profile.handler.ts`: `createAccountingProfile`
  - `services/company/finance-legal/handlers/accounting-regime.handler.ts`: `createFiscalProfile`
  - `services/company/finance-legal/handlers/accounting-period.handler.ts`: `openAccountingPeriod`
  - `services/company/finance-legal/handlers/financial-transaction.handler.ts`: `recordFinancialTransaction`
  - `services/company/finance-legal/handlers/legal-obligation.handler.ts`: `createObligation`, `fulfillObligation`
  - `services/company/finance-legal/handlers/legal-checklist-item.handler.ts`: `createChecklistItem`, `completeChecklistItem`
  - `services/company/finance-legal/handlers/finance-snapshot.handler.ts`: `recordFinanceSnapshot`
  - `services/company/finance-legal/handlers/validation.handler.ts`: `createHypothesis`, `createExperiment`, `createEvidence`
- Produces: không có (test terminal, không có task nào phụ thuộc ngược lại).

- [ ] **Step 1: Viết test (toàn bộ golden path trong 1 `it`, assert mỗi bước)**

```ts
// services/company/shared/tests/golden-path.e2e.test.ts
import { describe, expect, it } from "vitest";
import { registerUser } from "../../identity/handlers/auth.handler";
import { createOrganization, hireWorkforceMember } from "../../identity/handlers/organization.handler";
import { createOkrCycle, createObjective, addKeyResult } from "../../operations/handlers/okr.handler";
import { createInitiative } from "../../operations/handlers/initiative.handler";
import { createProject } from "../../operations/handlers/project.handler";
import { createTask } from "../../operations/handlers/task.handler";
import { createTaskDependency } from "../../operations/handlers/task-dependency.handler";
import { createCycle, createWeeklyPlan, createWeeklyCommitment } from "../../operations/handlers/twelve-week-year.handler";
import { createSalesLead } from "../../commercial/handlers/lead.handler";
import { createAccount } from "../../commercial/handlers/account.handler";
import { createContact } from "../../commercial/handlers/contact.handler";
import { createSalesOpportunity } from "../../commercial/handlers/opportunity.handler";
import { createCustomer } from "../../commercial/handlers/customer.handler";
import { createCampaign } from "../../commercial/handlers/marketing.handler";
import { createInvoice, createSubscription } from "../../commercial/handlers/billing.handler";
import { createAccountingProfile } from "../../finance-legal/handlers/accounting-profile.handler";
import { createFiscalProfile } from "../../finance-legal/handlers/accounting-regime.handler";
import { openAccountingPeriod } from "../../finance-legal/handlers/accounting-period.handler";
import { recordFinancialTransaction } from "../../finance-legal/handlers/financial-transaction.handler";
import { createObligation, fulfillObligation } from "../../finance-legal/handlers/legal-obligation.handler";
import { createChecklistItem, completeChecklistItem } from "../../finance-legal/handlers/legal-checklist-item.handler";
import { recordFinanceSnapshot } from "../../finance-legal/handlers/finance-snapshot.handler";
import { createHypothesis, createExperiment, createEvidence } from "../../finance-legal/handlers/validation.handler";

describe("golden path: Quốc Gia Khởi Nghiệp", () => {
  it("chạy trọn vòng đời một tổ chức qua identity → operations → commercial → finance-legal", async () => {
    // ── Identity ──
    const email = `golden-${Date.now()}@quocgiakhoinghiep.vn`;
    const register = await registerUser({
      email,
      password: "StartupNation#2026",
      displayName: "Founder Quốc Gia Khởi Nghiệp",
    });
    expect(register.workspaceId).toBeGreaterThan(0);
    const workspaceId = register.workspaceId;
    const auth = `Bearer ${register.accessToken}`;

    const organization = await createOrganization({ workspaceId, name: "Quốc Gia Khởi Nghiệp" });
    expect(organization.id).toBeGreaterThan(0);

    const coFounder = await hireWorkforceMember({
      organizationId: organization.id,
      memberType: "HUMAN",
      roleTitle: "Co-founder / COO",
    });
    expect(coFounder.memberType).toBe("HUMAN");

    const aiMember = await hireWorkforceMember({
      organizationId: organization.id,
      memberType: "AI_AGENT",
      roleTitle: "AI Ops Copilot",
      agentProfileId: "cosa-ops-copilot",
    });
    expect(aiMember.memberType).toBe("AI_AGENT");

    // ── Operations ──
    const okrCycle = await createOkrCycle({ workspaceId, name: "Q1 2026 - Launch nền tảng Quốc Gia Khởi Nghiệp" });
    const objective = await createObjective({
      workspaceId,
      cycleId: okrCycle.id,
      title: "Trở thành nền tảng vận hành số 1 cho startup Việt Nam",
      why: "Giúp founder tập trung xây sản phẩm thay vì vận hành",
    });
    const keyResult = await addKeyResult({
      objectiveId: objective.id,
      title: "100 startup onboard nền tảng",
      targetValue: 100,
      unit: "startups",
    });
    expect(keyResult.objectiveId).toBe(objective.id);

    const initiative = await createInitiative({
      workspaceId,
      title: "Ra mắt COSA Agent Platform bản beta",
      authorization: auth,
    });
    expect(initiative.workspaceId).toBe(workspaceId);

    const project = await createProject({
      workspaceId,
      title: "COSA Beta Launch",
      description: "Triển khai bản beta cho 100 startup đầu tiên",
      phase: "execution",
    });
    expect(project.workspaceId).toBe(workspaceId);

    const task1 = await createTask({
      workspaceId,
      title: "Hoàn thiện luồng onboarding founder",
      priority: "high",
      initiativeId: initiative.id,
      authorization: auth,
    });
    const task2 = await createTask({
      workspaceId,
      title: "Demo sản phẩm cho 10 startup thí điểm",
      priority: "medium",
      initiativeId: initiative.id,
      authorization: auth,
    });

    const dependency = await createTaskDependency({
      taskId: task2.id,
      dependsOnTaskId: task1.id,
      dependencyType: "BLOCKS",
    });
    expect(dependency.status).toBe("PENDING");

    const cycle12w = await createCycle({
      workspaceId,
      visionStatement: "12 tuần đưa COSA ra thị trường quốc gia khởi nghiệp",
      stageAtStart: "S1_PROBLEM_VALIDATION",
    });
    const weeklyPlan = await createWeeklyPlan({
      workspaceId,
      cycleId: cycle12w.id,
      weekNo: 1,
      focus: "Onboarding + demo sản phẩm",
    });
    const weeklyCommitment = await createWeeklyCommitment({
      workspaceId,
      weeklyPlanId: weeklyPlan.id,
      title: "Demo sản phẩm cho 10 startup thí điểm",
    });
    expect(weeklyCommitment.weeklyPlanId).toBe(weeklyPlan.id);

    // ── Commercial ──
    const lead = await createSalesLead({
      workspaceId,
      name: "Startup Xanh",
      company: "Startup Xanh JSC",
      source: "landing-page",
      authorization: auth,
    });
    const account = await createAccount({
      workspaceId,
      name: "Startup Xanh JSC",
      industry: "AgriTech",
      country: "VN",
      authorization: auth,
    });
    const contact = await createContact({
      workspaceId,
      accountId: account.id,
      name: "Nguyễn Văn A",
      title: "CEO",
      email: "ceo@startupxanh.vn",
      authorization: auth,
    });
    const opportunity = await createSalesOpportunity({
      workspaceId,
      accountId: account.id,
      primaryContactId: contact.id,
      sourceLeadId: lead.id,
      product: "COSA Agent Platform",
      estimatedValue: 120000000,
      authorization: auth,
    });
    expect(opportunity.accountId).toBe(account.id);

    const customer = await createCustomer({
      workspaceId,
      accountId: account.id,
      acquiredFromOpportunityId: opportunity.id,
      authorization: auth,
    });
    expect(customer.accountId).toBe(account.id);

    const campaign = await createCampaign({
      workspaceId,
      name: "Ra mắt Quốc Gia Khởi Nghiệp 2026",
      funnelStage: "awareness",
      channels: ["facebook", "email"],
      budget: 50000000,
      authorization: auth,
    });
    expect(campaign.workspaceId).toBe(workspaceId);

    const invoice = await createInvoice({
      workspaceId,
      customerId: customer.id,
      invoiceNumber: `INV-${Date.now()}`,
      amount: 12000000,
      currency: "VND",
      authorization: auth,
    });
    const subscription = await createSubscription({
      workspaceId,
      customerId: customer.id,
      planName: "COSA Growth",
      price: 4000000,
      currency: "VND",
      authorization: auth,
    });
    expect(subscription.customerId).toBe(customer.id);
    expect(invoice.customerId).toBe(customer.id);

    // ── Finance-Legal ──
    const accountingProfile = await createAccountingProfile({ workspaceId, authorization: auth });
    expect(accountingProfile.workspaceId).toBe(workspaceId);

    const fiscalProfile = await createFiscalProfile({
      workspaceId,
      fiscalYear: 2026,
      regulationCode: "VN_GAAP",
      authorization: auth,
    });
    expect(fiscalProfile.fiscalYear).toBe(2026);

    const period = await openAccountingPeriod({
      workspaceId,
      startDate: "2026-01-01",
      endDate: "2026-01-31",
      authorization: auth,
    });
    expect(period.status).toBeDefined();

    const transaction = await recordFinancialTransaction({
      workspaceId,
      transactionDate: "2026-01-15",
      description: "Thu phí subscription COSA Growth từ Startup Xanh JSC",
      amount: "4000000",
      direction: "IN",
      category: "revenue",
      authorization: auth,
    });
    expect(transaction.approvalStatus).toBe("AUTO_APPROVED");

    const obligation = await createObligation({
      workspaceId,
      title: "Nộp báo cáo thuế GTGT tháng 1/2026",
      dueAt: "2026-02-20",
      authorization: auth,
    });
    const fulfilled = await fulfillObligation({ id: obligation.id, authorization: auth });
    expect(fulfilled.id).toBe(obligation.id);
    expect(fulfilled.status).not.toBe(obligation.status);

    const checklistItem = await createChecklistItem({
      workspaceId,
      title: "Đăng ký giấy phép kinh doanh ngành công nghệ",
      authorization: auth,
    });
    const completedItem = await completeChecklistItem({ id: checklistItem.id, authorization: auth });
    expect(completedItem.id).toBe(checklistItem.id);

    const snapshot = await recordFinanceSnapshot({
      workspaceId,
      asOf: "2026-01-31",
      cash: "500000000",
      burn: "80000000",
      revenue: "16000000",
      expenses: "80000000",
      authorization: auth,
    });
    expect(snapshot.workspaceId).toBe(workspaceId);

    const hypothesis = await createHypothesis({
      workspaceId,
      title: "Startup sẵn sàng trả phí cho nền tảng vận hành hợp nhất",
      statement: "Nếu COSA giảm 50% thời gian vận hành, founder sẽ trả subscription hàng tháng",
      authorization: auth,
    });
    const experiment = await createExperiment({
      workspaceId,
      hypothesisId: hypothesis.id,
      title: "Pilot 10 startup dùng thử 30 ngày",
      experimentType: "pilot",
      authorization: auth,
    });
    const evidence = await createEvidence({
      workspaceId,
      experimentId: experiment.id,
      title: "8/10 startup pilot đồng ý trả phí sau 30 ngày",
      content: "80% conversion rate trong nhóm pilot, phản hồi tích cực về tính năng OKR + tài chính hợp nhất",
      strengthScore: 0.8,
      authorization: auth,
    });
    expect(evidence.experimentId).toBe(experiment.id);
  });
});
```

- [ ] **Step 2: Chạy test**

Run: `cd services/company && encore test golden-path`
Expected: 1 test PASS, không có test nào khác bị ảnh hưởng.

- [ ] **Step 3: Commit**

```bash
git add services/company/shared/tests/golden-path.e2e.test.ts
git commit -m "test(company): thêm golden-path e2e test xuyên suốt identity/operations/commercial/finance-legal"
```

---

### Task 4: Regression toàn bộ suite + báo cáo

**Files:** không sửa file nào.

- [ ] **Step 1: Chạy lại toàn bộ suite**

Run: `cd /Volumes/SSD/javis-saas && make services-test-company`
Expected: 29 test PASS (28 cũ + 1 golden-path mới), 0 FAIL.

- [ ] **Step 2: Nếu có FAIL**

Debug theo `superpowers:systematic-debugging` — xác định do seed script/test viết sai (sửa trong task tương ứng) hay do phát hiện bug thật trong handler (dừng lại, báo cáo cho người dùng trước khi sửa code nghiệp vụ ngoài phạm vi plan này).

- [ ] **Step 3: Báo cáo kết thúc**

Tổng hợp cho người dùng: trạng thái suite (xanh/số lượng test), đường dẫn 2 file mới, cách chạy lại seed (`node services/company/scripts/seed-demo.mjs` với `encore run` đang sống), và nhắc rằng phase tiếp theo (services/cosa, Agent Platform, frontend) cần spec riêng khi người dùng sẵn sàng.

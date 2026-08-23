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
  // Email/mật khẩu CỐ ĐỊNH (không random theo timestamp) để người dùng có thể
  // đăng nhập thật vào app và test bằng chính tài khoản này sau khi seed xong.
  const email = process.env.SEED_EMAIL || "founder@quocgiakhoinghiep.vn";
  const password = process.env.SEED_PASSWORD || "StartupNation#2026";

  let register;
  try {
    register = await call("POST", "/identity/register", {
      email,
      password,
      displayName: "Founder Quốc Gia Khởi Nghiệp",
    });
    console.log(`✓ register: userId=${register.userId} workspaceId=${register.workspaceId}`);
  } catch (err) {
    if (!String(err.message).includes("already")) throw err;
    console.log(
      `↻ Tài khoản ${email} đã tồn tại từ lần seed trước.\n` +
      `   Không seed lại (endpoint /identity/me hiện không dùng được để tra workspace cũ — đây là bug có sẵn ngoài phạm vi task này, không sửa ở đây).\n` +
      `   Đăng nhập bằng email/password ở trên để test trực tiếp.`
    );
    process.exit(0);
  }
  const token = register.accessToken;
  const workspaceId = register.workspaceId;

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

  console.log(`\n✅ Seed hoàn tất. workspaceId=${workspaceId}`);
  console.log(`   Đăng nhập test bằng: email=${email}  password=${password}`);
  console.log(`   (POST /identity/sessions với 2 giá trị trên để lấy accessToken)`);
}

main().catch((err) => {
  console.error(`\n❌ Seed thất bại: ${err.message}`);
  process.exit(1);
});

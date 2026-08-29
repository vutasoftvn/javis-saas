import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { hireWorkforceMember } from "../../identity/handlers/workforce.handler";
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



describe("golden path: Quốc Gia Khởi Nghiệp", () => {
  it("chạy trọn vòng đời một tổ chức qua identity → operations → commercial → finance-legal", async () => {
    // ── Identity ──
    const email = `golden-${Date.now()}@quocgiakhoinghiep.vn`;
    const session = await createTestSession({
      email,
      displayName: "Founder Quốc Gia Khởi Nghiệp",
    });
    expect(session.workspaceId).toBeTruthy();
    expect(typeof session.workspaceId).toBe("string");
    const workspaceId = session.workspaceId;
    const auth = `Bearer ${session.accessToken}`;

    const coFounder = await hireWorkforceMember({
      workspaceId,
      memberType: "HUMAN",
      roleTitle: "Co-founder / COO",
      humanUserId: session.userId,
      authorization: auth,
    });
    expect(coFounder.memberType).toBe("HUMAN");

    const aiMember = await hireWorkforceMember({
      workspaceId,
      memberType: "AI_AGENT",
      roleTitle: "AI Ops Copilot",
      agentSpecId: "cosa-ops-copilot",
      agentSpecVersion: "1.0",
      authorization: auth,
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
      authorization: auth,
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
      workspaceId,
      authorization: auth,
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
    const fulfilled = await fulfillObligation({ id: obligation.id, workspaceId, authorization: auth });
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
  });
});


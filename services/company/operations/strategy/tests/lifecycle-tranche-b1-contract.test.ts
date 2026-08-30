import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember, createSecondWorkspace, addMemberToWorkspace } from "../../tests/_helpers";
import { createProject, getProject } from "../../handlers/project.handler";
import { recordEvidence } from "../handlers/evidence.handler";
import { reviewEvidence } from "../handlers/evidence-review.handler";
import {
  createPilot,
  approvePilot,
  activatePilot,
  closePilot,
  getPilot,
  listPilots,
} from "../handlers/pilot-run.handler";

/**
 * Tranche B1 Contract Verification — chứng minh cùng các invariant đã kiểm chứng
 * ở Python agent-plane layer (tests/apps/cosa/test_lifecycle_tranche_b1_acceptance.py)
 * cũng đúng ở tầng Company service (TypeScript/Encore) — nguồn sự thật thật sự cho
 * business state. Agent plane chỉ có capability đọc (strategy.pilot.get) và tạo
 * draft đề xuất (strategy.pilot.create_draft); approve/activate là human-only qua
 * Company API, đây là nơi các bất biến đó được enforce bằng code thật.
 */
describe("COSA Lifecycle Tranche B1 Contract Verification (Pilot Run)", () => {
  it("creates a pilot draft referencing reviewed evidence on a P2 project", async () => {
    const ws = await createTestWorkspaceWithMember();

    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Contract Test P2 Project",
      description: "P2 project cho pilot draft contract test",
      lifecycleStage: "P2_SOLUTION_VALIDATION",
    });
    expect(project.lifecycleStage).toBe("P2_SOLUTION_VALIDATION");

    const candidateEvidence = await recordEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      sourceType: "customer_interview",
      claim: "Design partner cam kết pilot 3 tháng",
      sampleSize: 3,
      supportsOrRefutes: "supports",
    });
    // Evidence field name thực tế là `status`, giá trị khởi tạo là 'candidate'
    // (không phải `reviewStatus` như phỏng đoán ban đầu trong brief).
    expect(candidateEvidence.status).toBe("candidate");

    const reviewedEvidence = await reviewEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: candidateEvidence.id,
      action: "approve",
      comment: "Founder verified design partner commitment",
    });
    expect(reviewedEvidence.status).toBe("approved");

    const draft = await createPilot({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      designPartnerEvidenceRefs: [reviewedEvidence.id],
      metricContractArtifactRef: "artifact://ws/metrics/contract-v1",
      instrumentationArtifactRef: "artifact://ws/inst/contract-v1",
      onboardingArtifactRef: "artifact://ws/onb/contract-v1",
      rollbackArtifactRef: "artifact://ws/rb/contract-v1",
      releaseOwnerMemberId: ws.userId,
    });

    expect(draft.status).toBe("DRAFT");
    expect(draft.projectId).toBe(project.id);
    expect(draft.designPartnerEvidenceRefs).toContain(reviewedEvidence.id);
  });

  it("rejects pilot draft creation when a required artifact reference is missing", async () => {
    const ws = await createTestWorkspaceWithMember();

    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Contract Test Missing Artifact Project",
      lifecycleStage: "P2_SOLUTION_VALIDATION",
    });

    const evidence = await recordEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      sourceType: "customer_interview",
      claim: "Reviewed evidence for missing-artifact contract test",
    });
    await reviewEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: evidence.id,
      action: "approve",
    });

    // Thiếu rollbackArtifactRef — createPilotDraft validate field này ở tầng service
    // (pilot-run.service.ts) trước khi cho phép tạo DRAFT.
    await expect(
      createPilot({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        projectId: project.id,
        designPartnerEvidenceRefs: [evidence.id],
        metricContractArtifactRef: "artifact://ws/metrics/v1",
        instrumentationArtifactRef: "artifact://ws/inst/v1",
        onboardingArtifactRef: "artifact://ws/onb/v1",
        rollbackArtifactRef: "",
        releaseOwnerMemberId: ws.userId,
      })
    ).rejects.toThrow(/rollbackArtifactRef is required/i);
  });

  it("requires privileged role and non-empty approval reference for approvePilot and activatePilot", async () => {
    const ws = await createTestWorkspaceWithMember();
    const member = await addMemberToWorkspace(ws.workspaceId, "member");

    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Contract Test Privilege Project",
      lifecycleStage: "P2_SOLUTION_VALIDATION",
    });

    const evidence = await recordEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      sourceType: "customer_interview",
      claim: "Reviewed evidence for privilege contract test",
    });
    const reviewed = await reviewEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: evidence.id,
      action: "approve",
    });

    const draft = await createPilot({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      designPartnerEvidenceRefs: [reviewed.id],
      metricContractArtifactRef: "artifact://ws/metrics/v1",
      instrumentationArtifactRef: "artifact://ws/inst/v1",
      onboardingArtifactRef: "artifact://ws/onb/v1",
      rollbackArtifactRef: "artifact://ws/rb/v1",
      releaseOwnerMemberId: ws.userId,
    });

    // Member (non-privileged role) cannot approve
    await expect(
      approvePilot({
        authorization: member.bearerToken,
        workspaceId: ws.workspaceId,
        id: draft.id,
        approvalRef: "APR-PRIV-1",
      })
    ).rejects.toThrow(/founder|admin|privilege/i);

    // Empty approvalRef rejected even for privileged founder
    await expect(
      approvePilot({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        id: draft.id,
        approvalRef: "",
      })
    ).rejects.toThrow(/approvalRef is required/i);

    const approved = await approvePilot({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: draft.id,
      approvalRef: "APR-PRIV-1",
    });
    expect(approved.status).toBe("APPROVED");

    // Member (non-privileged role) cannot activate
    await expect(
      activatePilot({
        authorization: member.bearerToken,
        workspaceId: ws.workspaceId,
        id: draft.id,
        approvalRef: "APR-PRIV-1",
      })
    ).rejects.toThrow(/founder|admin|privilege/i);

    // Empty approvalRef rejected even for privileged founder
    await expect(
      activatePilot({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        id: draft.id,
        approvalRef: "",
      })
    ).rejects.toThrow(/approvalRef is required/i);
  });

  it("keeps project lifecycleStage unchanged after pilot activation (core invariant)", async () => {
    const ws = await createTestWorkspaceWithMember();

    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Contract Test Invariant Project",
      lifecycleStage: "P2_SOLUTION_VALIDATION",
    });

    const evidence = await recordEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      sourceType: "customer_interview",
      claim: "Reviewed evidence for invariant contract test",
    });
    const reviewed = await reviewEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: evidence.id,
      action: "approve",
    });

    const draft = await createPilot({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      designPartnerEvidenceRefs: [reviewed.id],
      metricContractArtifactRef: "artifact://ws/metrics/v1",
      instrumentationArtifactRef: "artifact://ws/inst/v1",
      onboardingArtifactRef: "artifact://ws/onb/v1",
      rollbackArtifactRef: "artifact://ws/rb/v1",
      releaseOwnerMemberId: ws.userId,
    });

    await approvePilot({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: draft.id,
      approvalRef: "APR-INVARIANT-1",
    });

    const active = await activatePilot({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: draft.id,
      approvalRef: "APR-INVARIANT-1",
    });
    expect(active.status).toBe("ACTIVE");

    const projectAfter = await getProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    // Bất biến cốt lõi: kích hoạt pilot KHÔNG BAO GIỜ thay đổi lifecycle stage —
    // quyền chuyển stage thuộc riêng về Stage Gate quyết định bởi Founder.
    expect(projectAfter.lifecycleStage).toBe("P2_SOLUTION_VALIDATION");
  });

  it("isolates workspaces: workspace B cannot list, get, approve, or activate workspace A's pilot", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createTestWorkspaceWithMember();

    const project = await createProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      title: "Contract Test Isolation Project",
      lifecycleStage: "P2_SOLUTION_VALIDATION",
    });

    const evidence = await recordEvidence({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: project.id,
      sourceType: "customer_interview",
      claim: "Reviewed evidence for isolation contract test",
    });
    const reviewed = await reviewEvidence({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: evidence.id,
      action: "approve",
    });

    const draft = await createPilot({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: project.id,
      designPartnerEvidenceRefs: [reviewed.id],
      metricContractArtifactRef: "artifact://ws-a/metrics/v1",
      instrumentationArtifactRef: "artifact://ws-a/inst/v1",
      onboardingArtifactRef: "artifact://ws-a/onb/v1",
      rollbackArtifactRef: "artifact://ws-a/rb/v1",
      releaseOwnerMemberId: wsA.userId,
    });

    await expect(
      getPilot({ authorization: wsB.bearerToken, workspaceId: wsB.workspaceId, id: draft.id })
    ).rejects.toThrow(/not found|không tồn tại/i);

    const listResultB = await listPilots({
      authorization: wsB.bearerToken,
      workspaceId: wsB.workspaceId,
      projectId: project.id,
    });
    expect(listResultB.items.length).toBe(0);

    await expect(
      approvePilot({
        authorization: wsB.bearerToken,
        workspaceId: wsB.workspaceId,
        id: draft.id,
        approvalRef: "APR-ISO-B",
      })
    ).rejects.toThrow(/not found|không tồn tại/i);

    await expect(
      activatePilot({
        authorization: wsB.bearerToken,
        workspaceId: wsB.workspaceId,
        id: draft.id,
        approvalRef: "APR-ISO-B",
      })
    ).rejects.toThrow(/not found|không tồn tại/i);
  });

  it("is idempotent on repeated activation: returns the same ACTIVE record without re-mutating", async () => {
    const ws = await createTestWorkspaceWithMember();

    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Contract Test Idempotent Activation Project",
      lifecycleStage: "P2_SOLUTION_VALIDATION",
    });

    const evidence = await recordEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      sourceType: "customer_interview",
      claim: "Reviewed evidence for idempotent activation contract test",
    });
    const reviewed = await reviewEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: evidence.id,
      action: "approve",
    });

    const draft = await createPilot({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      designPartnerEvidenceRefs: [reviewed.id],
      metricContractArtifactRef: "artifact://ws/metrics/v1",
      instrumentationArtifactRef: "artifact://ws/inst/v1",
      onboardingArtifactRef: "artifact://ws/onb/v1",
      rollbackArtifactRef: "artifact://ws/rb/v1",
      releaseOwnerMemberId: ws.userId,
    });

    await approvePilot({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: draft.id,
      approvalRef: "APR-IDEMPOTENT-1",
    });

    const firstActivation = await activatePilot({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: draft.id,
      approvalRef: "APR-IDEMPOTENT-1",
    });
    expect(firstActivation.status).toBe("ACTIVE");

    // Kích hoạt lại lần thứ hai: dịch vụ (pilot-run.service.ts activatePilot) trả
    // thẳng record hiện có khi status đã là ACTIVE, không throw, không tăng version,
    // không tạo thêm outbox event (không re-mutate).
    const secondActivation = await activatePilot({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: draft.id,
      approvalRef: "APR-IDEMPOTENT-1",
    });
    expect(secondActivation.status).toBe("ACTIVE");
    expect(secondActivation.id).toBe(firstActivation.id);
    expect(secondActivation.version).toBe(firstActivation.version);
    expect(secondActivation.activatedAt).toBe(firstActivation.activatedAt);
  });
});

import { describe, it, expect } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createHypothesis, listHypotheses, createExperiment, createEvidence } from "../handlers/validation.handler";

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  return { workspaceId: user.workspaceId, authorization: `Bearer ${user.accessToken}` };
}

describe("Validation & Evidence Chain Service", () => {
  it("creates a hypothesis and lists it", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Validation Ws Inc");
    const hyp = await createHypothesis({
      workspaceId,
      title: "Pricing Willingness to Pay",
      statement: "SaaS Founders are willing to pay $100/mo for autonomous accounting agent",
      confidenceScore: 0.7,
      authorization,
    });

    expect(hyp.id).toBeDefined();
    expect(hyp.workspaceId).toBe(workspaceId);
    expect(hyp.title).toBe("Pricing Willingness to Pay");
    expect(hyp.status).toBe("TESTING");

    const list = await listHypotheses({ workspaceId, authorization });
    expect(list.hypotheses.some((h) => h.id === hyp.id)).toBe(true);
  });

  it("rejects when caller is not a member of the target workspace", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Owner Validation Ws");
    const outsider = await makeAuthedWorkspace("Outsider Validation Test");
    await expect(
      createHypothesis({
        workspaceId,
        title: "Blocked hypothesis",
        statement: "Should not be created",
        authorization: outsider.authorization,
      })
    ).rejects.toThrow();
  });

  it("creates an experiment and attaches evidence", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Experiment Ws Inc");
    const hyp = await createHypothesis({
      workspaceId,
      title: "Problem Severity Hypothesis",
      statement: "Tax regulation compliance takes > 10 hours per week for SME owners",
      authorization,
    });

    const exp = await createExperiment({
      workspaceId,
      hypothesisId: hyp.id,
      experimentType: "INTERVIEW",
      title: "Conduct 10 Founder Tax Interviews",
      authorization,
    });

    expect(exp.id).toBeDefined();
    expect(exp.hypothesisId).toBe(hyp.id);
    expect(exp.status).toBe("RUNNING");

    const ev = await createEvidence({
      workspaceId,
      experimentId: exp.id,
      evidenceType: "VERBATIM_QUOTE",
      title: "Founder CEO Quote",
      content: "I spend every weekend sorting VAT invoices and TT58 books manually",
      strengthScore: 0.9,
      authorization,
    });

    expect(ev.id).toBeDefined();
    expect(ev.experimentId).toBe(exp.id);
    expect(ev.title).toBe("Founder CEO Quote");
    expect(ev.strengthScore).toBe(0.9);
  });
});

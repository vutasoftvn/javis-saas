import { describe, it, expect } from "vitest";
import { createHypothesis, listHypotheses, createExperiment, createEvidence } from "./validation";

describe("Validation & Evidence Chain Service", () => {
  const workspaceId = 700;

  it("creates a hypothesis and lists it", async () => {
    const hyp = await createHypothesis({
      workspaceId,
      title: "Pricing Willingness to Pay",
      statement: "SaaS Founders are willing to pay $100/mo for autonomous accounting agent",
      confidenceScore: 0.7,
    });

    expect(hyp.id).toBeDefined();
    expect(hyp.workspaceId).toBe(workspaceId);
    expect(hyp.title).toBe("Pricing Willingness to Pay");
    expect(hyp.status).toBe("TESTING");

    const list = await listHypotheses({ workspaceId });
    expect(list.hypotheses.some((h) => h.id === hyp.id)).toBe(true);
  });

  it("creates an experiment and attaches evidence", async () => {
    const hyp = await createHypothesis({
      workspaceId,
      title: "Problem Severity Hypothesis",
      statement: "Tax regulation compliance takes > 10 hours per week for SME owners",
    });

    const exp = await createExperiment({
      workspaceId,
      hypothesisId: hyp.id,
      experimentType: "INTERVIEW",
      title: "Conduct 10 Founder Tax Interviews",
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
    });

    expect(ev.id).toBeDefined();
    expect(ev.experimentId).toBe(exp.id);
    expect(ev.title).toBe("Founder CEO Quote");
    expect(ev.strengthScore).toBe(0.9);
  });
});

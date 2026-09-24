import jwt from "jsonwebtoken";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
  getAiGovernanceSnapshot,
  verifyAiGovernanceSnapshotSignature,
  type AiGovernanceSnapshotResult,
} from "../services/ai-governance-snapshot.service";

const TEST_CONTROL_DELEGATION_SECRET = "test-control-delegation-secret-min-32-chars";

function signControlDelegation(opts: { sub: string; organizationId: string; role?: string }): string {
  return jwt.sign(
    { sub: opts.sub, workspace_id: opts.organizationId, role: opts.role ?? "member" },
    process.env.COSA_CONTROL_DELEGATION_SECRET || TEST_CONTROL_DELEGATION_SECRET,
    { audience: "cosa_control", issuer: "cosa_apps", expiresIn: "10m" }
  );
}

const validRef = { id: "model_policy.default", version: "1.0.0", definitionHash: "a".repeat(64) };
const validEvaluatorRef = { id: "eval.safety_bench", version: "2.1.0", definitionHash: "b".repeat(64) };

function baseParams(overrides: Partial<Parameters<typeof getAiGovernanceSnapshot>[0]> = {}) {
  return {
    organizationId: "ws_1",
    projectId: "proj_1",
    policyRefs: [validRef],
    evaluatorRefs: [validEvaluatorRef],
    ...overrides,
  };
}

describe("getAiGovernanceSnapshot", () => {
  const originalSecret = process.env.COSA_CONTROL_DELEGATION_SECRET;
  const originalSigningSecret = process.env.COSA_AI_GOVERNANCE_SIGNING_SECRET;

  beforeEach(() => {
    process.env.COSA_CONTROL_DELEGATION_SECRET = TEST_CONTROL_DELEGATION_SECRET;
    process.env.COSA_AI_GOVERNANCE_SIGNING_SECRET = "test-ai-governance-signing-secret-min-32-chars";
  });

  afterEach(() => {
    process.env.COSA_CONTROL_DELEGATION_SECRET = originalSecret;
    process.env.COSA_AI_GOVERNANCE_SIGNING_SECRET = originalSigningSecret;
  });

  it("(a) rejects a request lacking valid Control Plane delegation auth", async () => {
    await expect(
      getAiGovernanceSnapshot(baseParams(), undefined)
    ).rejects.toMatchObject({ code: "unauthenticated" });

    await expect(
      getAiGovernanceSnapshot(baseParams(), "Bearer not-a-real-token")
    ).rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("(b) rejects a request for a workspace the delegation token isn't scoped to (foreign)", async () => {
    const delegation = signControlDelegation({ sub: "user_1", organizationId: "ws_other" });
    await expect(
      getAiGovernanceSnapshot(baseParams({ organizationId: "ws_1" }), `Bearer ${delegation}`)
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("(c) rejects a policyRefs/evaluatorRefs entry missing id/version/definitionHash", async () => {
    const delegation = signControlDelegation({ sub: "user_1", organizationId: "ws_1" });

    await expect(
      getAiGovernanceSnapshot(
        baseParams({ policyRefs: [{ id: "", version: "1.0.0", definitionHash: "a".repeat(64) }] }),
        `Bearer ${delegation}`
      )
    ).rejects.toMatchObject({ code: "invalid_argument" });

    await expect(
      getAiGovernanceSnapshot(
        baseParams({ evaluatorRefs: [{ id: "eval.x", version: "", definitionHash: "b".repeat(64) }] }),
        `Bearer ${delegation}`
      )
    ).rejects.toMatchObject({ code: "invalid_argument" });

    await expect(
      getAiGovernanceSnapshot(
        baseParams({ policyRefs: [{ id: "model_policy.default", version: "1.0.0", definitionHash: "" }] }),
        `Bearer ${delegation}`
      )
    ).rejects.toMatchObject({ code: "invalid_argument" });

    await expect(
      getAiGovernanceSnapshot(baseParams({ policyRefs: [] }), `Bearer ${delegation}`)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects empty organizationId/projectId", async () => {
    const delegation = signControlDelegation({ sub: "user_1", organizationId: "" });
    await expect(
      getAiGovernanceSnapshot(baseParams({ organizationId: "", projectId: "proj_1" }), `Bearer ${delegation}`)
    ).rejects.toMatchObject({ code: "invalid_argument" });

    const delegation2 = signControlDelegation({ sub: "user_1", organizationId: "ws_1" });
    await expect(
      getAiGovernanceSnapshot(baseParams({ organizationId: "ws_1", projectId: "" }), `Bearer ${delegation2}`)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("(d) produces a valid signature that a separate verification function can confirm", async () => {
    const delegation = signControlDelegation({ sub: "user_1", organizationId: "ws_1" });
    const snapshot = await getAiGovernanceSnapshot(baseParams(), `Bearer ${delegation}`);

    expect(snapshot.status).toBe("VERIFIED");
    expect(snapshot.signature).toBeTruthy();
    expect(verifyAiGovernanceSnapshotSignature(snapshot)).toBe(true);
  });

  it("(e) signature changes if any bound field changes (tamper-evidence)", async () => {
    const delegation = signControlDelegation({ sub: "user_1", organizationId: "ws_1" });
    const snapshot = await getAiGovernanceSnapshot(baseParams(), `Bearer ${delegation}`);

    const tampered: AiGovernanceSnapshotResult = {
      ...snapshot,
      policy: [{ ...snapshot.policy[0], definitionHash: "c".repeat(64) }],
    };

    expect(verifyAiGovernanceSnapshotSignature(tampered)).toBe(false);

    const tamperedStatus: AiGovernanceSnapshotResult = { ...snapshot, status: "VERIFIED" };
    // Sanity: identical clone still verifies (proves comparison isn't vacuous).
    expect(verifyAiGovernanceSnapshotSignature(tamperedStatus)).toBe(true);
  });

  it("(f) no mutation/write capability exists on this service module", async () => {
    const mod = await import("../services/ai-governance-snapshot.service");
    const exportedNames = Object.keys(mod);
    const forbidden = exportedNames.filter((name) => /update|write|set|upsert|delete|mutate/i.test(name));
    expect(forbidden).toEqual([]);
  });
});

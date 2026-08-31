import { afterEach, describe, expect, it } from "vitest";
import { createE2eSessionApi } from "../handlers/e2e-session.handler";

const originalSeedFlag = process.env.E2E_TEST_SEED_ENABLED;
const originalEnvironment = process.env.ENVIRONMENT;

function restore(name: "E2E_TEST_SEED_ENABLED" | "ENVIRONMENT", value: string | undefined) {
  if (value === undefined) delete process.env[name];
  else process.env[name] = value;
}

afterEach(() => {
  restore("E2E_TEST_SEED_ENABLED", originalSeedFlag);
  restore("ENVIRONMENT", originalEnvironment);
});

describe("identity E2E session endpoint", () => {
  it("fails closed unless the dedicated E2E process enables it", async () => {
    delete process.env.E2E_TEST_SEED_ENABLED;
    await expect(
      createE2eSessionApi({ email: "disabled-e2e-session@example.com", displayName: "Disabled E2E Session" })
    ).rejects.toThrow(/disabled/i);
  });

  it("is unavailable in production even when the E2E flag is set", async () => {
    process.env.E2E_TEST_SEED_ENABLED = "1";
    process.env.ENVIRONMENT = "production";
    await expect(
      createE2eSessionApi({ email: "production-e2e-session@example.com", displayName: "Production E2E Session" })
    ).rejects.toThrow(/never available/i);
  });

  it("creates an authenticated isolated session only when the local E2E flag is set", async () => {
    process.env.E2E_TEST_SEED_ENABLED = "1";
    delete process.env.ENVIRONMENT;
    const session = await createE2eSessionApi({
      email: `enabled-e2e-session-${Date.now()}@example.com`,
      displayName: "Enabled E2E Session",
    });

    expect(session.accessToken).toBeTruthy();
    expect(session.userId).toMatch(/^\d+$/);
    expect(session.workspaceId).toMatch(/^\d+$/);
  });
});

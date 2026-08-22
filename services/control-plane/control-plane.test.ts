import { describe, it, expect } from "vitest";
import { registerPlatform, loginPlatform, getPlatformUserMe, updatePlatformUserMe } from "./auth";
import { createCompany, joinCompany, listMyCompanies, validateMembership } from "./company";
import { verifyPlatformToken } from "./token";

describe("Control Plane Service", () => {
  const testEmail = `founder_${Date.now()}@example.com`;
  let platformToken = "";
  let companyId = "";

  it("registers a platform user with a new company", async () => {
    const res = await registerPlatform({
      email: testEmail,
      password: "password123",
      full_name: "John Doe",
      company_name: "Acme AI Corp",
    });

    expect(res.access_token).toBeDefined();
    expect(res.company_id).toBeDefined();
    platformToken = res.access_token;
    companyId = res.company_id!;

    const payload = verifyPlatformToken(res.access_token);
    expect(payload.aud).toBe("control_plane");
    expect(payload.sub).toBeDefined();
  });

  it("logs in the registered platform user", async () => {
    const loginRes = await loginPlatform({
      username: testEmail,
      password: "password123",
    });

    expect(loginRes.access_token).toBeDefined();
    expect(loginRes.token_type).toBe("bearer");
  });

  it("rejects invalid login password", async () => {
    await expect(
      loginPlatform({
        username: testEmail,
        password: "wrong_password",
      })
    ).rejects.toThrow();
  });

  it("retrieves current platform user profile", async () => {
    const profile = await getPlatformUserMe({
      authorization: `Bearer ${platformToken}`,
    });

    expect(profile.email).toBe(testEmail);
    expect(profile.full_name).toBe("John Doe");
  });

  it("updates platform user profile", async () => {
    const updated = await updatePlatformUserMe(
      {
        full_name: "John Doe Updated",
        phone: `+84912${Math.floor(100000 + Math.random() * 900000)}`,
      },
      {
        authorization: `Bearer ${platformToken}`,
      }
    );

    expect(updated.full_name).toBe("John Doe Updated");
    expect(updated.phone).toBeDefined();
  });

  it("lists companies of the platform user", async () => {
    const res = await listMyCompanies({
      authorization: `Bearer ${platformToken}`,
    });

    expect(res.companies.length).toBeGreaterThanOrEqual(1);
    expect(res.companies[0].company_id).toBe(companyId);
    expect(res.companies[0].role_id).toBe("founder");
  });

  it("creates a second company", async () => {
    const secondComp = await createCompany(
      { name: "Second Venture Inc" },
      { authorization: `Bearer ${platformToken}` }
    );

    expect(secondComp.company_id).toBeDefined();
    expect(secondComp.role_id).toBe("founder");
    expect(secondComp.name).toBe("Second Venture Inc");
  });

  it("joins an existing company for a new user", async () => {
    const newUserRes = await registerPlatform({
      email: `member_${Date.now()}@example.com`,
      password: "password123",
      full_name: "Jane Member",
    });

    const joined = await joinCompany(
      { company_id: companyId },
      { authorization: `Bearer ${newUserRes.access_token}` }
    );

    expect(joined.company_id).toBe(companyId);
    expect(joined.role_id).toBe("user");
  });

  it("validates membership via internal RPC", async () => {
    const validation = await validateMembership({
      platformToken,
      companyId,
    });

    expect(validation.valid).toBe(true);
    expect(validation.roleId).toBe("founder");
    expect(validation.companyName).toBe("Acme AI Corp");
    expect(validation.email).toBe(testEmail);
  });
});

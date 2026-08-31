import { describe, it, expect } from "vitest";
import { registerPlatform, loginPlatform, getMe, updateMe } from "../handlers/auth.handler";
import { createCompanyFor, joinCompanyFor, listMyCompaniesFor, validateMembership } from "../handlers/company.handler";
import { verifyPlatformToken } from "../services/token.service";

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
    expect(res.platform_workspace_id).toBeDefined();
    platformToken = res.access_token;
    companyId = res.platform_workspace_id!;

    const payload = verifyPlatformToken(res.access_token);
    expect(["cosa", "control_plane"]).toContain(payload.aud);
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

  it("retrieves current platform user profile with default member role", async () => {
    const profile = await getMe({ userID: verifyPlatformToken(platformToken).sub });

    expect(profile.email).toBe(testEmail);
    expect(profile.full_name).toBe("John Doe");
    expect(profile.role_id).toBe("member");
    expect(profile.is_platform_admin).toBe(false);
  });

  it("updates platform user profile with social persona fields", async () => {
    const updated = await updateMe(
      { userID: verifyPlatformToken(platformToken).sub },
      {
        full_name: "John Doe Updated",
        phone: `+84912${Math.floor(100000 + Math.random() * 900000)}`,
        headline: "Founder @ Cosa AI",
        bio: "Building next-gen AI workspace",
        role_id: "founder",
      }
    );

    expect(updated.full_name).toBe("John Doe Updated");
    expect(updated.phone).toBeDefined();
    expect(updated.headline).toBe("Founder @ Cosa AI");
    expect(updated.bio).toBe("Building next-gen AI workspace");
    expect(updated.role_id).toBe("founder");
  });

  it("rejects registration with duplicate email", async () => {
    await expect(
      registerPlatform({
        email: testEmail,
        password: "password123",
        full_name: "Duplicate User",
      })
    ).rejects.toThrow();
  });

  it("lists companies of the platform user", async () => {
    const res = await listMyCompaniesFor({ userID: verifyPlatformToken(platformToken).sub });

    expect(res.companies.length).toBeGreaterThanOrEqual(1);
    expect(res.companies[0].company_id).toBe(companyId);
    expect(res.companies[0].role_id).toBe("founder");
  });

  it("creates a second company", async () => {
    const secondComp = await createCompanyFor(
      { userID: verifyPlatformToken(platformToken).sub },
      { name: "Second Venture Inc" }
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

    const joined = await joinCompanyFor(
      { userID: verifyPlatformToken(newUserRes.access_token).sub },
      { company_id: companyId }
    );

    expect(joined.company_id).toBe(companyId);
    expect(joined.role_id).toBe("member");
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

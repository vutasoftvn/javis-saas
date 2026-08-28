import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { resolveCosaDatabaseUrl } from "../storage/client";

describe("resolveCosaDatabaseUrl", () => {
  const originalCosaUrl = process.env.COSA_DATABASE_URL;
  const originalControlPlaneUrl = process.env.CONTROL_PLANE_DATABASE_URL;
  const originalNodeEnv = process.env.NODE_ENV;

  beforeEach(() => {
    delete process.env.COSA_DATABASE_URL;
    delete process.env.CONTROL_PLANE_DATABASE_URL;
  });

  afterEach(() => {
    if (originalCosaUrl !== undefined) {
      process.env.COSA_DATABASE_URL = originalCosaUrl;
    } else {
      delete process.env.COSA_DATABASE_URL;
    }
    if (originalControlPlaneUrl !== undefined) {
      process.env.CONTROL_PLANE_DATABASE_URL = originalControlPlaneUrl;
    } else {
      delete process.env.CONTROL_PLANE_DATABASE_URL;
    }
    if (originalNodeEnv !== undefined) {
      process.env.NODE_ENV = originalNodeEnv;
    } else {
      delete process.env.NODE_ENV;
    }
  });

  it("throws descriptive error when neither COSA_DATABASE_URL nor CONTROL_PLANE_DATABASE_URL is set", () => {
    process.env.NODE_ENV = "development";
    expect(() => resolveCosaDatabaseUrl()).toThrowError(
      /COSA_DATABASE_URL \(hoặc CONTROL_PLANE_DATABASE_URL\) is required/
    );
  });

  it("error message does not contain hardcoded credentials", () => {
    try {
      resolveCosaDatabaseUrl();
      expect.unreachable("should have thrown");
    } catch (err: any) {
      expect(err.message).not.toContain("SecureCentralPass2026");
      expect(err.message).not.toContain("cosa_central_admin");
      expect(err.message).toContain("COSA_DATABASE_URL");
    }
  });

  it("resolves COSA_DATABASE_URL when set", () => {
    process.env.COSA_DATABASE_URL = "postgresql://custom_user:pass@localhost:5432/custom_cosa";
    expect(resolveCosaDatabaseUrl()).toBe("postgresql://custom_user:pass@localhost:5432/custom_cosa");
  });

  it("falls back to CONTROL_PLANE_DATABASE_URL when set", () => {
    process.env.CONTROL_PLANE_DATABASE_URL = "postgresql://cp_user:pass@localhost:5432/cp_cosa";
    expect(resolveCosaDatabaseUrl()).toBe("postgresql://cp_user:pass@localhost:5432/cp_cosa");
  });
});

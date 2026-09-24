import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import jwt from "jsonwebtoken";
import * as coreAccess from "../services/core-access.service";
import { verifyWorkspaceMembership } from "../services/workspace-connector.service";

const SECRET = "test-control-delegation-secret-min-32-chars";
const prev = process.env.COSA_CONTROL_DELEGATION_SECRET;

const sign = (claims: Record<string, unknown>, secret = SECRET) =>
  jwt.sign(claims, secret, { audience: "cosa_control", issuer: "cosa_apps", expiresIn: "10m" });

describe("verifyWorkspaceMembership với control-plane delegation do apps/cosa ký", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    process.env.COSA_CONTROL_DELEGATION_SECRET = SECRET;
  });

  afterAll(() => {
    if (prev === undefined) delete process.env.COSA_CONTROL_DELEGATION_SECRET;
    else process.env.COSA_CONTROL_DELEGATION_SECRET = prev;
  });

  it("tin role trong delegation của đúng workspace, không hỏi core", async () => {
    const authorize = vi.spyOn(coreAccess, "authorizeAndProjectCoreAccess");
    const token = sign({ sub: "42", workspace_id: "100", role: "admin" });

    expect(await verifyWorkspaceMembership("100", `Bearer ${token}`)).toEqual({
      platformCompanyId: null,
      membershipRole: "admin",
    });
    expect(authorize).not.toHaveBeenCalled();
  });

  it("delegation của workspace khác -> permission_denied", async () => {
    const token = sign({ sub: "42", workspace_id: "100", role: "admin" });
    await expect(verifyWorkspaceMembership("999", `Bearer ${token}`)).rejects.toMatchObject({
      code: "permission_denied",
    });
  });

  it("JWT không phải delegation hợp lệ -> unauthenticated", async () => {
    const token = sign({ sub: "42", workspace_id: "100", role: "admin" }, "another-secret-min-32-characters-long!!");
    await expect(verifyWorkspaceMembership("100", `Bearer ${token}`)).rejects.toMatchObject({
      code: "unauthenticated",
    });
    await expect(verifyWorkspaceMembership("100", undefined)).rejects.toMatchObject({ code: "unauthenticated" });
  });
});

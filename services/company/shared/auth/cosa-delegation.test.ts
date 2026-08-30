// services/company/shared/auth/cosa-delegation.test.ts
//
// Task 3 (AI compliance hardening) — verify cơ chế scoped COSA->Company
// delegation mới (mintCompanyDelegation/verifyCosaDelegation/consumeCosaDelegation).
// Trước Task 3 không có gì để test ở đây — "delegation" cũ chỉ re-sign lại
// {sub, aud?, exp} phía apps/cosa, services/company chưa từng verify claim
// có cấu trúc nào. RED ban đầu: cosa-delegation.service.ts chưa tồn tại.
import { eq } from "drizzle-orm";
import jwt from "jsonwebtoken";
import { afterAll, describe, expect, it } from "vitest";
import {
  consumeCosaDelegation,
  mintCompanyDelegation,
  verifyCosaDelegation,
} from "./cosa-delegation.service";
import { db, schema } from "../../identity/models/db";

const { identityCosaDelegationReplays } = schema;

const SECRET = process.env.COSA_COMPANY_DELEGATION_SECRET || "cosa-company-delegation-dev-secret-change-in-prod";

describe("cosa-delegation", () => {
  afterAll(async () => {
    // dọn record test tạo ra để không rò rỉ giữa các lần chạy suite.
    await db.delete(identityCosaDelegationReplays);
  });

  it("verifies a validly-signed delegation with matching scope", () => {
    const token = mintCompanyDelegation({
      sub: "member-1",
      workspace_id: "w1",
      run_id: "r1",
      capability_ids: ["finance.read", "finance.write"],
    });

    const claims = verifyCosaDelegation(token, {
      workspaceId: "w1",
      runId: "r1",
      capabilityId: "finance.write",
    });

    expect(claims.iss).toBe("cosa");
    expect(claims.aud).toBe("company");
    expect(claims.sub).toBe("member-1");
    expect(claims.principal_id).toBe("user:member-1");
    expect(claims.workspace_id).toBe("w1");
    expect(claims.run_id).toBe("r1");
    expect(claims.capability_ids).toEqual(["finance.read", "finance.write"]);
    expect(claims.jti).toBeTruthy();
  });

  it("rejects a valid signature when audience, workspace, run, or capability differs", () => {
    const token = mintCompanyDelegation({
      sub: "member-1",
      workspace_id: "w1",
      run_id: "r1",
      capability_ids: ["finance.read"],
    });

    expect(() =>
      verifyCosaDelegation(token, { workspaceId: "w2", runId: "r1", capabilityId: "finance.read" })
    ).toThrow();
    expect(() =>
      verifyCosaDelegation(token, { workspaceId: "w1", runId: "r2", capabilityId: "finance.read" })
    ).toThrow();
    expect(() =>
      verifyCosaDelegation(token, { workspaceId: "w1", runId: "r1", capabilityId: "finance.write" })
    ).toThrow();
  });

  it("rejects an expired delegation", () => {
    const token = mintCompanyDelegation({
      sub: "member-1",
      workspace_id: "w1",
      run_id: "r1",
      capability_ids: ["finance.read"],
      ttl_seconds: -1,
    });

    expect(() =>
      verifyCosaDelegation(token, { workspaceId: "w1", runId: "r1", capabilityId: "finance.read" })
    ).toThrow();
  });

  it("caps requested TTL at 600 seconds", () => {
    const token = mintCompanyDelegation({
      sub: "member-1",
      workspace_id: "w1",
      run_id: "r1",
      capability_ids: ["finance.read"],
      ttl_seconds: 999999,
    });
    const decoded = jwt.decode(token) as { exp: number; iat?: number };
    const now = Math.floor(Date.now() / 1000);
    expect(decoded.exp - now).toBeLessThanOrEqual(600);
  });

  it("rejects a token altered after signing (tampered capability)", () => {
    const token = mintCompanyDelegation({
      sub: "member-1",
      workspace_id: "w1",
      run_id: "r1",
      capability_ids: ["finance.read"],
    });
    const [header, payload, signature] = token.split(".");
    const decodedPayload = JSON.parse(Buffer.from(payload, "base64url").toString("utf8"));
    decodedPayload.capability_ids = ["finance.read", "finance.write"];
    const tamperedPayload = Buffer.from(JSON.stringify(decodedPayload)).toString("base64url");
    const tampered = `${header}.${tamperedPayload}.${signature}`;

    expect(() =>
      verifyCosaDelegation(tampered, { workspaceId: "w1", runId: "r1", capabilityId: "finance.write" })
    ).toThrow();
  });

  it("rejects a delegation signed with the wrong secret", () => {
    const forged = jwt.sign(
      {
        iss: "cosa",
        aud: "company",
        sub: "member-1",
        principal_id: "user:member-1",
        workspace_id: "w1",
        run_id: "r1",
        capability_ids: ["finance.read"],
        jti: "forged-jti",
      },
      "wrong-secret",
      { expiresIn: 60 }
    );

    expect(() =>
      verifyCosaDelegation(forged, { workspaceId: "w1", runId: "r1", capabilityId: "finance.read" })
    ).toThrow();
  });

  it("rejects a token missing jti", () => {
    const forged = jwt.sign(
      {
        iss: "cosa",
        aud: "company",
        sub: "member-1",
        principal_id: "user:member-1",
        workspace_id: "w1",
        run_id: "r1",
        capability_ids: ["finance.read"],
      },
      SECRET,
      { expiresIn: 60 }
    );

    expect(() =>
      verifyCosaDelegation(forged, { workspaceId: "w1", runId: "r1", capabilityId: "finance.read" })
    ).toThrow();
  });

  it("consumes a delegation exactly once for mutation/external side effects (replay rejected)", async () => {
    const token = mintCompanyDelegation({
      sub: "member-1",
      workspace_id: "w1",
      run_id: "r-replay-1",
      capability_ids: ["finance.write"],
    });
    const claims = verifyCosaDelegation(token, {
      workspaceId: "w1",
      runId: "r-replay-1",
      capabilityId: "finance.write",
    });

    await expect(consumeCosaDelegation(claims, "finance.write")).resolves.not.toThrow();
    await expect(consumeCosaDelegation(claims, "finance.write")).rejects.toThrow();
  });

  it("allows consuming distinct capabilities from the same delegation independently", async () => {
    const token = mintCompanyDelegation({
      sub: "member-1",
      workspace_id: "w1",
      run_id: "r-replay-2",
      capability_ids: ["finance.read", "finance.write"],
    });
    const claims = verifyCosaDelegation(token, {
      workspaceId: "w1",
      runId: "r-replay-2",
      capabilityId: "finance.read",
    });

    await expect(consumeCosaDelegation(claims, "finance.read")).resolves.not.toThrow();
    await expect(consumeCosaDelegation(claims, "finance.write")).resolves.not.toThrow();
  });

  it("persists the real jti (not a composite string) and enforces uniqueness via the composite (jti, capability_id) primary key", async () => {
    const token = mintCompanyDelegation({
      sub: "member-1",
      workspace_id: "w1",
      run_id: "r-replay-3",
      capability_ids: ["finance.read", "finance.write"],
    });
    const claims = verifyCosaDelegation(token, {
      workspaceId: "w1",
      runId: "r-replay-3",
      capabilityId: "finance.read",
    });

    await consumeCosaDelegation(claims, "finance.read");
    await consumeCosaDelegation(claims, "finance.write");

    const rows = await db
      .select()
      .from(identityCosaDelegationReplays)
      .where(eq(identityCosaDelegationReplays.jti, claims.jti));

    // Cùng jti thật (không phải chuỗi tổng hợp "jti:capability") xuất hiện ở
    // đúng 2 hàng — 1 hàng mỗi capability đã consume — chứng minh cột `jti`
    // chứa JWT ID thật và ràng buộc duy nhất nằm ở composite PK (jti,
    // capability_id), không phải ở cách app-layer tự ghép chuỗi.
    expect(rows).toHaveLength(2);
    expect(rows.map((r) => r.capabilityId).sort()).toEqual(["finance.read", "finance.write"]);
    for (const row of rows) {
      expect(row.jti).toBe(claims.jti);
    }

    // Insert trùng đúng (jti, capability_id) phải bị chặn qua ON CONFLICT ở
    // tầng DB (composite PK) — race-safe, không phụ thuộc app-layer kiểm tra
    // trước khi insert.
    const duplicateInsert = await db
      .insert(identityCosaDelegationReplays)
      .values({
        jti: claims.jti,
        capabilityId: "finance.read",
        workspaceId: claims.workspace_id,
        runId: claims.run_id,
      })
      .onConflictDoNothing({
        target: [identityCosaDelegationReplays.jti, identityCosaDelegationReplays.capabilityId],
      })
      .returning({ jti: identityCosaDelegationReplays.jti });
    expect(duplicateInsert).toHaveLength(0);

    // Insert cùng jti nhưng capability_id KHÁC (chưa từng consume) phải OK —
    // đúng ngữ nghĩa composite PK, không phải PK đơn cột jti.
    const newCapabilityInsert = await db
      .insert(identityCosaDelegationReplays)
      .values({
        jti: claims.jti,
        capabilityId: "finance.admin",
        workspaceId: claims.workspace_id,
        runId: claims.run_id,
      })
      .onConflictDoNothing({
        target: [identityCosaDelegationReplays.jti, identityCosaDelegationReplays.capabilityId],
      })
      .returning({ jti: identityCosaDelegationReplays.jti });
    expect(newCapabilityInsert).toHaveLength(1);
  });
});

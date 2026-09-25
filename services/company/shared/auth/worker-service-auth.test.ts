import { describe, it, expect, beforeEach, afterEach } from "vitest";
import jwt from "jsonwebtoken";
import {
  requireWorkerServiceAuth,
  setWorkerServiceSecretForTesting,
  type WorkerServiceClaims,
} from "./worker-service-auth";

const TEST_SECRET = "test-worker-jwt-secret-min-32-chars-long-fixture";

describe("worker-service-auth", () => {
  const originalEnv = { ...process.env };

  beforeEach(() => {
    process.env = { ...originalEnv };
    setWorkerServiceSecretForTesting(null);
  });

  afterEach(() => {
    process.env = { ...originalEnv };
    setWorkerServiceSecretForTesting(null);
  });

  it("fails closed when secret is missing in production", async () => {
    process.env.ENVIRONMENT = "production";
    delete process.env.WORKER_SERVICE_JWT_SECRET;
    delete process.env.NODE_ENV;

    await expect(() => requireWorkerServiceAuth({ authorization: "Bearer anything" }))
      .rejects.toMatchObject({ code: "internal" });
  });

  it("fails closed when secret is shorter than 32 chars in staging/production", async () => {
    process.env.ENVIRONMENT = "production";
    process.env.WORKER_SERVICE_JWT_SECRET = "short-secret";

    await expect(() => requireWorkerServiceAuth({ authorization: "Bearer anything" }))
      .rejects.toMatchObject({ code: "internal" });
  });

  it("rejects static dev-worker-service-token", async () => {
    process.env.ENVIRONMENT = "development";
    process.env.WORKER_SERVICE_JWT_SECRET = TEST_SECRET;

    await expect(() => requireWorkerServiceAuth({ serviceToken: "dev-worker-service-token" }))
      .rejects.toMatchObject({ code: "unauthenticated" });

    await expect(() => requireWorkerServiceAuth({ authorization: "Bearer dev-worker-service-token" }))
      .rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("rejects token with wrong issuer (iss)", async () => {
    setWorkerServiceSecretForTesting(TEST_SECRET);
    const token = jwt.sign(
      { role: "worker_service", jti: "test-jti-1", sub: "worker-1" },
      TEST_SECRET,
      { issuer: "wrong-issuer", audience: "company-internal", expiresIn: "5m" }
    );

    await expect(() => requireWorkerServiceAuth({ authorization: `Bearer ${token}` }))
      .rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("rejects token with wrong audience (aud)", async () => {
    setWorkerServiceSecretForTesting(TEST_SECRET);
    const token = jwt.sign(
      { role: "worker_service", jti: "test-jti-1", sub: "worker-1" },
      TEST_SECRET,
      { issuer: "apps-cosa", audience: "wrong-aud", expiresIn: "5m" }
    );

    await expect(() => requireWorkerServiceAuth({ authorization: `Bearer ${token}` }))
      .rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("rejects expired token", async () => {
    setWorkerServiceSecretForTesting(TEST_SECRET);
    const token = jwt.sign(
      { role: "worker_service", jti: "test-jti-1", sub: "worker-1" },
      TEST_SECRET,
      { issuer: "apps-cosa", audience: "company-internal", expiresIn: "-1s" }
    );

    await expect(() => requireWorkerServiceAuth({ authorization: `Bearer ${token}` }))
      .rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("rejects token missing required claims (role, sub, jti)", async () => {
    setWorkerServiceSecretForTesting(TEST_SECRET);
    // Missing role
    const tokenNoRole = jwt.sign(
      { jti: "test-jti-1", sub: "worker-1" },
      TEST_SECRET,
      { issuer: "apps-cosa", audience: "company-internal", expiresIn: "5m" }
    );
    await expect(() => requireWorkerServiceAuth({ authorization: `Bearer ${tokenNoRole}` }))
      .rejects.toMatchObject({ code: "unauthenticated" });

    // Missing sub
    const tokenNoSub = jwt.sign(
      { role: "worker_service", jti: "test-jti-1" },
      TEST_SECRET,
      { issuer: "apps-cosa", audience: "company-internal", expiresIn: "5m" }
    );
    await expect(() => requireWorkerServiceAuth({ authorization: `Bearer ${tokenNoSub}` }))
      .rejects.toMatchObject({ code: "unauthenticated" });

    // Missing jti
    const tokenNoJti = jwt.sign(
      { role: "worker_service", sub: "worker-1" },
      TEST_SECRET,
      { issuer: "apps-cosa", audience: "company-internal", expiresIn: "5m" }
    );
    await expect(() => requireWorkerServiceAuth({ authorization: `Bearer ${tokenNoJti}` }))
      .rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("accepts valid short-lived token via Authorization header or X-Service-Token", async () => {
    setWorkerServiceSecretForTesting(TEST_SECRET);
    const token = jwt.sign(
      { role: "worker_service", jti: "unique-jti-123", sub: "worker-agent-42" },
      TEST_SECRET,
      { issuer: "apps-cosa", audience: "company-internal", expiresIn: "60s" }
    );

    const claimsFromAuth = await requireWorkerServiceAuth({ authorization: `Bearer ${token}` });
    expect(claimsFromAuth).toMatchObject({
      iss: "apps-cosa",
      aud: "company-internal",
      sub: "worker-agent-42",
      role: "worker_service",
      jti: "unique-jti-123",
    });
    expect(claimsFromAuth.exp).toBeGreaterThan(Math.floor(Date.now() / 1000));

    const claimsFromHeader = await requireWorkerServiceAuth({ serviceToken: token });
    expect(claimsFromHeader.sub).toBe("worker-agent-42");

    const claimsFromXHeader = await requireWorkerServiceAuth({ "x-service-token": token });
    expect(claimsFromXHeader.sub).toBe("worker-agent-42");
  });

  it("rejects when no credentials are provided", async () => {
    setWorkerServiceSecretForTesting(TEST_SECRET);
    await expect(() => requireWorkerServiceAuth({}))
      .rejects.toMatchObject({ code: "unauthenticated" });
  });
});

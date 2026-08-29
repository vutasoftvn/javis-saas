import { afterEach, describe, expect, it } from "vitest";
import {
  requireCosaInternalUrl,
  requireCosaServiceToken,
  requireLocalServiceSecret,
} from "../service-identity";

// Lưu/khôi phục các biến môi trường mà test này chạm vào — vitest chạy dưới
// NODE_ENV=test (non-strict), nên chỉ set "production" trong phạm vi từng case.
const KEYS = ["NODE_ENV", "ENVIRONMENT", "APP_ENV", "COSA_LOCAL_SERVICE_SECRET", "COSA_SERVICE_TOKEN", "COSA_INTERNAL_URL"] as const;
const saved: Record<string, string | undefined> = {};

function restore(): void {
  for (const k of KEYS) {
    if (saved[k] === undefined) delete process.env[k];
    else process.env[k] = saved[k];
  }
}

afterEach(restore);

describe("service-identity — non-strict env", () => {
  it("returns dev defaults and never throws when unset", () => {
    for (const k of KEYS) saved[k] = process.env[k];
    delete process.env.ENVIRONMENT;
    delete process.env.APP_ENV;
    process.env.NODE_ENV = "test";
    delete process.env.COSA_LOCAL_SERVICE_SECRET;
    delete process.env.COSA_SERVICE_TOKEN;
    delete process.env.COSA_INTERNAL_URL;

    expect(requireLocalServiceSecret()).toBe("dev-secret");
    expect(requireCosaServiceToken()).toBe("local-dev-service-token");
    expect(requireCosaInternalUrl()).toBe("http://127.0.0.1:8000");
  });

  it("returns the provided value when set in non-strict env", () => {
    for (const k of KEYS) saved[k] = process.env[k];
    process.env.NODE_ENV = "test";
    process.env.COSA_LOCAL_SERVICE_SECRET = "short";
    expect(requireLocalServiceSecret()).toBe("short");
  });
});

describe("service-identity — strict env (production)", () => {
  it("throws when the secret is unset", () => {
    for (const k of KEYS) saved[k] = process.env[k];
    process.env.NODE_ENV = "production";
    delete process.env.COSA_LOCAL_SERVICE_SECRET;
    expect(() => requireLocalServiceSecret()).toThrow(/development value/i);
  });

  it("throws when the token is a dev sentinel", () => {
    for (const k of KEYS) saved[k] = process.env[k];
    process.env.NODE_ENV = "production";
    process.env.COSA_SERVICE_TOKEN = "local-dev-service-token";
    expect(() => requireCosaServiceToken()).toThrow(/development value/i);
  });

  it("throws when the secret is shorter than 32 chars", () => {
    for (const k of KEYS) saved[k] = process.env[k];
    process.env.NODE_ENV = "production";
    process.env.COSA_LOCAL_SERVICE_SECRET = "x".repeat(20);
    expect(() => requireLocalServiceSecret()).toThrow(/32 characters/i);
  });

  it("returns a 40-char secret unchanged", () => {
    for (const k of KEYS) saved[k] = process.env[k];
    process.env.NODE_ENV = "production";
    const strong = "a".repeat(40);
    process.env.COSA_LOCAL_SERVICE_SECRET = strong;
    expect(requireLocalServiceSecret()).toBe(strong);
  });

  it("rejects a loopback COSA_INTERNAL_URL and accepts an internal DNS name", () => {
    for (const k of KEYS) saved[k] = process.env[k];
    process.env.NODE_ENV = "production";
    process.env.COSA_INTERNAL_URL = "http://127.0.0.1:8000";
    expect(() => requireCosaInternalUrl()).toThrow(/loopback/i);
    process.env.COSA_INTERNAL_URL = "http://cosa-api.internal:8000";
    expect(requireCosaInternalUrl()).toBe("http://cosa-api.internal:8000");
  });

  it("throws when COSA_INTERNAL_URL is unset in strict env", () => {
    for (const k of KEYS) saved[k] = process.env[k];
    process.env.NODE_ENV = "production";
    delete process.env.COSA_INTERNAL_URL;
    expect(() => requireCosaInternalUrl()).toThrow(/required/i);
  });
});

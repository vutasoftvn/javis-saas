import { describe, it, expect, afterEach } from "vitest";
import { getPlatformJwtSecret, getPlatformUrl } from "../services/platform.client";

describe("platform.client configuration errors", () => {
  const prevSecret = process.env.PLATFORM_JWT_SECRET;
  const prevUrl = process.env.PLATFORM_API_BASE_URL;
  const prevEnv = process.env.NODE_ENV;

  afterEach(() => {
    if (prevSecret === undefined) delete process.env.PLATFORM_JWT_SECRET;
    else process.env.PLATFORM_JWT_SECRET = prevSecret;
    if (prevUrl === undefined) delete process.env.PLATFORM_API_BASE_URL;
    else process.env.PLATFORM_API_BASE_URL = prevUrl;
    if (prevEnv === undefined) delete process.env.NODE_ENV;
    else process.env.NODE_ENV = prevEnv;
  });

  it("throws APIError.internal when PLATFORM_JWT_SECRET too short in prod", () => {
    process.env.NODE_ENV = "production";
    process.env.PLATFORM_JWT_SECRET = "short";

    expect(() => getPlatformJwtSecret()).toThrow(
      expect.objectContaining({ code: "internal" })
    );
  });

  it("throws APIError.internal when PLATFORM_API_BASE_URL uses dev default in prod", () => {
    process.env.NODE_ENV = "production";
    process.env.PLATFORM_API_BASE_URL = "http://127.0.0.1:4001";

    expect(() => getPlatformUrl()).toThrow(
      expect.objectContaining({ code: "internal" })
    );
  });
});

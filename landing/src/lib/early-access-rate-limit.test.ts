import { afterEach, describe, expect, it, vi } from "vitest";
import { createRateLimiter, InMemoryRateLimiter, PostgresRateLimiter } from "./early-access-rate-limit";

describe("createRateLimiter", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("fails loudly instead of silently using in-memory rate limiting when production has no DATABASE_URL", () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("DATABASE_URL", "");
    expect(() => createRateLimiter()).toThrow(/DATABASE_URL/);
  });

  it("uses the durable Postgres adapter in production when DATABASE_URL is set", () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("DATABASE_URL", "postgres://user:pass@localhost:5432/early_access");
    expect(createRateLimiter()).toBeInstanceOf(PostgresRateLimiter);
  });

  it("falls back to the in-memory adapter outside production without DATABASE_URL (test/dev only)", () => {
    vi.stubEnv("NODE_ENV", "test");
    vi.stubEnv("DATABASE_URL", "");
    expect(createRateLimiter()).toBeInstanceOf(InMemoryRateLimiter);
  });
});

describe("InMemoryRateLimiter", () => {
  it("allows up to the limit within a window, then denies with a positive retryAfterSeconds", async () => {
    const limiter = new InMemoryRateLimiter();
    const key = "ip:203.0.113.10";
    expect((await limiter.consume(key, 3, 3600)).allowed).toBe(true);
    expect((await limiter.consume(key, 3, 3600)).allowed).toBe(true);
    expect((await limiter.consume(key, 3, 3600)).allowed).toBe(true);
    const fourth = await limiter.consume(key, 3, 3600);
    expect(fourth.allowed).toBe(false);
    expect(fourth.retryAfterSeconds).toBeGreaterThan(0);
  });

  it("tracks independent windows per key", async () => {
    const limiter = new InMemoryRateLimiter();
    expect((await limiter.consume("ip:a", 1, 3600)).allowed).toBe(true);
    expect((await limiter.consume("ip:a", 1, 3600)).allowed).toBe(false);
    expect((await limiter.consume("ip:b", 1, 3600)).allowed).toBe(true);
  });
});

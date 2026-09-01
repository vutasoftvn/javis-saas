import { afterEach, describe, expect, it, vi } from "vitest";
import { createEarlyAccessStore, InMemoryEarlyAccessStore, PostgresEarlyAccessStore } from "./early-access-store";

describe("createEarlyAccessStore", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("fails loudly instead of silently using an in-memory store when production has no DATABASE_URL", () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("DATABASE_URL", "");
    expect(() => createEarlyAccessStore()).toThrow(/DATABASE_URL/);
  });

  it("uses the durable Postgres adapter in production when DATABASE_URL is set", () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("DATABASE_URL", "postgres://user:pass@localhost:5432/early_access");
    expect(createEarlyAccessStore()).toBeInstanceOf(PostgresEarlyAccessStore);
  });

  it("falls back to the in-memory adapter outside production without DATABASE_URL (test/dev only)", () => {
    vi.stubEnv("NODE_ENV", "test");
    vi.stubEnv("DATABASE_URL", "");
    expect(createEarlyAccessStore()).toBeInstanceOf(InMemoryEarlyAccessStore);
  });
});

describe("InMemoryEarlyAccessStore", () => {
  it("dedups by normalized email and only marks queued once given a provider message id", async () => {
    const store = new InMemoryEarlyAccessStore();
    const created = await store.create({
      fullName: "Ada Lovelace",
      email: "ada@example.com",
      phone: "0912345678",
      company: "Analytical Engines",
      priorityInterest: "Trọn bộ Hệ điều hành COSA OS",
      accessCode: "ref-code-1",
      emailDeliveryStatus: "pending",
    });

    expect(await store.findByEmail("ada@example.com")).toEqual(created);

    await store.markEmailQueued(created.id, "resend-msg-1");
    const updated = await store.findByEmail("ada@example.com");
    expect(updated?.emailDeliveryStatus).toBe("queued");
    expect(updated?.emailProviderMessageId).toBe("resend-msg-1");
  });
});

import { afterEach, describe, expect, it, vi } from "vitest";
import { createEarlyAccessStore, InMemoryEarlyAccessStore, PostgresEarlyAccessStore } from "./early-access-store";

describe("createEarlyAccessStore", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("fails loudly instead of silently using an in-memory store when production has no DATABASE_URL", () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("DATABASE_URL", "");
    vi.stubEnv("ALLOW_IN_MEMORY_FALLBACK", "false");
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

  it("claimEmailAttempt only succeeds once per pending/failed record (atomic claim semantics)", async () => {
    const store = new InMemoryEarlyAccessStore();
    const created = await store.create({
      fullName: "Grace Hopper",
      email: "grace@example.com",
      phone: "0912345679",
      company: "COBOL Inc",
      priorityInterest: "Trọn bộ Hệ điều hành COSA OS",
      accessCode: "ref-code-2",
      emailDeliveryStatus: "pending",
    });

    expect(await store.claimEmailAttempt(created.id)).toBe(true);
    // Lần claim thứ hai trên cùng bản ghi phải thất bại vì trạng thái đã
    // chuyển sang "sending" — đây chính là cơ chế chống gửi email trùng khi
    // có 2 request đồng thời cho cùng một bản ghi pending/failed.
    expect(await store.claimEmailAttempt(created.id)).toBe(false);

    await store.markEmailFailed(created.id);
    expect((await store.findByEmail("grace@example.com"))?.emailDeliveryStatus).toBe("failed");
    // Sau khi failed, claim lại được phép (retry tiếp theo).
    expect(await store.claimEmailAttempt(created.id)).toBe(true);
  });

  it("markEmailSimulated transitions a record to simulated", async () => {
    const store = new InMemoryEarlyAccessStore();
    const created = await store.create({
      fullName: "Ada Lovelace",
      email: "ada2@example.com",
      phone: "0912345678",
      company: "Analytical Engines",
      priorityInterest: "Trọn bộ Hệ điều hành COSA OS",
      accessCode: "ref-code-3",
      emailDeliveryStatus: "pending",
    });

    await store.markEmailSimulated(created.id);
    expect((await store.findByEmail("ada2@example.com"))?.emailDeliveryStatus).toBe("simulated");
  });

  it("updates persona discovery data successfully", async () => {
    const store = new InMemoryEarlyAccessStore();
    await store.create({
      fullName: "Student B",
      email: "student@school.edu.vn",
      phone: "0912345678",
      company: "School Project",
      userSegment: "Học sinh, Sinh viên / Nghiên cứu học tập",
      projectName: "AI Thesis",
      priorityInterest: "Gói Free - 1 Workspace & 1 Project",
      accessCode: "ref-code-4",
      emailDeliveryStatus: "pending",
    });

    const ok = await store.updatePersonaDiscovery("student@school.edu.vn", {
      firstProjectGoal: "Nghiên cứu đồ án AI",
      aiAutonomyLevel: "L1",
    });
    expect(ok).toBe(true);

    const record = await store.findByEmail("student@school.edu.vn");
    expect(record?.personaData).toMatchObject({
      firstProjectGoal: "Nghiên cứu đồ án AI",
      aiAutonomyLevel: "L1",
    });
  });
});


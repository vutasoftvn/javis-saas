import type { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/resend", () => ({
  sendEarlyAccessEmails: vi.fn(),
  isEarlyAccessEmailSimulated: vi.fn(() => false),
}));
vi.mock("@/lib/early-access-store", () => ({
  earlyAccessStore: {
    findByEmail: vi.fn(),
    create: vi.fn(),
    markEmailQueued: vi.fn(),
    markEmailFailed: vi.fn(),
    markEmailSimulated: vi.fn(),
    claimEmailAttempt: vi.fn(),
  },
}));
vi.mock("@/lib/early-access-rate-limit", () => ({
  earlyAccessRateLimiter: { consume: vi.fn() },
}));

import { POST } from "./route";
import { isEarlyAccessEmailSimulated, sendEarlyAccessEmails } from "@/lib/resend";
import { earlyAccessStore as store } from "@/lib/early-access-store";
import { earlyAccessRateLimiter as limiter } from "@/lib/early-access-rate-limit";

const validBody = {
  fullName: "Ada Lovelace",
  email: "ada@example.com",
  phone: "0912345678",
  company: "Analytical Engines",
};

const post = (body: string, headers: Record<string, string> = {}) =>
  POST(
    new Request("http://localhost/api/early-access", {
      method: "POST",
      headers: { "content-type": "application/json", ...headers },
      body,
    }) as NextRequest
  );

const existingRegistration = {
  id: "existing-1",
  email: "ada@example.com",
  fullName: "Ada Lovelace",
  phone: "0912345678",
  company: "Analytical Engines",
  priorityInterest: "Trọn bộ Hệ điều hành COSA OS",
  accessCode: "existing-access-code",
  emailDeliveryStatus: "queued" as const,
  registeredAt: new Date().toISOString(),
};

describe("POST /api/early-access", () => {
  beforeEach(() => {
    vi.mocked(limiter.consume).mockReset().mockResolvedValue({ allowed: true, retryAfterSeconds: 0 });
    vi.mocked(store.findByEmail).mockReset().mockResolvedValue(null);
    vi.mocked(store.create)
      .mockReset()
      .mockImplementation(async (input) => ({
        ...input,
        id: "new-registration-1",
        registeredAt: new Date().toISOString(),
      }));
    vi.mocked(store.markEmailQueued).mockReset().mockResolvedValue(undefined);
    vi.mocked(store.markEmailFailed).mockReset().mockResolvedValue(undefined);
    vi.mocked(store.markEmailSimulated).mockReset().mockResolvedValue(undefined);
    vi.mocked(store.claimEmailAttempt).mockReset().mockResolvedValue(true);
    vi.mocked(sendEarlyAccessEmails).mockReset();
    vi.mocked(isEarlyAccessEmailSimulated).mockReset().mockReturnValue(false);
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.useRealTimers();
  });

  it("returns 400 for invalid JSON", async () => {
    expect((await post("{")).status).toBe(400);
  });

  it("returns 413 for an oversized body", async () => {
    expect((await post(JSON.stringify({ ...validBody, note: "x".repeat(17_000) }))).status).toBe(413);
  });

  it("returns 502 when the real user-email delivery fails, and marks the registration failed", async () => {
    vi.mocked(sendEarlyAccessEmails).mockResolvedValueOnce({
      userEmailSent: false,
      adminEmailSent: false,
      simulated: false,
      error: "provider down",
    });
    const response = await post(JSON.stringify(validBody));
    expect(response.status).toBe(502);
    expect(store.markEmailFailed).toHaveBeenCalledWith("new-registration-1");
  });

  it("returns 200 only after real user-email delivery", async () => {
    vi.mocked(sendEarlyAccessEmails).mockResolvedValueOnce({
      userEmailSent: true,
      adminEmailSent: true,
      providerMessageId: "resend-msg-1",
    });
    const response = await post(JSON.stringify(validBody));
    expect(response.status).toBe(200);
    expect(store.markEmailQueued).toHaveBeenCalledWith("new-registration-1", "resend-msg-1");
  });

  it("persists before attempting to send email, and only marks queued after a provider message id", async () => {
    const callOrder: string[] = [];
    vi.mocked(store.create).mockImplementationOnce(async (input) => {
      callOrder.push("create");
      return { ...input, id: "ordered-1", registeredAt: new Date().toISOString() };
    });
    vi.mocked(sendEarlyAccessEmails).mockImplementationOnce(async () => {
      callOrder.push("send");
      return { userEmailSent: true, adminEmailSent: true, providerMessageId: "msg-ordered" };
    });
    vi.mocked(store.markEmailQueued).mockImplementationOnce(async () => {
      callOrder.push("markQueued");
    });

    await post(JSON.stringify(validBody));

    expect(callOrder).toEqual(["create", "send", "markQueued"]);
  });

  it("does not report success: true on the simulated (no real email sent) path", async () => {
    vi.mocked(isEarlyAccessEmailSimulated).mockReturnValue(true);
    vi.mocked(sendEarlyAccessEmails).mockResolvedValueOnce({
      userEmailSent: false,
      adminEmailSent: false,
      simulated: true,
    });
    const res = await post(JSON.stringify(validBody));
    const json = await res.json();
    expect(json.simulated).toBe(true);
    expect(json.success).not.toBe(true);
    expect(store.create).toHaveBeenCalledWith(expect.objectContaining({ emailDeliveryStatus: "simulated" }));
    expect(store.markEmailQueued).not.toHaveBeenCalled();
  });

  it("returns 429 before email when IP quota is exhausted", async () => {
    vi.mocked(limiter.consume).mockResolvedValueOnce({ allowed: false, retryAfterSeconds: 3600 });
    const response = await post(JSON.stringify(validBody), { "x-forwarded-for": "203.0.113.10" });
    expect(response.status).toBe(429);
    expect(response.headers.get("Retry-After")).toBe("3600");
    expect(sendEarlyAccessEmails).not.toHaveBeenCalled();
    expect(store.create).not.toHaveBeenCalled();
  });

  it("is idempotent for an email already queued", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.mocked(store.findByEmail).mockResolvedValue(existingRegistration);
    const responsePromise = post(JSON.stringify(validBody));
    await vi.advanceTimersByTimeAsync(10_000);
    const response = await responsePromise;
    expect(response.status).toBe(200);
    expect(sendEarlyAccessEmails).not.toHaveBeenCalled();
    expect(store.create).not.toHaveBeenCalled();
    const json = await response.json();
    expect(json.success).toBe(true);
    expect(json.accessCode).toBe(existingRegistration.accessCode);
  });

  it("pads the response latency for an already-queued duplicate so it isn't trivially faster than a fresh registration", async () => {
    // Bằng chứng cho fix Important #2: nhánh duplicate (queued/simulated)
    // KHÔNG được resolve ngay lập tức — nếu không có độ trễ giả lập, promise
    // sẽ resolve trước khi advance timer, và assertion `resolved === false`
    // dưới đây sẽ fail.
    vi.useFakeTimers();
    vi.mocked(store.findByEmail).mockResolvedValue(existingRegistration);

    let resolved = false;
    const responsePromise = post(JSON.stringify(validBody)).then((response) => {
      resolved = true;
      return response;
    });

    await vi.advanceTimersByTimeAsync(0);
    expect(resolved).toBe(false);

    await vi.advanceTimersByTimeAsync(10_000);
    const response = await responsePromise;
    expect(resolved).toBe(true);
    expect(response.status).toBe(200);
  });

  it("does NOT report success for a duplicate whose earlier email delivery never completed (status pending), and retries delivery instead", async () => {
    vi.mocked(store.findByEmail).mockResolvedValue({ ...existingRegistration, emailDeliveryStatus: "pending" });
    vi.mocked(sendEarlyAccessEmails).mockResolvedValueOnce({
      userEmailSent: true,
      adminEmailSent: true,
      providerMessageId: "resend-msg-retry",
    });

    const response = await post(JSON.stringify(validBody));

    expect(sendEarlyAccessEmails).toHaveBeenCalledTimes(1);
    expect(store.create).not.toHaveBeenCalled();
    expect(store.markEmailQueued).toHaveBeenCalledWith(existingRegistration.id, "resend-msg-retry");
    expect(response.status).toBe(200);
    const json = await response.json();
    expect(json.success).toBe(true);
  });

  it("returns 502 (not success) when the retried delivery for a pending duplicate also fails", async () => {
    vi.mocked(store.findByEmail).mockResolvedValue({ ...existingRegistration, emailDeliveryStatus: "pending" });
    vi.mocked(sendEarlyAccessEmails).mockResolvedValueOnce({
      userEmailSent: false,
      adminEmailSent: false,
      error: "still down",
    });

    const response = await post(JSON.stringify(validBody));

    expect(response.status).toBe(502);
    const json = await response.json();
    expect(json.success).not.toBe(true);
    expect(store.markEmailFailed).toHaveBeenCalledWith(existingRegistration.id);
  });

  it("does NOT report success for a duplicate with a previously failed delivery until a retry actually succeeds", async () => {
    vi.mocked(store.findByEmail).mockResolvedValue({ ...existingRegistration, emailDeliveryStatus: "failed" });
    vi.mocked(sendEarlyAccessEmails).mockResolvedValueOnce({
      userEmailSent: true,
      adminEmailSent: true,
      providerMessageId: "resend-msg-retry-2",
    });

    const response = await post(JSON.stringify(validBody));

    expect(sendEarlyAccessEmails).toHaveBeenCalledTimes(1);
    expect(response.status).toBe(200);
    const json = await response.json();
    expect(json.success).toBe(true);
  });

  it("marks a retried pending duplicate as simulated when the environment flips to simulated mid-retry", async () => {
    vi.mocked(store.findByEmail).mockResolvedValue({ ...existingRegistration, emailDeliveryStatus: "pending" });
    vi.mocked(sendEarlyAccessEmails).mockResolvedValueOnce({
      userEmailSent: false,
      adminEmailSent: false,
      simulated: true,
    });

    const response = await post(JSON.stringify(validBody));

    expect(store.markEmailSimulated).toHaveBeenCalledWith(existingRegistration.id);
    expect(store.markEmailQueued).not.toHaveBeenCalled();
    expect(store.markEmailFailed).not.toHaveBeenCalled();
    const json = await response.json();
    expect(json.simulated).toBe(true);
    expect(json.success).not.toBe(true);
  });

  it("does not send a second email when the retry claim fails (concurrent request already claimed it)", async () => {
    vi.mocked(store.findByEmail).mockResolvedValue({ ...existingRegistration, emailDeliveryStatus: "pending" });
    vi.mocked(store.claimEmailAttempt).mockResolvedValueOnce(false);

    const response = await post(JSON.stringify(validBody));

    expect(response.status).toBe(202);
    expect(sendEarlyAccessEmails).not.toHaveBeenCalled();
    const json = await response.json();
    expect(json.success).not.toBe(true);
  });

  it("sends at most one confirmation email when two requests race for the same pending duplicate", async () => {
    // Bằng chứng cho fix của race condition: mô phỏng claimEmailAttempt như
    // một Postgres UPDATE ... WHERE status IN (...) thật — chỉ lệnh gọi ĐẦU
    // TIÊN thành công (true), mọi lệnh gọi sau đó cho cùng id thất bại
    // (false), giống hệt ngữ nghĩa "chỉ 1 dòng bị UPDATE" của SQL nguyên tử.
    let claimed = false;
    vi.mocked(store.claimEmailAttempt).mockImplementation(async () => {
      if (claimed) return false;
      claimed = true;
      return true;
    });
    vi.mocked(store.findByEmail).mockResolvedValue({ ...existingRegistration, emailDeliveryStatus: "pending" });
    vi.mocked(sendEarlyAccessEmails).mockResolvedValue({
      userEmailSent: true,
      adminEmailSent: true,
      providerMessageId: "resend-msg-race",
    });

    const [firstResponse, secondResponse] = await Promise.all([
      post(JSON.stringify(validBody)),
      post(JSON.stringify(validBody)),
    ]);

    expect(sendEarlyAccessEmails).toHaveBeenCalledTimes(1);
    const statuses = [firstResponse.status, secondResponse.status].sort();
    // Một request thắng (200, gửi thật), request còn lại thấy claim thất bại
    // (202, không gửi gì thêm) — tuyệt đối không có trường hợp cả hai đều
    // gọi sendEarlyAccessEmails.
    expect(statuses).toEqual([200, 202]);
  });

  it("rejects submissions with a filled honeypot field without persisting or emailing", async () => {
    const response = await post(JSON.stringify({ ...validBody, website: "http://spambot.example" }));
    expect(response.status).toBe(200);
    expect(store.create).not.toHaveBeenCalled();
    expect(sendEarlyAccessEmails).not.toHaveBeenCalled();
  });

  it("rejects an invalid CAPTCHA in production before persistence/email", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("TURNSTILE_SECRET_KEY", "test-secret");
    const originalFetch = global.fetch;
    global.fetch = vi.fn().mockResolvedValue({
      json: async () => ({ success: false }),
    }) as unknown as typeof fetch;

    try {
      const response = await post(JSON.stringify({ ...validBody, turnstileToken: "bad-token" }));
      expect(response.status).toBe(400);
      expect(store.create).not.toHaveBeenCalled();
      expect(sendEarlyAccessEmails).not.toHaveBeenCalled();
    } finally {
      global.fetch = originalFetch;
    }
  });
});

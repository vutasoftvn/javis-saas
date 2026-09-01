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
    vi.mocked(sendEarlyAccessEmails).mockReset();
    vi.mocked(isEarlyAccessEmailSimulated).mockReset().mockReturnValue(false);
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("returns 400 for invalid JSON", async () => {
    expect((await post("{")).status).toBe(400);
  });

  it("returns 413 for an oversized body", async () => {
    expect((await post(JSON.stringify({ ...validBody, note: "x".repeat(17_000) }))).status).toBe(413);
  });

  it("returns 502 when the real user-email delivery fails", async () => {
    vi.mocked(sendEarlyAccessEmails).mockResolvedValueOnce({
      userEmailSent: false,
      adminEmailSent: false,
      simulated: false,
      error: "provider down",
    });
    expect((await post(JSON.stringify(validBody))).status).toBe(502);
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
    vi.mocked(store.findByEmail).mockResolvedValue(existingRegistration);
    const response = await post(JSON.stringify(validBody));
    expect(response.status).toBe(200);
    expect(sendEarlyAccessEmails).not.toHaveBeenCalled();
    expect(store.create).not.toHaveBeenCalled();
    const json = await response.json();
    expect(json.success).toBe(true);
    expect(json.accessCode).toBe(existingRegistration.accessCode);
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

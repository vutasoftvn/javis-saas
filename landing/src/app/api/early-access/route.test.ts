import type { NextRequest } from "next/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/resend", () => ({ sendEarlyAccessEmails: vi.fn() }));
import { POST } from "./route";
import { sendEarlyAccessEmails } from "@/lib/resend";

const validBody = { fullName: "Ada Lovelace", email: "ada@example.com", phone: "0912345678", company: "Analytical Engines" };
const post = (body: string) => POST(new Request("http://localhost/api/early-access", {
  method: "POST", headers: { "content-type": "application/json" }, body,
}) as NextRequest);

describe("POST /api/early-access", () => {
  it("returns 400 for invalid JSON", async () => expect((await post("{" )).status).toBe(400));
  it("returns 413 for an oversized body", async () => expect((await post(JSON.stringify({ ...validBody, note: "x".repeat(17_000) }))).status).toBe(413));
  it("returns 502 when the real user-email delivery fails", async () => {
    vi.mocked(sendEarlyAccessEmails).mockResolvedValueOnce({ userEmailSent: false, adminEmailSent: false, simulated: false, error: "provider down" });
    expect((await post(JSON.stringify(validBody))).status).toBe(502);
  });
  it("returns 200 only after real user-email delivery", async () => {
    vi.mocked(sendEarlyAccessEmails).mockResolvedValueOnce({ userEmailSent: true, adminEmailSent: true });
    expect((await post(JSON.stringify(validBody))).status).toBe(200);
  });
  it("does not report success: true on the simulated (no real email sent) path", async () => {
    vi.mocked(sendEarlyAccessEmails).mockResolvedValueOnce({ userEmailSent: false, adminEmailSent: false, simulated: true });
    const res = await post(JSON.stringify(validBody));
    const json = await res.json();
    expect(json.simulated).toBe(true);
    expect(json.success).not.toBe(true);
  });
});

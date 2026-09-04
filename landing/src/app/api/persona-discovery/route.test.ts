import { describe, expect, it, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";
import { POST } from "./route";
import { earlyAccessStore } from "@/lib/early-access-store";

vi.mock("@/lib/early-access-store", () => {
  const updatePersonaDiscovery = vi.fn();
  return {
    earlyAccessStore: {
      updatePersonaDiscovery,
    },
  };
});

function makeRequest(body: unknown): NextRequest {
  return new NextRequest("http://localhost:3000/api/persona-discovery", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

describe("POST /api/persona-discovery", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("updates persona discovery for registered user successfully", async () => {
    vi.mocked(earlyAccessStore.updatePersonaDiscovery).mockResolvedValueOnce(true);

    const req = makeRequest({
      email: "test@school.edu.vn",
      firstProjectGoal: "Làm đồ án tốt nghiệp AI",
      biggestChallenge: ["Quá tải vì làm một mình"],
      aiAutonomyLevel: "L1",
    });

    const res = await POST(req);
    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.success).toBe(true);
  });

  it("returns 404 when email is not found in registrations", async () => {
    vi.mocked(earlyAccessStore.updatePersonaDiscovery).mockResolvedValueOnce(false);

    const req = makeRequest({
      email: "notfound@example.com",
      firstProjectGoal: "Nghiên cứu",
    });

    const res = await POST(req);
    expect(res.status).toBe(404);
    const json = await res.json();
    expect(json.success).toBe(false);
  });

  it("returns 400 for invalid email", async () => {
    const req = makeRequest({
      email: "invalid-email",
    });

    const res = await POST(req);
    expect(res.status).toBe(400);
  });
});

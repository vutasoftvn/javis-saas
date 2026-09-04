import { describe, expect, it } from "vitest";
import { escapeHtml, parseEarlyAccessRegistration, parsePersonaDiscovery } from "./early-access";

describe("early access input", () => {
  it("rejects malformed or overlong input", () => {
    expect(() => parseEarlyAccessRegistration({ fullName: "A", email: "bad", phone: "1", company: "" })).toThrow();
    expect(() => parseEarlyAccessRegistration({ fullName: "A".repeat(121), email: "a@example.com", phone: "0912345678", company: "C" })).toThrow();
  });

  it("escapes all HTML metacharacters before email rendering", () => {
    expect(escapeHtml('<img src=x onerror=alert(1)>')).toBe('&lt;img src=x onerror=alert(1)&gt;');
  });

  it("parses userSegment and projectName properly", () => {
    const parsed = parseEarlyAccessRegistration({
      fullName: "Học Sinh A",
      email: "student@school.edu.vn",
      phone: "0912345678",
      userSegment: "Học sinh, Sinh viên / Nghiên cứu học tập",
      projectName: "Đồ án Tốt nghiệp AI",
    });
    expect(parsed.userSegment).toBe("Học sinh, Sinh viên / Nghiên cứu học tập");
    expect(parsed.projectName).toBe("Đồ án Tốt nghiệp AI");
    expect(parsed.priorityInterest).toBe("Gói Free - 1 Workspace & 1 Project");
  });

  it("parses persona discovery survey successfully", () => {
    const persona = parsePersonaDiscovery({
      email: "founder@opc.vn",
      firstProjectGoal: "Nghiên cứu thị trường & Lập PRD",
      biggestChallenge: ["Quá tải vì làm một mình", "Thiếu phương pháp"],
      aiAutonomyLevel: "L1",
      targetTimelineWeeks: 12,
    });
    expect(persona.email).toBe("founder@opc.vn");
    expect(persona.aiAutonomyLevel).toBe("L1");
    expect(persona.biggestChallenge).toHaveLength(2);
  });
});


import { describe, expect, it } from "vitest";
import {
  evaluatePredicate,
  validatePredicate,
  Predicate,
} from "../../services/customer-engagement/automation/predicate";
import type { AutomationFacts } from "../../services/customer-engagement/automation/facts";

describe("Automation Predicate Evaluator & Validator Tests", () => {
  const sampleFacts: AutomationFacts = {
    thread: {
      status: "open",
      priority: "urgent",
      tier: "vip",
      activeMode: "team_queue",
      ownerMemberId: null,
      escalationLevel: 1,
      ageMinutes: 45,
      minutesSinceLastCustomerMsg: 10,
      firstResponded: false,
      hasOpenDecisionRequest: true,
    },
    inbox: {
      channelType: "zalo",
      locale: "vi",
      businessHoursOpen: true,
    },
    sla: {
      firstResponseDueInMinutes: -15,
      resolutionDueInMinutes: 120,
      firstResponseBreached: true,
      resolutionBreached: false,
      pctToFirstResponseBreach: 100,
    },
    contact: {
      present: true,
      doNotContact: false,
    },
    account: {
      present: true,
    },
    customer: {
      present: true,
      healthStatus: "AT_RISK",
      tier: "enterprise",
    },
    lastMessage: {
      direction: "inbound",
      visibility: "customer",
    },
    csat: {
      latestScore: 2,
      latestRecordedMinutesAgo: 5,
    },
    labels: ["critical", "billing"],
  };

  it("should evaluate eq, ne, gt, gte, lt, lte accurately", () => {
    expect(evaluatePredicate({ fact: "thread.status", op: "eq", value: "open" }, sampleFacts)).toBe(true);
    expect(evaluatePredicate({ fact: "thread.status", op: "ne", value: "resolved" }, sampleFacts)).toBe(true);
    expect(evaluatePredicate({ fact: "thread.ageMinutes", op: "gt", value: 30 }, sampleFacts)).toBe(true);
    expect(evaluatePredicate({ fact: "thread.ageMinutes", op: "gt", value: 60 }, sampleFacts)).toBe(false);
    expect(evaluatePredicate({ fact: "csat.latestScore", op: "lte", value: 2 }, sampleFacts)).toBe(true);
    expect(evaluatePredicate({ fact: "csat.latestScore", op: "gte", value: 3 }, sampleFacts)).toBe(false);
  });

  it("should evaluate in, not_in, contains accurately", () => {
    expect(evaluatePredicate({ fact: "thread.priority", op: "in", value: ["urgent", "high"] }, sampleFacts)).toBe(true);
    expect(evaluatePredicate({ fact: "thread.priority", op: "not_in", value: ["low", "normal"] }, sampleFacts)).toBe(true);
    expect(evaluatePredicate({ fact: "labels", op: "contains", value: "critical" }, sampleFacts)).toBe(true);
    expect(evaluatePredicate({ fact: "labels", op: "contains", value: "sales" }, sampleFacts)).toBe(false);
  });

  it("should handle null facts gracefully (gt on null is false, eq null is true)", () => {
    expect(evaluatePredicate({ fact: "thread.ownerMemberId", op: "eq", value: null as any }, sampleFacts)).toBe(true);
    expect(evaluatePredicate({ fact: "thread.ownerMemberId", op: "gt", value: 5 }, sampleFacts)).toBe(false);
  });

  it("should evaluate nested all, any, not trees", () => {
    const complexPredicate: Predicate = {
      all: [
        { fact: "thread.status", op: "eq", value: "open" },
        {
          any: [
            { fact: "sla.firstResponseBreached", op: "eq", value: true },
            { fact: "customer.healthStatus", op: "eq", value: "CHURNED" },
          ],
        },
        {
          not: {
            fact: "contact.doNotContact",
            op: "eq",
            value: true,
          },
        },
      ],
    };

    expect(evaluatePredicate(complexPredicate, sampleFacts)).toBe(true);
  });

  it("should validate predicate and reject invalid fact keys or invalid ops", () => {
    expect(() =>
      validatePredicate({ fact: "thread.status", op: "eq", value: "open" })
    ).not.toThrow();

    // Invalid fact key
    expect(() =>
      validatePredicate({ fact: "thread.unknown_field", op: "eq", value: "test" })
    ).toThrow(/Invalid fact key/i);

    // Invalid op
    expect(() =>
      validatePredicate({ fact: "thread.status", op: "regex" as any, value: ".*" })
    ).toThrow(/Invalid operator/i);

    // contains on non-array fact
    expect(() =>
      validatePredicate({ fact: "thread.status", op: "contains", value: "open" })
    ).toThrow(/contains/i);

    // in on non-array value
    expect(() =>
      validatePredicate({ fact: "thread.status", op: "in", value: "open" as any })
    ).toThrow(/array value/i);
  });
});

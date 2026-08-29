import { describe, expect, it } from "vitest";
import {
  SLA_POLICY_SEED,
  RETENTION_TRANSCRIPT_DAYS,
  RETENTION_RAW_ATTACHMENT_DAYS,
  RETENTION_METADATA_DAYS,
  computeSlaSnapshot,
  snapshotThreadSla,
  resolveTier,
  dateFromVietnamLocal,
  getVietnamLocalTime,
} from "../../services/customer-engagement/sla.service";
import { generateSnowflake } from "../../../shared/services/snowflake.service";

// Helper: Convert UTC date to Vietnam local time components for assertion
function getVietnamLocalComponents(utcDate: Date): {
  year: number;
  month: number;
  day: number;
  hours: number;
  minutes: number;
  dayOfWeek: number;
} {
  const vietnamOffsetMs = 7 * 60 * 60 * 1000;
  const localTime = new Date(utcDate.getTime() + vietnamOffsetMs);
  return {
    year: localTime.getUTCFullYear(),
    month: localTime.getUTCMonth(),
    day: localTime.getUTCDate(),
    hours: localTime.getUTCHours(),
    minutes: localTime.getUTCMinutes(),
    dayOfWeek: localTime.getUTCDay(),
  };
}

// Helper: Assert that a UTC date equals a Vietnam local instant (Y-M-D H:M)
function assertVietnamLocalInstant(
  utcDate: Date,
  expectedYear: number,
  expectedMonth: number,
  expectedDay: number,
  expectedHours: number,
  expectedMinutes: number,
  label: string = ""
): void {
  const local = getVietnamLocalComponents(utcDate);
  const actual = `${local.year}-${String(local.month + 1).padStart(2, "0")}-${String(local.day).padStart(2, "0")} ${String(local.hours).padStart(2, "0")}:${String(local.minutes).padStart(2, "0")}`;
  const expected = `${expectedYear}-${String(expectedMonth + 1).padStart(2, "0")}-${String(expectedDay).padStart(2, "0")} ${String(expectedHours).padStart(2, "0")}:${String(expectedMinutes).padStart(2, "0")}`;
  if (label) {
    expect(actual, label).toBe(expected);
  } else {
    expect(actual).toBe(expected);
  }
}

describe("SLA_POLICY_SEED", () => {
  it("defines version 1 policy with Asia/Ho_Chi_Minh timezone", () => {
    expect(SLA_POLICY_SEED.version).toBe(1);
    expect(SLA_POLICY_SEED.timezone).toBe("Asia/Ho_Chi_Minh");
  });

  it("has business calendar for weekdays 1-5, 08:30-17:30", () => {
    expect(SLA_POLICY_SEED.business_calendar.weekdays).toEqual([1, 2, 3, 4, 5]);
    expect(SLA_POLICY_SEED.business_calendar.hours.start).toBe("08:30");
    expect(SLA_POLICY_SEED.business_calendar.hours.end).toBe("17:30");
  });

  it("has standard tier with 240min first_response, 1440min resolution on business clock", () => {
    const standard = SLA_POLICY_SEED.tiers.standard;
    expect(standard.first_response_minutes).toBe(240);
    expect(standard.resolution_minutes).toBe(1440);
    expect(standard.clock).toBe("business");
    expect(standard.warning_at_percent).toBe(75);
  });

  it("has priority tier with 60min first_response, 480min resolution on business clock", () => {
    const priority = SLA_POLICY_SEED.tiers.priority;
    expect(priority.first_response_minutes).toBe(60);
    expect(priority.resolution_minutes).toBe(480);
    expect(priority.clock).toBe("business");
    expect(priority.warning_at_percent).toBe(75);
  });

  it("has vip tier with 30min first_response, 480min resolution on calendar clock, on_call mode, route_key support-oncall", () => {
    const vip = SLA_POLICY_SEED.tiers.vip;
    expect(vip.first_response_minutes).toBe(30);
    expect(vip.resolution_minutes).toBe(480);
    expect(vip.clock).toBe("calendar");
    expect(vip.warning_at_percent).toBe(50);
    expect(vip.out_of_hours.mode).toBe("on_call");
    expect(vip.out_of_hours.route_key).toBe("support-oncall");
  });
});

describe("retention constants", () => {
  it("exports RETENTION_TRANSCRIPT_DAYS = 365", () => {
    expect(RETENTION_TRANSCRIPT_DAYS).toBe(365);
  });

  it("exports RETENTION_RAW_ATTACHMENT_DAYS = 90", () => {
    expect(RETENTION_RAW_ATTACHMENT_DAYS).toBe(90);
  });

  it("exports RETENTION_METADATA_DAYS = 730", () => {
    expect(RETENTION_METADATA_DAYS).toBe(730);
  });
});

describe("resolveTier", () => {
  it("returns params.tier if provided", () => {
    const inbox = { defaultTier: "standard" };
    expect(resolveTier(inbox, { tier: "vip" })).toBe("vip");
  });

  it("returns inbox.defaultTier if params.tier not provided", () => {
    const inbox = { defaultTier: "priority" };
    expect(resolveTier(inbox, {})).toBe("priority");
  });

  it("returns 'standard' if neither params.tier nor inbox.defaultTier provided", () => {
    const inbox = {};
    expect(resolveTier(inbox, {})).toBe("standard");
  });

  it("throws invalidArgument for invalid tier", () => {
    const inbox = { defaultTier: "standard" };
    expect(() => resolveTier(inbox, { tier: "invalid" })).toThrow(/invalidArgument|invalid tier/i);
  });
});

describe("computeSlaSnapshot", () => {
  it("computes standard tier with business clock (Mon 10:00 + 240 min = Mon 14:00)", () => {
    const openedAt = new Date("2026-08-31T03:00:00Z"); // Monday 10:00 Vietnam time (UTC+7)
    const snapshot = computeSlaSnapshot(SLA_POLICY_SEED, "standard", openedAt);

    expect(snapshot.version).toBe(1);
    expect(snapshot.tier).toBe("standard");
    expect(snapshot.firstResponseDueAt).toBeDefined();
    expect(snapshot.resolutionDueAt).toBeDefined();
    expect(snapshot.warningAtPercent).toBe(75);
    expect(snapshot.outOfHoursMode).toBe("pause");
    expect(snapshot.routeKey).toBeNull();

    // 240 business minutes = 4 hours, all within same day (10:00 → 14:00)
    assertVietnamLocalInstant(snapshot.firstResponseDueAt, 2026, 7, 31, 14, 0, "Standard tier: Mon 10:00 + 240 min");
  });

  it("computes vip tier with calendar clock (add minutes directly) and on_call routeKey", () => {
    // VIP tier: 30 minutes first_response, calendar clock (direct add), on_call mode
    const openedAt = new Date("2026-08-31T03:00:00Z"); // Monday 10:00 Vietnam time (UTC+7)
    const snapshot = computeSlaSnapshot(SLA_POLICY_SEED, "vip", openedAt);

    expect(snapshot.version).toBe(1);
    expect(snapshot.tier).toBe("vip");
    expect(snapshot.warningAtPercent).toBe(50);
    expect(snapshot.outOfHoursMode).toBe("on_call");
    expect(snapshot.routeKey).toBe("support-oncall");

    // Calendar clock: 30 minutes added directly, should be 10:30
    const firstResponseDue = snapshot.firstResponseDueAt;
    const expectedTime = new Date(openedAt.getTime() + 30 * 60 * 1000);
    expect(firstResponseDue.getTime()).toBe(expectedTime.getTime());

    // Verify calendar clock result: Mon 10:00 + 30 min → Mon 10:30 Vietnam time
    assertVietnamLocalInstant(snapshot.firstResponseDueAt, 2026, 7, 31, 10, 30, "VIP calendar clock: Mon 10:00 + 30 → Mon 10:30");
  });

  // Required test 1: Fri Aug 28 2026 17:00 local + 60 business min → Mon Aug 31 2026 09:00 local
  it("business clock: Friday 17:00 + 60 min → Monday 09:00", () => {
    // Fri Aug 28, 2026 at 17:00 Vietnam time = 10:00 UTC
    const openedAt = new Date("2026-08-28T10:00:00Z");
    const snapshot = computeSlaSnapshot(SLA_POLICY_SEED, "priority", openedAt);
    // 30 min left Friday (17:00→17:30) + 30 min Monday (08:30→09:00) = Monday 09:00
    assertVietnamLocalInstant(snapshot.firstResponseDueAt, 2026, 7, 31, 9, 0, "Fri 17:00 + 60 → Mon 09:00");
  });

  // Required test 2: Mon Aug 31 2026 10:00 local + 240 business min → Mon Aug 31 2026 14:00 local
  it("business clock: Mon 10:00 + 240 min → Mon 14:00 (same day)", () => {
    // Monday Aug 31, 2026 at 10:00 Vietnam time = 03:00 UTC
    const openedAt = new Date("2026-08-31T03:00:00Z");
    const snapshot = computeSlaSnapshot(SLA_POLICY_SEED, "standard", openedAt);
    // 240 min = 4 hours, all within business day (10:00 to 14:00)
    assertVietnamLocalInstant(snapshot.firstResponseDueAt, 2026, 7, 31, 14, 0, "Mon 10:00 + 240 → Mon 14:00");
  });

  // Required test 3: Mon Aug 31 2026 16:00 local + 120 business min → Tue Sept 1 2026 09:00 local
  // (90 min carries: 90 to 17:30 Mon leaves 30 → Tue Sept 1 08:30 + 30 → Tue Sept 1 2026 09:00 local)
  // Test with standard tier 240 min from Mon 16:00:
  // 90 min left Mon (16:00-17:30) + 150 min Tue (08:30-11:00) = Tue 11:00
  it("business clock: Mon 16:00 + 240 min standard tier → Tue 11:00 (overflow to next day)", () => {
    // Monday Aug 31, 2026 at 16:00 Vietnam time = 09:00 UTC
    const openedAt = new Date("2026-08-31T09:00:00Z");

    // Standard tier: 240 min first_response
    const snapshot = computeSlaSnapshot(SLA_POLICY_SEED, "standard", openedAt);
    // 16:00 + 90 min = 17:30 (end of Mon)
    // 08:30 + 150 min = 11:00 (Tue)
    assertVietnamLocalInstant(snapshot.firstResponseDueAt, 2026, 8, 1, 11, 0, "Standard 240min: Mon 16:00 + 240 → Tue 11:00");
  });

  it("pauses timer outside business hours for business clock tiers", () => {
    // Monday 20:00 (outside business hours 08:30-17:30)
    // Add 240 business minutes for standard tier
    // Should advance to next business day
    const openedAt = new Date("2026-08-31T13:00:00Z"); // Monday 20:00 Vietnam time (UTC+7)
    const snapshot = computeSlaSnapshot(SLA_POLICY_SEED, "standard", openedAt);

    expect(snapshot.firstResponseDueAt).toBeDefined();
    // Verify result is within business hours in Vietnam timezone
    const local = getVietnamLocalComponents(snapshot.firstResponseDueAt);
    const timeInMinutes = local.hours * 60 + local.minutes;
    const startMinutes = 8 * 60 + 30; // 08:30
    const endMinutes = 17 * 60 + 30; // 17:30
    expect(timeInMinutes).toBeGreaterThanOrEqual(startMinutes);
    expect(timeInMinutes).toBeLessThanOrEqual(endMinutes);
  });
});

describe("timezone conversion helpers (round-trip test)", () => {
  it("round-trip: dateFromVietnamLocal → getVietnamLocalTime preserves local time", () => {
    // Create a date from Vietnam local time (Aug 31, 2026 16:00 Vietnam time)
    const utcDate = dateFromVietnamLocal(2026, 7, 31, 16, 0, 0); // 0-indexed month: 7=Aug
    const local = getVietnamLocalTime(utcDate);

    expect(local.year).toBe(2026);
    expect(local.month).toBe(7); // August (0-indexed)
    expect(local.day).toBe(31);
    expect(local.hours).toBe(16);
    expect(local.minutes).toBe(0);
    // Aug 31 is Monday (day 1)
    expect(local.dayOfWeek).toBe(1);
  });

  it("can create dates for day overflow (Aug 31 + 1 = Sept 1)", () => {
    // When adding 1 day to Aug 31, we should get Sept 1
    const nextDay = dateFromVietnamLocal(2026, 7, 32, 8, 30, 0); // Aug 32 overflows to Sept 1
    const local = getVietnamLocalTime(nextDay);

    expect(local.year).toBe(2026);
    expect(local.month).toBe(8); // September (0-indexed)
    expect(local.day).toBe(1);
    expect(local.hours).toBe(8);
    expect(local.minutes).toBe(30);
    // Sept 1 is Tuesday (day 2)
    expect(local.dayOfWeek).toBe(2);
  });
});

describe("snapshotThreadSla", () => {
  it("returns partial insert values for thread opening", () => {
    const threadValues = { workspaceId: BigInt(generateSnowflake()) };
    const openedAt = new Date("2026-08-31T10:00:00+07:00");
    const snapshot = snapshotThreadSla(threadValues, SLA_POLICY_SEED, "vip", openedAt);

    expect(snapshot.tier).toBe("vip");
    expect(snapshot.slaPolicyVersion).toBe(1);
    expect(snapshot.slaSnapshot).toBeDefined();
    expect(snapshot.firstResponseDueAt).toBeDefined();
    expect(snapshot.resolutionDueAt).toBeDefined();
    expect(snapshot.escalationRouteKey).toBe("support-oncall");
  });

  it("sets escalationRouteKey to null for pause mode tiers", () => {
    const threadValues = { workspaceId: BigInt(generateSnowflake()) };
    const openedAt = new Date("2026-08-31T10:00:00+07:00");
    const snapshot = snapshotThreadSla(threadValues, SLA_POLICY_SEED, "standard", openedAt);

    expect(snapshot.escalationRouteKey).toBeNull();
  });

  it("snapshot object contains version, tier, warning percent, route key", () => {
    const threadValues = { workspaceId: BigInt(generateSnowflake()) };
    const openedAt = new Date("2026-08-31T10:00:00+07:00");
    const snapshot = snapshotThreadSla(threadValues, SLA_POLICY_SEED, "vip", openedAt);

    const slaSnapshot = snapshot.slaSnapshot as any;
    expect(slaSnapshot.version).toBe(1);
    expect(slaSnapshot.tier).toBe("vip");
    expect(slaSnapshot.warningAtPercent).toBe(50);
    expect(slaSnapshot.outOfHoursMode).toBe("on_call");
    expect(slaSnapshot.routeKey).toBe("support-oncall");
  });
});

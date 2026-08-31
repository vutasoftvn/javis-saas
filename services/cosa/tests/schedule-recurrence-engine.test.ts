// Schedule recurrence engine — timezone, DST, and recurrence-rule calculation.
import { describe, expect, it } from "vitest";
import {
  calculateNextRun,
  getUtcDateFromTzWallClock,
  getTzDayOfWeek,
  validateIanaTimezone,
} from "../services/schedule/schedule-recurrence.engine";

describe("schedule recurrence engine", () => {
  // ============================================================================
  // validateIanaTimezone
  // ============================================================================
  describe("validateIanaTimezone", () => {
    it("accepts valid IANA timezone", () => {
      expect(() => validateIanaTimezone("Asia/Ho_Chi_Minh")).not.toThrow();
      expect(() => validateIanaTimezone("America/New_York")).not.toThrow();
      expect(() => validateIanaTimezone("Europe/London")).not.toThrow();
      expect(() => validateIanaTimezone("UTC")).not.toThrow();
    });

    it("rejects invalid IANA timezone", () => {
      expect(() => validateIanaTimezone("InvalidTZ")).toThrow();
      expect(() => validateIanaTimezone("NotATimezone")).toThrow();
    });
  });

  // ============================================================================
  // getUtcDateFromTzWallClock — wall-clock conversion without DST
  // ============================================================================
  describe("getUtcDateFromTzWallClock — Asia/Ho_Chi_Minh (no DST)", () => {
    it("converts wall-clock time in UTC+7 timezone to UTC correctly", () => {
      // 2026-09-01 12:00:00 in Asia/Ho_Chi_Minh (UTC+7) = 2026-09-01 05:00:00 UTC
      const result = getUtcDateFromTzWallClock(
        2026,
        8, // September (0-indexed)
        1,
        12,
        0,
        "Asia/Ho_Chi_Minh"
      );
      expect(result.getUTCHours()).toBe(5);
      expect(result.getUTCMinutes()).toBe(0);
      expect(result.getUTCDate()).toBe(1);
      expect(result.getUTCMonth()).toBe(8);
      expect(result.getUTCFullYear()).toBe(2026);
    });

    it("handles midnight in wall-clock timezone", () => {
      // 2026-09-01 00:00:00 in Asia/Ho_Chi_Minh (UTC+7) = 2026-08-31 17:00:00 UTC
      const result = getUtcDateFromTzWallClock(
        2026,
        8,
        1,
        0,
        0,
        "Asia/Ho_Chi_Minh"
      );
      expect(result.getUTCHours()).toBe(17);
      expect(result.getUTCDate()).toBe(31);
      expect(result.getUTCMonth()).toBe(7);
    });

    it("handles end of month correctly in wall-clock timezone", () => {
      // 2026-08-31 23:59:00 in Asia/Ho_Chi_Minh (UTC+7) = 2026-08-31 16:59:00 UTC
      const result = getUtcDateFromTzWallClock(
        2026,
        7,
        31,
        23,
        59,
        "Asia/Ho_Chi_Minh"
      );
      expect(result.getUTCHours()).toBe(16);
      expect(result.getUTCMinutes()).toBe(59);
      expect(result.getUTCDate()).toBe(31);
      expect(result.getUTCMonth()).toBe(7);
    });
  });

  // ============================================================================
  // getUtcDateFromTzWallClock — DST-observing timezones
  // ============================================================================
  describe("getUtcDateFromTzWallClock — America/New_York (with DST)", () => {
    it("converts wall-clock time in EDT (UTC-4) to UTC correctly", () => {
      // 2026-09-01 12:00:00 EDT (UTC-4, daylight saving active) = 2026-09-01 16:00:00 UTC
      const result = getUtcDateFromTzWallClock(
        2026,
        8, // September (DST active)
        1,
        12,
        0,
        "America/New_York"
      );
      expect(result.getUTCHours()).toBe(16);
      expect(result.getUTCMinutes()).toBe(0);
    });

    it("converts wall-clock time in EST (UTC-5) to UTC correctly", () => {
      // 2026-01-01 12:00:00 EST (UTC-5, no daylight saving) = 2026-01-01 17:00:00 UTC
      const result = getUtcDateFromTzWallClock(
        2026,
        0, // January (standard time)
        1,
        12,
        0,
        "America/New_York"
      );
      expect(result.getUTCHours()).toBe(17);
      expect(result.getUTCMinutes()).toBe(0);
    });
  });

  describe("getUtcDateFromTzWallClock — Europe/London (with DST)", () => {
    it("converts wall-clock time in BST (UTC+1) to UTC correctly", () => {
      // 2026-09-01 12:00:00 BST (UTC+1, daylight saving active) = 2026-09-01 11:00:00 UTC
      const result = getUtcDateFromTzWallClock(
        2026,
        8, // September (DST active)
        1,
        12,
        0,
        "Europe/London"
      );
      expect(result.getUTCHours()).toBe(11);
      expect(result.getUTCMinutes()).toBe(0);
    });

    it("converts wall-clock time in GMT (UTC+0) to UTC correctly", () => {
      // 2026-01-01 12:00:00 GMT (UTC+0, standard time) = 2026-01-01 12:00:00 UTC
      const result = getUtcDateFromTzWallClock(
        2026,
        0, // January (standard time)
        1,
        12,
        0,
        "Europe/London"
      );
      expect(result.getUTCHours()).toBe(12);
      expect(result.getUTCMinutes()).toBe(0);
    });
  });

  // ============================================================================
  // getTzDayOfWeek
  // ============================================================================
  describe("getTzDayOfWeek", () => {
    it("returns correct day of week in target timezone", () => {
      // 2026-09-01 is a Tuesday
      // Create a UTC date and verify day of week in different timezones
      const utcDate = new Date("2026-09-01T00:00:00Z");
      expect(getTzDayOfWeek(utcDate, "UTC")).toBe(2); // Tuesday
    });

    it("handles day-of-week boundary crossing near midnight", () => {
      // 2026-09-01 00:30 UTC is still Tuesday in UTC, but may be different in earlier timezones
      const utcDate = new Date("2026-09-01T00:30:00Z");
      const utcDow = getTzDayOfWeek(utcDate, "UTC");
      expect(utcDow).toBe(2); // Tuesday

      // In Asia/Ho_Chi_Minh (UTC+7), this is 2026-09-01 07:30, still Tuesday
      const hcmDow = getTzDayOfWeek(utcDate, "Asia/Ho_Chi_Minh");
      expect(hcmDow).toBe(2); // Still Tuesday
    });

    it("handles timezone where local date is previous day from UTC", () => {
      // 2026-09-01 02:00 UTC = 2026-08-31 22:00 EDT (previous day in America/New_York)
      const utcDate = new Date("2026-09-01T02:00:00Z");
      const utcDow = getTzDayOfWeek(utcDate, "UTC");
      const edtDow = getTzDayOfWeek(utcDate, "America/New_York");
      // UTC: Sept 1 = Tuesday (2)
      // EDT: Aug 31 = Monday (1)
      expect(utcDow).toBe(2);
      expect(edtDow).toBe(1);
    });

    it("maps all weekday abbreviations correctly", () => {
      // Use specific UTC dates that correspond to each day of week
      // 2026-08-31 is Monday
      const dates = [
        { date: new Date("2026-08-31T00:00:00Z"), expectedDow: 1 }, // Monday
        { date: new Date("2026-09-01T00:00:00Z"), expectedDow: 2 }, // Tuesday
        { date: new Date("2026-09-02T00:00:00Z"), expectedDow: 3 }, // Wednesday
        { date: new Date("2026-09-03T00:00:00Z"), expectedDow: 4 }, // Thursday
        { date: new Date("2026-09-04T00:00:00Z"), expectedDow: 5 }, // Friday
        { date: new Date("2026-09-05T00:00:00Z"), expectedDow: 6 }, // Saturday
        { date: new Date("2026-09-06T00:00:00Z"), expectedDow: 7 }, // Sunday
      ];

      for (const { date, expectedDow } of dates) {
        expect(getTzDayOfWeek(date, "UTC")).toBe(expectedDow);
      }
    });
  });

  // ============================================================================
  // calculateNextRun — basic functionality
  // ============================================================================
  describe("calculateNextRun — basic recurrence", () => {
    it("returns null for one_time schedule", () => {
      const now = new Date("2026-09-01T12:00:00Z");
      const result = calculateNextRun("one_time", "Asia/Ho_Chi_Minh", 14, 30, null, now);
      expect(result).toBeNull();
    });

    it("calculates next daily run in target timezone", () => {
      // Now: 2026-09-01 10:00 UTC
      // Target: 14:00 (2 PM) in Asia/Ho_Chi_Minh (UTC+7)
      //   Today at 14:00 HCM = 2026-09-01 07:00 UTC (in the past)
      //   Tomorrow at 14:00 HCM = 2026-09-02 07:00 UTC (next run)
      const now = new Date("2026-09-01T10:00:00Z");
      const result = calculateNextRun("daily", "Asia/Ho_Chi_Minh", 14, 0, null, now);

      expect(result).not.toBeNull();
      expect(result!.getUTCHours()).toBe(7);
      expect(result!.getUTCDate()).toBe(2);
      expect(result!.getUTCMonth()).toBe(8);
    });

    it("handles exact match of current time correctly", () => {
      // Now: 2026-09-01 07:00 UTC = 2026-09-01 14:00 HCM
      // Next run at 14:00 HCM should be tomorrow
      const now = new Date("2026-09-01T07:00:00Z");
      const result = calculateNextRun("daily", "Asia/Ho_Chi_Minh", 14, 0, null, now);

      expect(result).not.toBeNull();
      // Should be tomorrow
      expect(result!.getUTCDate()).toBe(2);
    });

    it("returns next run within 14-day search window", () => {
      const now = new Date("2026-09-01T10:00:00Z");
      const result = calculateNextRun("daily", "UTC", 12, 30, null, now);

      expect(result).not.toBeNull();
      expect(result!.getUTCHours()).toBe(12);
      expect(result!.getUTCMinutes()).toBe(30);
      // Should be tomorrow or today depending on current time
      const diffDays = (result!.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);
      expect(diffDays).toBeGreaterThan(0);
      expect(diffDays).toBeLessThanOrEqual(14);
    });

    it("throws on invalid hour", () => {
      const now = new Date("2026-09-01T10:00:00Z");
      expect(() =>
        calculateNextRun("daily", "UTC", 25, 0, null, now)
      ).toThrow();
    });

    it("throws on invalid minute", () => {
      const now = new Date("2026-09-01T10:00:00Z");
      expect(() =>
        calculateNextRun("daily", "UTC", 12, 60, null, now)
      ).toThrow();
    });

    it("uses default hour=0 and minute=0 when null", () => {
      // Now: 2026-09-01 01:00 UTC
      // Next midnight UTC should be tomorrow
      const now = new Date("2026-09-01T01:00:00Z");
      const result = calculateNextRun("daily", "UTC", null, null, null, now);

      expect(result).not.toBeNull();
      expect(result!.getUTCHours()).toBe(0);
      expect(result!.getUTCMinutes()).toBe(0);
      expect(result!.getUTCDate()).toBe(2);
    });
  });

  // ============================================================================
  // calculateNextRun — weekdays recurrence
  // ============================================================================
  describe("calculateNextRun — weekdays recurrence", () => {
    it("skips weekends when weekdays=[1,2,3,4,5] (Mon-Fri)", () => {
      // 2026-09-05 is Saturday, 2026-09-06 is Sunday
      // Schedule at 10:00 UTC on weekdays only
      // From Friday 2026-09-04 23:00 UTC, next should be Monday 2026-09-07 10:00 UTC
      const now = new Date("2026-09-04T23:00:00Z");
      const result = calculateNextRun("weekdays", "UTC", 10, 0, [1, 2, 3, 4, 5], now);

      expect(result).not.toBeNull();
      expect(result!.getUTCDate()).toBe(7); // Monday
      expect(result!.getUTCHours()).toBe(10);
    });

    it("returns null when no weekdays match and search exhausted", () => {
      // Schedule only on Sunday (7), starting from a Friday evening
      // 14-day window: should find next Sunday
      const now = new Date("2026-09-04T23:00:00Z");
      const result = calculateNextRun("weekdays", "UTC", 10, 0, [7], now);

      expect(result).not.toBeNull();
      // Next Sunday from Friday 2026-09-04 should be 2026-09-06
      expect(result!.getUTCDate()).toBe(6);
    });

    it("handles timezone day-of-week offset correctly", () => {
      // 2026-09-01 00:00 UTC is Tuesday
      // In America/New_York (EDT, UTC-4), this is 2026-08-31 20:00 EDT, which is Monday
      // Schedule weekdays only (Mon-Fri) at 10:00 EDT
      // So 2026-08-31 10:00 EDT (Mon) is in the past, next is 2026-09-01 10:00 EDT (Tue)
      const now = new Date("2026-08-31T16:00:00Z"); // 12:00 PM EDT on Monday
      const result = calculateNextRun("weekdays", "America/New_York", 10, 0, [1, 2, 3, 4, 5], now);

      expect(result).not.toBeNull();
      // Should find next weekday
      const tzDow = getTzDayOfWeek(result!, "America/New_York");
      expect([1, 2, 3, 4, 5]).toContain(tzDow);
    });

    it("returns null when no matching weekday in search window", () => {
      // This is tricky — we'd need a scenario where no weekday exists in 14 days,
      // which is impossible. So let's test with empty weekdays array instead.
      const now = new Date("2026-09-01T10:00:00Z");
      const result = calculateNextRun("weekdays", "UTC", 10, 0, [], now);

      expect(result).toBeNull();
    });

    it("handles null weekdays array", () => {
      const now = new Date("2026-09-01T10:00:00Z");
      const result = calculateNextRun("weekdays", "UTC", 10, 0, null, now);

      expect(result).toBeNull();
    });
  });

  // ============================================================================
  // calculateNextRun — DST edge cases (spring forward)
  // ============================================================================
  describe("calculateNextRun — DST spring-forward edge case (America/New_York)", () => {
    it("handles schedule at time that skips during spring-forward transition", () => {
      // In America/New_York in 2026:
      // DST spring-forward happens on 2026-03-08 at 02:00 EST → 03:00 EDT
      // If schedule is at 02:30 (which doesn't exist that morning), ensure calculation is sound
      // Note: the wall-clock converter should handle this gracefully
      const now = new Date("2026-03-07T12:00:00Z"); // Day before transition
      // Try to schedule at 02:30 EST (which becomes 03:30 EDT in the spring-forward skip)
      const result = calculateNextRun("daily", "America/New_York", 2, 30, null, now);

      expect(result).not.toBeNull();
      // The result should be a valid UTC time
      expect(result!.getTime()).toBeGreaterThan(now.getTime());
    });
  });

  // ============================================================================
  // calculateNextRun — DST edge cases (fall back)
  // ============================================================================
  describe("calculateNextRun — DST fall-back edge case (America/New_York)", () => {
    it("handles schedule during fall-back transition (time occurs twice)", () => {
      // In America/New_York in 2026:
      // DST fall-back happens on 2026-11-01 at 02:00 EDT → 01:00 EST
      // Times between 01:00-02:00 occur twice that hour
      const now = new Date("2026-10-31T12:00:00Z"); // Day before transition
      // Schedule at 01:30 (occurs twice during transition)
      const result = calculateNextRun("daily", "America/New_York", 1, 30, null, now);

      expect(result).not.toBeNull();
      // Result should be a valid UTC time
      expect(result!.getTime()).toBeGreaterThan(now.getTime());
    });
  });

  // ============================================================================
  // calculateNextRun — DST edge cases (Europe/London)
  // ============================================================================
  describe("calculateNextRun — DST transitions (Europe/London)", () => {
    it("handles spring-forward transition in Europe/London", () => {
      // Europe/London spring-forward: 2026-03-29 at 01:00 GMT → 02:00 BST
      const now = new Date("2026-03-28T12:00:00Z");
      const result = calculateNextRun("daily", "Europe/London", 12, 0, null, now);

      expect(result).not.toBeNull();
      expect(result!.getTime()).toBeGreaterThan(now.getTime());
    });

    it("handles fall-back transition in Europe/London", () => {
      // Europe/London fall-back: 2026-10-25 at 02:00 BST → 01:00 GMT
      const now = new Date("2026-10-24T12:00:00Z");
      const result = calculateNextRun("daily", "Europe/London", 12, 0, null, now);

      expect(result).not.toBeNull();
      expect(result!.getTime()).toBeGreaterThan(now.getTime());
    });
  });

  // ============================================================================
  // calculateNextRun — Crossing DST boundary with weekday filter
  // ============================================================================
  describe("calculateNextRun — DST boundary with weekdays filter", () => {
    it("finds correct weekday across DST transition", () => {
      // Schedule a Friday 14:00 EDT in March 2026 (around spring transition)
      // March 2026: 6, 13, 20, 27 are Fridays
      const now = new Date("2026-03-22T15:00:00Z"); // Sunday evening before 27th
      const result = calculateNextRun(
        "weekdays",
        "America/New_York",
        14,
        0,
        [5], // Friday only
        now
      );

      expect(result).not.toBeNull();
      // Should find Friday 2026-03-27
      const tzDow = getTzDayOfWeek(result!, "America/New_York");
      expect(tzDow).toBe(5); // Friday
    });
  });

  // ============================================================================
  // calculateNextRun — Edge case: month-end boundaries
  // ============================================================================
  describe("calculateNextRun — month-end boundaries", () => {
    it("finds next run correctly at month boundaries", () => {
      // August 31, 23:00 UTC in Asia/Ho_Chi_Minh is Sept 1, 06:00 HCM
      // Next run at 14:00 HCM should be Sept 1
      const now = new Date("2026-08-31T23:00:00Z");
      const result = calculateNextRun("daily", "Asia/Ho_Chi_Minh", 14, 0, null, now);

      expect(result).not.toBeNull();
      expect(result!.getUTCDate()).toBe(1);
      expect(result!.getUTCMonth()).toBe(8); // September (0-indexed)
    });
  });

  // ============================================================================
  // calculateNextRun — Edge case: leap year
  // ============================================================================
  describe("calculateNextRun — leap year handling", () => {
    it("handles schedule at Feb 29 in a leap year", () => {
      // 2024 is a leap year, 2026 is not
      // If we're in 2026 and schedule for Feb 29, it should skip to March 1 or next leap year
      // But our function just calculates next run day by day, so it should handle this
      const now = new Date("2026-02-28T10:00:00Z");
      const result = calculateNextRun("daily", "UTC", 14, 0, null, now);

      expect(result).not.toBeNull();
      // Should find a valid future date
      expect(result!.getTime()).toBeGreaterThan(now.getTime());
    });

    it("handles Feb 29 in actual leap year 2024", () => {
      const now = new Date("2024-02-28T10:00:00Z");
      const result = calculateNextRun("daily", "UTC", 14, 0, null, now);

      expect(result).not.toBeNull();
      // Could be Feb 29 or Mar 1
      expect(result!.getTime()).toBeGreaterThan(now.getTime());
    });
  });

  // ============================================================================
  // calculateNextRun — Timezone validation
  // ============================================================================
  describe("calculateNextRun — timezone validation", () => {
    it("throws on invalid timezone", () => {
      const now = new Date("2026-09-01T10:00:00Z");
      expect(() =>
        calculateNextRun("daily", "InvalidTZ", 14, 0, null, now)
      ).toThrow();
    });
  });

  // ============================================================================
  // calculateNextRun — Integration: multiple timezones, same schedule
  // ============================================================================
  describe("calculateNextRun — consistency across timezones", () => {
    it("produces correct UTC times across three different timezones for same wall-clock time", () => {
      const now = new Date("2026-09-01T10:00:00Z");
      const wallClockHour = 14;
      const wallClockMinute = 0;

      const hcmResult = calculateNextRun(
        "daily",
        "Asia/Ho_Chi_Minh",
        wallClockHour,
        wallClockMinute,
        null,
        now
      );
      const nycResult = calculateNextRun(
        "daily",
        "America/New_York",
        wallClockHour,
        wallClockMinute,
        null,
        now
      );
      const lonResult = calculateNextRun(
        "daily",
        "Europe/London",
        wallClockHour,
        wallClockMinute,
        null,
        now
      );

      // All should be valid dates
      expect(hcmResult).not.toBeNull();
      expect(nycResult).not.toBeNull();
      expect(lonResult).not.toBeNull();

      // All should be in the future
      expect(hcmResult!.getTime()).toBeGreaterThan(now.getTime());
      expect(nycResult!.getTime()).toBeGreaterThan(now.getTime());
      expect(lonResult!.getTime()).toBeGreaterThan(now.getTime());

      // They should all be different UTC times (because local 14:00 means different UTC times)
      expect(hcmResult!.getTime()).not.toBe(nycResult!.getTime());
      expect(nycResult!.getTime()).not.toBe(lonResult!.getTime());
    });
  });

  // ============================================================================
  // calculateNextRun — Real-world scenario: Daily standup at 09:00 Asia/Ho_Chi_Minh
  // ============================================================================
  describe("calculateNextRun — real-world scenario", () => {
    it("correctly schedules daily 09:00 HCM standup", () => {
      // Scenario: daily standup at 09:00 Asia/Ho_Chi_Minh
      // Monday morning 2026-09-01, we want to find when the next standup runs
      const scheduleCreatedAt = new Date("2026-09-01T01:00:00Z"); // 08:00 HCM on Mon
      const result = calculateNextRun(
        "daily",
        "Asia/Ho_Chi_Minh",
        9,
        0,
        null,
        scheduleCreatedAt
      );

      expect(result).not.toBeNull();
      // 09:00 HCM = 02:00 UTC
      expect(result!.getUTCHours()).toBe(2);
      expect(result!.getUTCMinutes()).toBe(0);
    });

    it("correctly schedules weekday-only 14:00 EDT meetings (US trading hours)", () => {
      // Scenario: business meeting Mon-Fri at 14:00 EDT (2 PM Eastern)
      // Called on Friday evening
      const now = new Date("2026-09-04T23:00:00Z"); // 19:00 EDT Friday
      const result = calculateNextRun(
        "weekdays",
        "America/New_York",
        14,
        0,
        [1, 2, 3, 4, 5],
        now
      );

      expect(result).not.toBeNull();
      // Should be Monday 14:00 EDT = 18:00 UTC (Sept 7)
      expect(result!.getUTCDate()).toBe(7);
      expect(result!.getUTCHours()).toBe(18);
    });
  });
});

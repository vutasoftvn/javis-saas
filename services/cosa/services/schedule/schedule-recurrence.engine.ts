import { APIError } from "encore.dev/api";
import { ScheduleKind } from "./schedule-types";

export function validateIanaTimezone(tz: string): void {
  try {
    Intl.DateTimeFormat(undefined, { timeZone: tz });
  } catch {
    throw APIError.invalidArgument(`invalid IANA timezone: '${tz}'`);
  }
}

/**
 * Calculates next run date in UTC given timezone, hour, minute, and optional weekdays (1-7, Mon-Sun).
 */
export function calculateNextRun(
  kind: ScheduleKind,
  tz: string,
  hour?: number | null,
  minute?: number | null,
  weekdays?: number[] | null,
  now: Date = new Date()
): Date | null {
  if (kind === "one_time") {
    return null;
  }

  validateIanaTimezone(tz);
  const h = hour ?? 0;
  const m = minute ?? 0;
  if (h < 0 || h > 23 || m < 0 || m > 59) {
    throw APIError.invalidArgument(`invalid hour (${h}) or minute (${m})`);
  }

  // Iterate up to 14 days ahead to find the next matching slot
  for (let offsetDays = 0; offsetDays <= 14; offsetDays++) {
    const testDate = new Date(now.getTime() + offsetDays * 86400000);

    // Format testDate in target timezone to get YYYY-MM-DD
    const formatter = new Intl.DateTimeFormat("en-US", {
      timeZone: tz,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      weekday: "narrow",
    });

    const parts = formatter.formatToParts(testDate);
    const partMap: Record<string, string> = {};
    for (const p of parts) {
      partMap[p.type] = p.value;
    }
    const year = parseInt(partMap.year, 10);
    const month = parseInt(partMap.month, 10) - 1;
    const day = parseInt(partMap.day, 10);

    // Convert wall time in target tz to UTC Date
    const targetUtc = getUtcDateFromTzWallClock(year, month, day, h, m, tz);

    if (targetUtc > now) {
      if (kind === "daily") {
        return targetUtc;
      }
      if (kind === "weekdays" && weekdays && weekdays.length > 0) {
        // Get day of week in target timezone (1=Mon, ..., 7=Sun)
        const dayOfWeekTz = getTzDayOfWeek(targetUtc, tz);
        if (weekdays.includes(dayOfWeekTz)) {
          return targetUtc;
        }
      }
    }
  }

  return null;
}

export function getUtcDateFromTzWallClock(
  year: number,
  month: number,
  day: number,
  hour: number,
  minute: number,
  tz: string
): Date {
  const baseUtc = new Date(Date.UTC(year, month, day, hour, minute, 0));
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });

  const parts = formatter.formatToParts(baseUtc);
  const partMap: Record<string, string> = {};
  for (const p of parts) partMap[p.type] = p.value;
  let hTz = parseInt(partMap.hour, 10);
  if (hTz === 24) hTz = 0;
  const mTz = parseInt(partMap.minute, 10);
  const yTz = parseInt(partMap.year, 10);
  const monTz = parseInt(partMap.month, 10) - 1;
  const dTz = parseInt(partMap.day, 10);

  const asUtc = Date.UTC(yTz, monTz, dTz, hTz, mTz, 0);
  const offsetMs = asUtc - baseUtc.getTime();
  return new Date(baseUtc.getTime() - offsetMs);
}

export function getTzDayOfWeek(date: Date, tz: string): number {
  const dayStr = new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    weekday: "short",
  }).format(date);
  const map: Record<string, number> = {
    Mon: 1,
    Tue: 2,
    Wed: 3,
    Thu: 4,
    Fri: 5,
    Sat: 6,
    Sun: 7,
  };
  return map[dayStr] || 1;
}

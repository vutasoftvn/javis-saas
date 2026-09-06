import { APIError } from "encore.dev/api";

/**
 * Validates whether a given string is a strictly valid civil date in YYYY-MM-DD format.
 * Rejects non-existent dates (e.g., 2026-02-30, 2026-13-45) via round-trip date parsing.
 */
export function validateLocalDateString(dateStr: string): { year: number; month: number; day: number } {
  if (!dateStr || typeof dateStr !== "string") {
    throw APIError.invalidArgument("Date string must be a non-empty string in YYYY-MM-DD format");
  }
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateStr.trim());
  if (!match) {
    throw APIError.invalidArgument(`Invalid date format '${dateStr}', expected YYYY-MM-DD`);
  }

  const year = parseInt(match[1]!, 10);
  const month = parseInt(match[2]!, 10);
  const day = parseInt(match[3]!, 10);

  if (month < 1 || month > 12) {
    throw APIError.invalidArgument(`Invalid month in date '${dateStr}'`);
  }

  const d = new Date(Date.UTC(year, month - 1, day));
  if (
    d.getUTCFullYear() !== year ||
    d.getUTCMonth() !== month - 1 ||
    d.getUTCDate() !== day
  ) {
    throw APIError.invalidArgument(`Date '${dateStr}' does not exist on the calendar`);
  }

  return { year, month, day };
}

/**
 * Calculates civil epoch days (days elapsed since 1970-01-01 UTC).
 * Pure date arithmetic, immune to DST and timezone hour variations.
 */
export function localDateToEpochDays(dateStr: string): number {
  const { year, month, day } = validateLocalDateString(dateStr);
  const ms = Date.UTC(year, month - 1, day);
  return Math.floor(ms / 86400000);
}

/**
 * Converts civil epoch days back into YYYY-MM-DD format.
 */
export function epochDaysToLocalDate(epochDays: number): string {
  const d = new Date(epochDays * 86400000);
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  const day = String(d.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/**
 * Adds an integer number of days to a civil local date.
 */
export function addDaysToLocalDate(dateStr: string, days: number): string {
  if (!Number.isInteger(days)) {
    throw APIError.invalidArgument(`days must be an integer, got ${days}`);
  }
  const epochDays = localDateToEpochDays(dateStr);
  return epochDaysToLocalDate(epochDays + days);
}

/**
 * Calculates end date exclusive of a cycle:
 * endLocalDateExclusive = startLocalDate + (7 * durationWeeks) days.
 */
export function calculateCycleEndDateExclusive(startLocalDate: string, durationWeeks: number): string {
  validateDurationWeeks(durationWeeks);
  return addDaysToLocalDate(startLocalDate, durationWeeks * 7);
}

/**
 * Validates duration in weeks. Must be a positive integer (e.g. 2, 6, 12, 16).
 */
export function validateDurationWeeks(durationWeeks: number): void {
  if (!Number.isInteger(durationWeeks) || durationWeeks <= 0) {
    throw APIError.invalidArgument(`durationWeeks must be a positive integer, got ${durationWeeks}`);
  }
}

/**
 * Resolves which 1-based execution week a given local date falls into.
 * Returns null if the target date is before startLocalDate or on/after endLocalDateExclusive.
 *
 * Each week is a 7-day civil block:
 * - Week 1: [start, start + 7d)
 * - Week 2: [start + 7d, start + 14d)
 * - ...
 * - Week N: [start + (N-1)*7d, start + N*7d)
 */
export function resolveExecutionWeek(
  startLocalDate: string,
  durationWeeks: number,
  localDate: string
): number | null {
  validateDurationWeeks(durationWeeks);
  const startDays = localDateToEpochDays(startLocalDate);
  const targetDays = localDateToEpochDays(localDate);

  const diffDays = targetDays - startDays;
  if (diffDays < 0) {
    return null; // Before cycle start
  }

  const totalDays = durationWeeks * 7;
  if (diffDays >= totalDays) {
    return null; // On or after end date exclusive
  }

  const weekNo = Math.floor(diffDays / 7) + 1;
  if (weekNo < 1 || weekNo > durationWeeks) {
    return null;
  }
  return weekNo;
}

/**
 * Converts a UTC/timestamp instant into a local date string (YYYY-MM-DD)
 * using the specified IANA timezone (e.g., 'Asia/Ho_Chi_Minh', 'America/New_York').
 */
export function getLocalDateFromInstant(instant: Date, timezone = "UTC"): string {
  try {
    const formatter = new Intl.DateTimeFormat("en-CA", {
      timeZone: timezone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
    return formatter.format(instant);
  } catch {
    // Fallback if invalid timezone passed
    const formatter = new Intl.DateTimeFormat("en-CA", {
      timeZone: "UTC",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
    return formatter.format(instant);
  }
}

/**
 * Finds next Monday on or after a given civil local date.
 * If the date is already a Monday, returns that date.
 */
export function nextMondayOnOrAfterLocalDate(localDate: string): string {
  const { year, month, day } = validateLocalDateString(localDate);
  const d = new Date(Date.UTC(year, month - 1, day));
  const isoDay = d.getUTCDay() === 0 ? 7 : d.getUTCDay(); // 1=Mon..7=Sun
  const add = isoDay === 1 ? 0 : 8 - isoDay;
  return addDaysToLocalDate(localDate, add);
}

/**
 * Converts a civil date string (YYYY-MM-DD) and optional local time into a UTC Date instant
 * representing that exact civil date and time in the specified timezone.
 * Roundtrips safely with getLocalDateFromInstant(instant, timezone) === localDate.
 */
export function localDateToTimezoneInstant(localDate: string, timezone = "UTC", time = "12:00:00"): Date {
  validateLocalDateString(localDate);
  const guess = new Date(`${localDate}T${time}Z`);
  try {
    const invDate = new Date(guess.toLocaleString("en-US", { timeZone: timezone }));
    const diff = guess.getTime() - invDate.getTime();
    return new Date(guess.getTime() + diff);
  } catch {
    return guess;
  }
}


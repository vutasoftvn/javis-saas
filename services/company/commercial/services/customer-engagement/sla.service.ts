import { APIError } from "encore.dev/api";

// SLA Policy seed - freeze version 1 policy with Asia/Ho_Chi_Minh timezone
export const SLA_POLICY_SEED = {
  version: 1,
  timezone: "Asia/Ho_Chi_Minh",
  business_calendar: {
    weekdays: [1, 2, 3, 4, 5] as number[], // Mon-Fri (1-5)
    hours: {
      start: "08:30",
      end: "17:30",
    },
    holiday_calendar: "VN",
  },
  tiers: {
    standard: {
      first_response_minutes: 240,
      resolution_minutes: 1440,
      clock: "business" as const,
      warning_at_percent: 75,
      out_of_hours: {
        mode: "pause" as const,
      },
    },
    priority: {
      first_response_minutes: 60,
      resolution_minutes: 480,
      clock: "business" as const,
      warning_at_percent: 75,
      out_of_hours: {
        mode: "pause" as const,
      },
    },
    vip: {
      first_response_minutes: 30,
      resolution_minutes: 480,
      clock: "calendar" as const,
      warning_at_percent: 50,
      out_of_hours: {
        mode: "on_call" as const,
        route_key: "support-oncall",
        steps: [
          { role: "primary", ack_minutes: 15 },
          { role: "backup", after_minutes: 15 },
          { role: "duty_manager", after_minutes: 30 },
        ],
      },
    },
  },
};

// Retention constants in days
export const RETENTION_TRANSCRIPT_DAYS = 365;
export const RETENTION_RAW_ATTACHMENT_DAYS = 90;
export const RETENTION_METADATA_DAYS = 730;

// Helper: parse HH:MM format to minutes since midnight
function timeStringToMinutes(timeStr: string): number {
  const [hours, minutes] = timeStr.split(":").map(Number);
  return hours * 60 + minutes;
}

// Helper: create a date from Vietnam local time components (month is 0-indexed, 0=Jan, 11=Dec)
export function dateFromVietnamLocal(year: number, month: number, day: number, hours: number, minutes: number, seconds: number = 0): Date {
  const vietnamOffsetMs = 7 * 60 * 60 * 1000;
  // Create UTC date equivalent of Vietnam local time
  const utcDate = new Date(Date.UTC(year, month, day, hours, minutes, seconds));
  // Subtract the offset to get back to UTC
  return new Date(utcDate.getTime() - vietnamOffsetMs);
}

// Helper: get the local time in Asia/Ho_Chi_Minh (UTC+7, no DST)
// Returns a plain object with year, month (0-indexed), day, hours, minutes, seconds, day of week
export function getVietnamLocalTime(date: Date): {
  year: number;
  month: number; // 0-indexed (0=Jan, 11=Dec)
  day: number;
  hours: number;
  minutes: number;
  seconds: number;
  dayOfWeek: number; // 0=Sun, 1=Mon, ..., 6=Sat
} {
  // Use Intl.DateTimeFormat to convert UTC to Vietnam local time (Asia/Ho_Chi_Minh = UTC+7, no DST)
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Ho_Chi_Minh",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    weekday: "short",
  });

  const parts = formatter.formatToParts(date);
  const partMap: Record<string, string> = {};
  for (const part of parts) {
    partMap[part.type] = part.value;
  }

  const year = parseInt(partMap["year"], 10);
  const month = parseInt(partMap["month"], 10) - 1; // Convert to 0-indexed
  const day = parseInt(partMap["day"], 10);
  const hours = parseInt(partMap["hour"], 10);
  const minutes = parseInt(partMap["minute"], 10);
  const seconds = parseInt(partMap["second"], 10);

  // Map weekday name to number: Sun=0, Mon=1, ..., Sat=6
  const weekdayMap: Record<string, number> = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  const dayOfWeek = weekdayMap[partMap["weekday"]] ?? 0;

  return {
    year,
    month,
    day,
    hours,
    minutes,
    seconds,
    dayOfWeek,
  };
}

// Helper: check if a time is within business hours
function isWithinBusinessHours(local: ReturnType<typeof getVietnamLocalTime>, businessHours: { start: string; end: string }, weekdays: number[]): boolean {
  // Check if it's a business weekday
  if (!weekdays.includes(local.dayOfWeek)) {
    return false;
  }

  const startMinutes = timeStringToMinutes(businessHours.start);
  const endMinutes = timeStringToMinutes(businessHours.end);
  const currentMinutes = local.hours * 60 + local.minutes;

  return currentMinutes >= startMinutes && currentMinutes < endMinutes;
}

// Helper: add business minutes to a date
function addBusinessMinutes(
  startDate: Date,
  minutesToAdd: number,
  businessHours: { start: string; end: string },
  weekdays: number[]
): Date {
  let current = new Date(startDate);
  let remainingMinutes = minutesToAdd;

  const startMinutes = timeStringToMinutes(businessHours.start);
  const endMinutes = timeStringToMinutes(businessHours.end);
  const businessMinutesPerDay = endMinutes - startMinutes;

  while (remainingMinutes > 0) {
    const local = getVietnamLocalTime(current);
    const currentTimeMinutes = local.hours * 60 + local.minutes;

    // If we're outside business hours or not on a business day, move to next business hour
    if (!weekdays.includes(local.dayOfWeek) || currentTimeMinutes >= endMinutes) {
      // Move to next day start time
      if (local.dayOfWeek === 5) {
        // Friday -> skip to Monday
        current = dateFromVietnamLocal(local.year, local.month, local.day + 3, 8, 30, 0);
      } else if (local.dayOfWeek === 6) {
        // Saturday -> skip to Monday
        current = dateFromVietnamLocal(local.year, local.month, local.day + 2, 8, 30, 0);
      } else if (local.dayOfWeek === 0) {
        // Sunday -> skip to Monday
        current = dateFromVietnamLocal(local.year, local.month, local.day + 1, 8, 30, 0);
      } else {
        // Weekday but past business hours -> next day at start
        current = dateFromVietnamLocal(local.year, local.month, local.day + 1, 8, 30, 0);
      }
      continue;
    }

    if (currentTimeMinutes < startMinutes) {
      // Before business hours -> move to start
      current = dateFromVietnamLocal(local.year, local.month, local.day, 8, 30, 0);
      continue;
    }

    // We're within business hours
    const minutesUntilEndOfDay = endMinutes - currentTimeMinutes;
    if (remainingMinutes <= minutesUntilEndOfDay) {
      // Can finish today
      current = new Date(current.getTime() + remainingMinutes * 60 * 1000);
      remainingMinutes = 0;
    } else {
      // Fill rest of day and continue tomorrow
      remainingMinutes -= minutesUntilEndOfDay;
      current = dateFromVietnamLocal(local.year, local.month, local.day + 1, 8, 30, 0);
    }
  }

  return current;
}

export interface SlaSnapshot {
  version: number;
  tier: string;
  firstResponseDueAt: Date;
  resolutionDueAt: Date;
  warningAtPercent: number;
  outOfHoursMode: string;
  routeKey: string | null;
}

export function resolveTier(
  inbox: { defaultTier?: string },
  params: { tier?: string }
): "standard" | "priority" | "vip" {
  const tier = params.tier ?? inbox.defaultTier ?? "standard";

  if (!["standard", "priority", "vip"].includes(tier)) {
    throw APIError.invalidArgument(`invalid tier: ${tier}, must be one of standard, priority, vip`);
  }

  return tier as "standard" | "priority" | "vip";
}

export function computeSlaSnapshot(
  slaPolicy: typeof SLA_POLICY_SEED,
  tier: "standard" | "priority" | "vip",
  openedAt: Date
): SlaSnapshot {
  const tierPolicy = slaPolicy.tiers[tier];
  if (!tierPolicy) {
    throw APIError.invalidArgument(`unknown tier: ${tier}`);
  }

  let firstResponseDueAt: Date;
  let resolutionDueAt: Date;

  const clockType = tierPolicy.clock as string;

  if (clockType === "calendar") {
    // Direct addition of minutes
    firstResponseDueAt = new Date(openedAt.getTime() + tierPolicy.first_response_minutes * 60 * 1000);
    resolutionDueAt = new Date(openedAt.getTime() + tierPolicy.resolution_minutes * 60 * 1000);
  } else if (clockType === "business") {
    // Business clock: only count business hours
    // TODO: holidays aren't loaded in P0 - implement holiday calendar lookup when available
    firstResponseDueAt = addBusinessMinutes(
      openedAt,
      tierPolicy.first_response_minutes,
      slaPolicy.business_calendar.hours,
      slaPolicy.business_calendar.weekdays
    );
    resolutionDueAt = addBusinessMinutes(
      openedAt,
      tierPolicy.resolution_minutes,
      slaPolicy.business_calendar.hours,
      slaPolicy.business_calendar.weekdays
    );
  } else {
    throw APIError.invalidArgument(`unknown clock type: ${clockType}`);
  }

  const outOfHoursMode = tierPolicy.out_of_hours?.mode ?? "pause";
  let routeKey: string | null = null;

  if (outOfHoursMode === "on_call") {
    const outOfHours = tierPolicy.out_of_hours as any;
    if (outOfHours?.route_key) {
      routeKey = outOfHours.route_key;
    }
  }

  return {
    version: slaPolicy.version,
    tier,
    firstResponseDueAt,
    resolutionDueAt,
    warningAtPercent: tierPolicy.warning_at_percent,
    outOfHoursMode,
    routeKey,
  };
}

export function snapshotThreadSla(
  threadValues: { workspaceId: bigint },
  slaPolicy: typeof SLA_POLICY_SEED,
  tier: "standard" | "priority" | "vip",
  openedAt: Date
): {
  tier: string;
  slaPolicyVersion: number;
  slaSnapshot: SlaSnapshot;
  firstResponseDueAt: Date;
  resolutionDueAt: Date;
  escalationRouteKey: string | null;
} {
  const snapshot = computeSlaSnapshot(slaPolicy, tier, openedAt);

  return {
    tier: snapshot.tier,
    slaPolicyVersion: snapshot.version,
    slaSnapshot: snapshot,
    firstResponseDueAt: snapshot.firstResponseDueAt,
    resolutionDueAt: snapshot.resolutionDueAt,
    escalationRouteKey: snapshot.routeKey,
  };
}

import { APIError } from "encore.dev/api";

// Bảng field hợp lệ cho từng chiều onboarding — nguồn sự thật duy nhất cho payload
// `POST /operations/onboard/dimensions/:dimension`. apps/cosa giữ bảng tương ứng ở
// `apps/cosa/workflows/onboarding_dimensions.py`; tests/contracts/
// test_startup_os_dimension_fields.py đối chiếu hai bên (lệch ⇒ dữ liệu agent gửi
// bị bỏ âm thầm, đúng lỗi đã xảy ra khi workflow gửi `arr`/`burn_rate_weekly`).
//
// Kiểu field:
// - string / integer / number / boolean: giá trị đơn, cho phép null.
// - string_array: mảng chuỗi.
// - value_list: mảng chuỗi hoặc { valueText, isFireWorthy?, realityStatus? }.
// - competitor_list: mảng { name, whyWinning?, threatLevel? }.
export type OnboardFieldType =
  | "string"
  | "integer"
  | "number"
  | "boolean"
  | "string_array"
  | "value_list"
  | "competitor_list";

export const ONBOARD_DIMENSION_FIELDS = {
  identity: {
    whatTheyDo: "string",
    whoTheyServe: "string",
    foundingWhy: "string",
    oneSentencePitch: "string",
    values: "value_list",
    notCaptured: "string_array",
  },
  stage_scale: {
    headcountFt: "integer",
    headcountContractor: "integer",
    revenueArr: "number",
    revenueCurrency: "string",
    runwayMonths: "number",
    stage: "string",
    whatBrokeLast90d: "string",
    notCaptured: "string_array",
  },
  founder: {
    founderName: "string",
    role: "string",
    superpower: "string",
    blindSpots: "string",
    archetype: "string",
    whatKeepsUp: "string",
    cofounderCritique: "string",
    notCaptured: "string_array",
  },
  team_culture: {
    threeWords: "string_array",
    lastRealConflict: "string",
    conflictResolution: "string",
    strongestLeader: "string",
    weakestLeader: "string",
    hasRealConflict: "boolean",
    notCaptured: "string_array",
  },
  market: {
    marketDescription: "string",
    unfairAdvantage: "string",
    competitiveThreat: "string",
    hasRealCompetition: "boolean",
    competitors: "competitor_list",
    notCaptured: "string_array",
  },
  challenges: {
    priorityProduct: "integer",
    priorityGrowth: "integer",
    priorityPeople: "integer",
    priorityMoney: "integer",
    priorityOperations: "integer",
    avoidedDecision: "string",
    extraDayAnswer: "string",
    notCaptured: "string_array",
  },
  goals_ambition: {
    goal12MonthsText: "string",
    goal36MonthsText: "string",
    exitOrientation: "string",
    personalSuccessDefinition: "string",
    notCaptured: "string_array",
  },
} as const satisfies Record<string, Record<string, OnboardFieldType>>;

export type OnboardDimension = keyof typeof ONBOARD_DIMENSION_FIELDS;

// Giá trị enum lưu dạng text trong DB (xem comment schema onboard.ts).
const ENUM_VALUES: Partial<Record<string, readonly string[]>> = {
  stage: ["pre_pmf", "scaling", "optimizing"],
  archetype: ["product", "sales", "technical", "operator", "hybrid"],
  exitOrientation: ["exit", "build_forever", "undecided"],
};

const PRIORITY_FIELDS = new Set([
  "priorityProduct",
  "priorityGrowth",
  "priorityPeople",
  "priorityMoney",
  "priorityOperations",
]);

export function isOnboardDimension(value: string): value is OnboardDimension {
  return Object.prototype.hasOwnProperty.call(ONBOARD_DIMENSION_FIELDS, value);
}

function fail(dimension: string, field: string, reason: string): never {
  throw APIError.invalidArgument(`onboard dimension '${dimension}' field '${field}': ${reason}`);
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function checkField(dimension: string, field: string, type: OnboardFieldType, value: unknown): void {
  if (value === null || value === undefined) return;
  switch (type) {
    case "string":
      if (typeof value !== "string") fail(dimension, field, "must be a string");
      {
        const allowed = ENUM_VALUES[field];
        if (allowed && !allowed.includes(value)) {
          fail(dimension, field, `must be one of ${allowed.join(", ")}`);
        }
      }
      return;
    case "integer":
      if (typeof value !== "number" || !Number.isInteger(value)) fail(dimension, field, "must be an integer");
      if (PRIORITY_FIELDS.has(field) && (value < 1 || value > 5)) fail(dimension, field, "must be between 1 and 5");
      if (value < 0) fail(dimension, field, "must not be negative");
      return;
    case "number":
      if (typeof value !== "number" || !Number.isFinite(value)) fail(dimension, field, "must be a finite number");
      if (value < 0) fail(dimension, field, "must not be negative");
      return;
    case "boolean":
      if (typeof value !== "boolean") fail(dimension, field, "must be a boolean");
      return;
    case "string_array":
      if (!Array.isArray(value) || value.some((v) => typeof v !== "string")) {
        fail(dimension, field, "must be an array of strings");
      }
      return;
    case "value_list":
      if (!Array.isArray(value)) fail(dimension, field, "must be an array");
      for (const item of value) {
        if (typeof item === "string") continue;
        if (!isPlainObject(item) || typeof item.valueText !== "string" || item.valueText.trim() === "") {
          fail(dimension, field, "each item must be a string or { valueText }");
        }
        if (item.isFireWorthy !== undefined && typeof item.isFireWorthy !== "boolean") {
          fail(dimension, field, "isFireWorthy must be a boolean");
        }
        if (
          item.realityStatus !== undefined &&
          !["real", "poster", "unclear"].includes(String(item.realityStatus))
        ) {
          fail(dimension, field, "realityStatus must be one of real, poster, unclear");
        }
      }
      return;
    case "competitor_list":
      if (!Array.isArray(value)) fail(dimension, field, "must be an array");
      for (const item of value) {
        if (!isPlainObject(item) || typeof item.name !== "string" || item.name.trim() === "") {
          fail(dimension, field, "each competitor must be { name }");
        }
        if (item.whyWinning !== undefined && typeof item.whyWinning !== "string") {
          fail(dimension, field, "whyWinning must be a string");
        }
        if (
          item.threatLevel !== undefined &&
          !["low", "medium", "high"].includes(String(item.threatLevel))
        ) {
          fail(dimension, field, "threatLevel must be one of low, medium, high");
        }
      }
      return;
  }
}

/**
 * Kiểm payload 1 chiều trước khi ghi. Field lạ bị từ chối (không bỏ âm thầm) để
 * lệch hợp đồng giữa client/agent và Company lộ ra ngay tại request.
 */
export function validateOnboardDimensionData(
  dimension: string,
  data: unknown
): { dimension: OnboardDimension; data: Record<string, unknown> } {
  if (!isOnboardDimension(dimension)) {
    throw APIError.invalidArgument(`Chiều onboarding không hợp lệ: ${dimension}`);
  }
  if (!isPlainObject(data)) {
    throw APIError.invalidArgument(`onboard dimension '${dimension}': data must be an object`);
  }
  const fields: Record<string, OnboardFieldType> = ONBOARD_DIMENSION_FIELDS[dimension];
  const unknown = Object.keys(data).filter((key) => !(key in fields));
  if (unknown.length > 0) {
    throw APIError.invalidArgument(
      `onboard dimension '${dimension}': unknown field(s) ${unknown.join(", ")}; ` +
        `allowed: ${Object.keys(fields).join(", ")}`
    );
  }
  for (const [field, type] of Object.entries(fields)) {
    checkField(dimension, field, type, data[field]);
  }
  const captured = Object.keys(fields).filter(
    (field) => field !== "notCaptured" && data[field] !== undefined && data[field] !== null
  );
  if (captured.length === 0) {
    throw APIError.invalidArgument(`onboard dimension '${dimension}': at least one field must be provided`);
  }
  if (dimension === "founder" && (typeof data.founderName !== "string" || data.founderName.trim() === "")) {
    fail(dimension, "founderName", "is required");
  }
  return { dimension, data };
}

// M2 §2 / ADR-ID-MODEL-001 — Snowflake SpineId generator (control-plane authoritative).
//
// Bit layout v1 (63-bit, fit BIGINT signed):
//   | 41 bit ms từ COSA epoch | 1 bit reserved(=0) | 10 bit slot | 12 bit sequence |
//
// Slot KHÔNG còn là `Math.random()*1024` — nó do snowflake-registry cấp qua
// lease + fencing. Process authoritative phải gọi `configureGeneratorSlot()` sau
// khi acquire slot; nếu chưa cấu hình ở staging/prod ⇒ ném lỗi (fail-closed).

import { isStagingOrProd } from "../shared/env";

export const COSA_SNOWFLAKE_EPOCH_MS = 1704067200000n; // 2024-01-01T00:00:00Z
export const SNOWFLAKE_LAYOUT_VERSION = 1;

const TIMESTAMP_SHIFT = 23n; // 1 reserved + 10 slot + 12 seq
const SLOT_SHIFT = 12n;
const MAX_SEQUENCE = 4095n;
const MAX_SLOT = 1023;
// Ngân sách drift cho virtual-clock khi phát hiện đồng hồ lùi (ms).
const CLOCK_DRIFT_BUDGET_MS = 5000;

let configuredSlot: bigint | null = null;
let sequence = 0n;
let lastTimestamp = -1n;

function isTestOrDev(): boolean {
  const env = (process.env.NODE_ENV || "").toLowerCase();
  return env === "test" || env === "development" || env === "dev" || env === "";
}

/** Gọi sau khi acquire slot từ snowflake-registry. `slot` ∈ [0, 1023]. */
export function configureGeneratorSlot(slot: number): void {
  if (!Number.isInteger(slot) || slot < 0 || slot > MAX_SLOT) {
    throw new Error(`Snowflake slot không hợp lệ: ${slot}`);
  }
  configuredSlot = BigInt(slot);
}

/** Dùng trong test để reset về trạng thái chưa cấu hình. */
export function __resetGeneratorForTest(): void {
  configuredSlot = null;
  sequence = 0n;
  lastTimestamp = -1n;
}

function resolveSlot(): bigint {
  if (configuredSlot !== null) return configuredSlot;
  if (isTestOrDev()) {
    const raw = process.env.COSA_SNOWFLAKE_TEST_SLOT;
    const parsed = raw !== undefined ? Number(raw) : 0;
    return BigInt(Number.isInteger(parsed) && parsed >= 0 && parsed <= MAX_SLOT ? parsed : 0);
  }
  if (isStagingOrProd()) {
    throw new Error(
      "Snowflake generator chưa được cấp slot (configureGeneratorSlot chưa gọi) — từ chối sinh ID"
    );
  }
  return 0n;
}

export function generateSnowflake(): bigint {
  let timestamp = BigInt(Date.now());

  if (timestamp < lastTimestamp) {
    // Đồng hồ lùi: virtual-clock advance trong drift budget, KHÔNG phát ID lùi.
    if (lastTimestamp - timestamp > BigInt(CLOCK_DRIFT_BUDGET_MS)) {
      throw new Error(
        `Đồng hồ lùi ${lastTimestamp - timestamp}ms vượt drift budget ${CLOCK_DRIFT_BUDGET_MS}ms`
      );
    }
    timestamp = lastTimestamp;
  }

  if (timestamp === lastTimestamp) {
    sequence = (sequence + 1n) & MAX_SEQUENCE;
    if (sequence === 0n) {
      // Sequence exhaustion trong 1ms ⇒ spin sang ms kế.
      let next = BigInt(Date.now());
      while (next <= lastTimestamp) next = BigInt(Date.now());
      timestamp = next;
    }
  } else {
    sequence = 0n;
  }

  lastTimestamp = timestamp;

  return (
    ((timestamp - COSA_SNOWFLAKE_EPOCH_MS) << TIMESTAMP_SHIFT) |
    (resolveSlot() << SLOT_SHIFT) |
    sequence
  );
}

export function generateSnowflakeStr(): string {
  return generateSnowflake().toString();
}

/** Bóc slot + timestamp từ một Snowflake (dùng cho test / debug). */
export function decodeSnowflake(id: bigint): { timestampMs: bigint; slot: number; sequence: number } {
  return {
    timestampMs: (id >> TIMESTAMP_SHIFT) + COSA_SNOWFLAKE_EPOCH_MS,
    slot: Number((id >> SLOT_SHIFT) & 1023n),
    sequence: Number(id & MAX_SEQUENCE),
  };
}

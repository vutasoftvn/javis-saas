// M2 §2 / ADR-ID-MODEL-001 — Snowflake ID cho `services/company`.
//
// Guardrail 6: KHÔNG random node ID cho production. `NODE_ID = Math.random()*1024`
// đã bị bỏ — slot lấy từ env `COMPANY_SNOWFLAKE_SLOT` (0..1023). Ở staging/prod
// thiếu env ⇒ ném lỗi (fail-closed); test/dev mặc định slot 0.
//
// Bit layout v1 (63-bit, fit BIGINT signed) — đồng bộ services/cosa:
//   | 41 bit ms từ COSA epoch | 1 bit reserved(=0) | 10 bit slot | 12 bit sequence |
//
// LƯU Ý (M2 §2 còn lại): các entity SpineId (workspace/project/legal_entity/
// workforce_member/sop_definition + lifecycle/approval record) rồi sẽ được mint
// qua RPC control-plane `mintSpineId`; hàm này chỉ còn dùng cho các record local
// còn lại tới khi call-site được chuyển. `generateSnowflake()` giữ chữ ký đồng bộ.
import { isStagingOrProd } from "../env";

export const COSA_SNOWFLAKE_EPOCH_MS = 1704067200000n; // 2024-01-01T00:00:00Z
export const SNOWFLAKE_LAYOUT_VERSION = 1;

const TIMESTAMP_SHIFT = 23n; // 1 reserved + 10 slot + 12 seq
const SLOT_SHIFT = 12n;
const MAX_SEQUENCE = 4095n;
const MAX_SLOT = 1023;
const CLOCK_DRIFT_BUDGET_MS = 5000;

let sequence = 0n;
let lastTimestamp = -1n;
let resolvedSlot: bigint | null = null;

function resolveSlot(): bigint {
  if (resolvedSlot !== null) return resolvedSlot;
  const raw = process.env.COMPANY_SNOWFLAKE_SLOT;
  if (raw !== undefined && raw !== "") {
    const n = Number(raw);
    if (!Number.isInteger(n) || n < 0 || n > MAX_SLOT) {
      throw new Error(`COMPANY_SNOWFLAKE_SLOT không hợp lệ: ${raw} (cần 0..1023)`);
    }
    resolvedSlot = BigInt(n);
    return resolvedSlot;
  }
  if (isStagingOrProd()) {
    throw new Error(
      "COMPANY_SNOWFLAKE_SLOT phải được set (0..1023) ở staging/production — không random node ID"
    );
  }
  resolvedSlot = 0n; // test/dev
  return resolvedSlot;
}

export function generateSnowflake(): bigint {
  let timestamp = BigInt(Date.now());

  if (timestamp < lastTimestamp) {
    if (lastTimestamp - timestamp > BigInt(CLOCK_DRIFT_BUDGET_MS)) {
      throw new Error(
        `Đồng hồ lùi ${lastTimestamp - timestamp}ms vượt drift budget ${CLOCK_DRIFT_BUDGET_MS}ms`
      );
    }
    timestamp = lastTimestamp; // virtual-clock: không phát ID lùi
  }

  if (timestamp === lastTimestamp) {
    sequence = (sequence + 1n) & MAX_SEQUENCE;
    if (sequence === 0n) {
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

/** Bóc slot + timestamp (test / debug). */
export function decodeSnowflake(id: bigint): { timestampMs: bigint; slot: number; sequence: number } {
  return {
    timestampMs: (id >> TIMESTAMP_SHIFT) + COSA_SNOWFLAKE_EPOCH_MS,
    slot: Number((id >> SLOT_SHIFT) & 1023n),
    sequence: Number(id & MAX_SEQUENCE),
  };
}

/** Reset trạng thái module (test). */
export function __resetSnowflakeForTest(): void {
  sequence = 0n;
  lastTimestamp = -1n;
  resolvedSlot = null;
}

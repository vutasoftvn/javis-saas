import { Pool } from "pg";
import { assertDurableAdapterConfigured } from "./early-access-store";

export interface RateLimiter {
  consume(
    key: string,
    limit: number,
    windowSeconds: number
  ): Promise<{ allowed: boolean; retryAfterSeconds: number }>;
}

/**
 * Adapter in-memory — CHỈ dùng cho test/dev. Bộ đếm không chia sẻ giữa nhiều
 * instance/worker và mất khi restart, nên KHÔNG được coi là rate limit thật
 * ở production (một attacker chỉ cần request rơi vào instance khác là vượt
 * qua giới hạn hoàn toàn).
 */
export class InMemoryRateLimiter implements RateLimiter {
  private readonly counters = new Map<string, { windowStart: number; count: number }>();

  async consume(
    key: string,
    limit: number,
    windowSeconds: number
  ): Promise<{ allowed: boolean; retryAfterSeconds: number }> {
    const nowSeconds = Math.floor(Date.now() / 1000);
    const windowStart = Math.floor(nowSeconds / windowSeconds) * windowSeconds;
    const existing = this.counters.get(key);

    let count: number;
    if (existing && existing.windowStart === windowStart) {
      existing.count += 1;
      count = existing.count;
    } else {
      count = 1;
      this.counters.set(key, { windowStart, count });
    }

    const allowed = count <= limit;
    const retryAfterSeconds = allowed ? 0 : windowStart + windowSeconds - nowSeconds;
    return { allowed, retryAfterSeconds };
  }
}

// Migration-on-boot: bảng đếm dùng cửa sổ cố định (fixed window) theo
// (key, window_start) — đơn giản, đủ chính xác cho quy mô đăng ký early
// access, tránh cần thư viện rate-limit ngoài hay hạ tầng trả phí (Upstash/
// Vercel KV) mà đề bài yêu cầu tránh.
const CREATE_RATE_LIMIT_TABLE_SQL = `
CREATE TABLE IF NOT EXISTS early_access_rate_limit_counters (
  key TEXT NOT NULL,
  window_start BIGINT NOT NULL,
  count INTEGER NOT NULL,
  PRIMARY KEY (key, window_start)
);
`;

/**
 * Adapter Postgres — durable, dùng chung giữa các instance/worker ở
 * production. Dùng UPSERT nguyên tử (ON CONFLICT ... DO UPDATE ... RETURNING)
 * để tăng bộ đếm mà không có race condition giữa các request đồng thời.
 */
export class PostgresRateLimiter implements RateLimiter {
  private readonly pool: Pool;
  private schemaReady: Promise<void> | null = null;

  constructor(connectionString: string) {
    this.pool = new Pool({ connectionString });
  }

  private ensureSchema(): Promise<void> {
    if (!this.schemaReady) {
      this.schemaReady = this.pool.query(CREATE_RATE_LIMIT_TABLE_SQL).then(() => undefined);
    }
    return this.schemaReady;
  }

  async consume(
    key: string,
    limit: number,
    windowSeconds: number
  ): Promise<{ allowed: boolean; retryAfterSeconds: number }> {
    await this.ensureSchema();
    const nowSeconds = Math.floor(Date.now() / 1000);
    const windowStart = Math.floor(nowSeconds / windowSeconds) * windowSeconds;

    const result = await this.pool.query<{ count: number }>(
      `INSERT INTO early_access_rate_limit_counters (key, window_start, count)
       VALUES ($1, $2, 1)
       ON CONFLICT (key, window_start) DO UPDATE
         SET count = early_access_rate_limit_counters.count + 1
       RETURNING count`,
      [key, windowStart]
    );
    const count = Number(result.rows[0]?.count ?? 1);

    // Dọn dẹp cơ hội (best-effort): xoá cửa sổ đã hết hạn từ lâu để bảng
    // không phình vô hạn — không quan trọng nếu lệnh này thất bại, không
    // ảnh hưởng tới tính đúng đắn của rate limit hiện tại.
    void this.pool
      .query(`DELETE FROM early_access_rate_limit_counters WHERE window_start < $1`, [
        windowStart - windowSeconds * 2,
      ])
      .catch(() => undefined);

    const allowed = count <= limit;
    const retryAfterSeconds = allowed ? 0 : windowStart + windowSeconds - nowSeconds;
    return { allowed, retryAfterSeconds };
  }
}

export function createRateLimiter(): RateLimiter {
  const databaseUrl = process.env.DATABASE_URL;
  if (databaseUrl) {
    return new PostgresRateLimiter(databaseUrl);
  }
  if (process.env.NODE_ENV === "production") {
    assertDurableAdapterConfigured(databaseUrl);
  }
  return new InMemoryRateLimiter();
}

// Khởi tạo LAZY — xem giải thích chi tiết ở early-access-store.ts (tránh
// throw ngay lúc `next build` import module để thu thập page data, chỉ throw
// đúng lúc request thật đầu tiên gọi tới nếu thiếu DATABASE_URL).
let cachedLimiter: RateLimiter | null = null;
function getEarlyAccessRateLimiter(): RateLimiter {
  if (!cachedLimiter) {
    cachedLimiter = createRateLimiter();
  }
  return cachedLimiter;
}

export const earlyAccessRateLimiter: RateLimiter = {
  consume: (key, limit, windowSeconds) => getEarlyAccessRateLimiter().consume(key, limit, windowSeconds),
};

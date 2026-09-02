import { Pool } from "pg";

// Dùng chung một Pool cho mỗi connection string thay vì mỗi adapter
// (EarlyAccessStore và RateLimiter) tự mở Pool riêng — tránh nhân đôi số kết
// nối/pool tới cùng một database khi cả hai adapter cùng trỏ tới
// DATABASE_URL giống nhau.
const poolsByConnectionString = new Map<string, Pool>();
export function getSharedPgPool(connectionString: string): Pool {
  let pool = poolsByConnectionString.get(connectionString);
  if (!pool) {
    pool = new Pool({ connectionString });
    poolsByConnectionString.set(connectionString, pool);
  }
  return pool;
}

/**
 * PRIVACY OPERATIONS — Early Access registrations
 *
 * Dữ liệu lưu trữ: chỉ các trường form cần thiết để xử lý đăng ký Early
 * Access (fullName, email, phone, company, role, teamSize, priorityInterest,
 * note, accessCode, trạng thái gửi email, thời điểm đăng ký). Không thu thập
 * thêm trường nào ngoài những gì form yêu cầu.
 *
 * Retention (thời hạn lưu trữ): mặc định 365 ngày kể từ registered_at (cấu
 * hình qua biến môi trường EARLY_ACCESS_RETENTION_DAYS trong .env.example).
 * Đây là quy trình MANUAL/documented-only ở giai đoạn hiện tại — CHƯA có
 * pipeline xoá tự động; vận hành viên chịu trách nhiệm định kỳ chạy truy vấn
 * dọn dẹp thủ công, ví dụ:
 *   DELETE FROM early_access_registrations
 *   WHERE registered_at < now() - interval '365 days';
 *
 * Erasure process (quy trình xoá theo yêu cầu chủ thể dữ liệu): khi nhận yêu
 * cầu xoá dữ liệu (qua email/kênh liên hệ công khai của COSA OS), vận hành
 * viên xác minh danh tính người yêu cầu qua email đã đăng ký, sau đó chạy:
 *   DELETE FROM early_access_registrations WHERE email = $1;
 * trực tiếp trên database Postgres của landing (KHÔNG phải database
 * services/company hay services/cosa). Không có bản sao lưu (backup) nào
 * khác cần xoá thêm ở phạm vi tính năng này (chỉ 1 bảng, 1 database).
 *
 * accessCode CHỈ là mã tham chiếu đăng ký hiển thị cho người dùng để đối
 * chiếu, KHÔNG phải authorization credential — không dùng giá trị này để cấp
 * quyền truy cập bất kỳ tài nguyên nào.
 */

// Trạng thái gửi email xác nhận của một bản ghi đăng ký early access.
// - pending: đã lưu bền vững, chưa gửi/chưa xác nhận queue thành công.
// - sending: đã CLAIM quyền gửi (qua claimEmailAttempt) và đang gọi provider
//   — trạng thái tạm thời, ngăn 1 request thứ hai đồng thời cũng claim và
//   gửi trùng email cho cùng một bản ghi (xem claimEmailAttempt()).
// - queued: nhà cung cấp email (Resend) đã trả về providerMessageId thật.
// - simulated: môi trường dev/chưa cấu hình RESEND_API_KEY — không có email
//   thật nào được gửi, nhưng bản ghi vẫn được lưu bền vững.
// - failed: đã thử gửi nhưng nhà cung cấp báo lỗi.
export type EmailDeliveryStatus = "pending" | "sending" | "queued" | "simulated" | "failed";

export interface NewEarlyAccessRegistration {
  fullName: string;
  email: string;
  phone: string;
  company: string;
  role?: string;
  teamSize?: string;
  priorityInterest: string;
  note?: string;
  // Mã tham chiếu đăng ký (sinh bằng crypto.randomUUID() ở route handler) —
  // CHỈ dùng để người dùng tra cứu/đối chiếu đăng ký của họ, KHÔNG phải
  // credential cấp quyền truy cập hệ thống. Không dùng giá trị này ở bất kỳ
  // đâu để authorization.
  accessCode: string;
  emailDeliveryStatus: EmailDeliveryStatus;
}

export interface EarlyAccessRegistration extends NewEarlyAccessRegistration {
  id: string;
  registeredAt: string; // ISO 8601
  emailProviderMessageId?: string;
}

export interface EarlyAccessStore {
  findByEmail(email: string): Promise<EarlyAccessRegistration | null>;
  create(input: NewEarlyAccessRegistration): Promise<EarlyAccessRegistration>;
  markEmailQueued(id: string, providerMessageId: string): Promise<void>;
  // Đánh dấu "failed" khi lần gửi (đầu tiên hoặc retry ở nhánh duplicate)
  // thất bại — bắt buộc để route handler KHÔNG bao giờ trả success: true
  // cho một bản ghi mà email xác nhận chưa từng được gửi thành công (nếu
  // không có method này, trạng thái "failed" trong EmailDeliveryStatus sẽ
  // không bao giờ được ghi, và lần đăng ký lại sau đó sẽ đọc "pending" mãi
  // mãi mà không biết cần thử gửi lại).
  markEmailFailed(id: string): Promise<void>;
  // Đánh dấu "simulated" khi một lần RETRY (nhánh duplicate pending/failed)
  // phát hiện môi trường đã chuyển sang simulated (RESEND_API_KEY bị gỡ
  // giữa chừng) — nếu không cập nhật, bản ghi kẹt ở "pending"/"failed" mãi
  // mãi và mọi lần resubmit sau đó sẽ lại thử retry vô ích.
  markEmailSimulated(id: string): Promise<void>;
  // Chuyển nguyên tử "pending"/"failed" -> "sending" và trả về true CHỈ KHI
  // request này là request đầu tiên giành được quyền gửi lại. Một request
  // đồng thời khác gọi hàm này trên cùng id sẽ nhận về false (bản ghi không
  // còn ở "pending"/"failed" nữa) và KHÔNG được phép gọi sendEarlyAccessEmails
  // — đây là cơ chế chống gửi trùng nhiều email xác nhận cho cùng một người
  // dùng khi có 2+ request gần như đồng thời cho cùng email (double-click,
  // retry storm...). Tương tự vai trò UNIQUE + upsert của create() bảo vệ
  // race condition ở nhánh đăng ký mới.
  claimEmailAttempt(id: string): Promise<boolean>;
}

/**
 * Adapter in-memory — CHỈ dùng cho test/dev. Dữ liệu mất khi tiến trình khởi
 * động lại và không được chia sẻ giữa nhiều instance/worker, vì vậy tuyệt đối
 * không được dùng ở production (xem createEarlyAccessStore()).
 */
export class InMemoryEarlyAccessStore implements EarlyAccessStore {
  private readonly byEmail = new Map<string, EarlyAccessRegistration>();
  private sequence = 0;

  async findByEmail(email: string): Promise<EarlyAccessRegistration | null> {
    return this.byEmail.get(email) ?? null;
  }

  async create(input: NewEarlyAccessRegistration): Promise<EarlyAccessRegistration> {
    this.sequence += 1;
    const registration: EarlyAccessRegistration = {
      ...input,
      id: `mem-${this.sequence}`,
      registeredAt: new Date().toISOString(),
    };
    this.byEmail.set(input.email, registration);
    return registration;
  }

  async markEmailQueued(id: string, providerMessageId: string): Promise<void> {
    for (const registration of this.byEmail.values()) {
      if (registration.id === id) {
        registration.emailDeliveryStatus = "queued";
        registration.emailProviderMessageId = providerMessageId;
        return;
      }
    }
  }

  async markEmailFailed(id: string): Promise<void> {
    for (const registration of this.byEmail.values()) {
      if (registration.id === id) {
        registration.emailDeliveryStatus = "failed";
        return;
      }
    }
  }

  async markEmailSimulated(id: string): Promise<void> {
    for (const registration of this.byEmail.values()) {
      if (registration.id === id) {
        registration.emailDeliveryStatus = "simulated";
        return;
      }
    }
  }

  async claimEmailAttempt(id: string): Promise<boolean> {
    // JS đơn luồng nên không có race condition thật giữa 2 lệnh gọi đồng bộ
    // này, nhưng vẫn implement đúng ngữ nghĩa "chỉ 1 request được claim" để
    // hành vi nhất quán với PostgresEarlyAccessStore và test được ở cả hai
    // adapter cùng một cách.
    for (const registration of this.byEmail.values()) {
      if (registration.id === id) {
        if (registration.emailDeliveryStatus === "pending" || registration.emailDeliveryStatus === "failed") {
          registration.emailDeliveryStatus = "sending";
          return true;
        }
        return false;
      }
    }
    return false;
  }
}

// Tự tạo schema khi khởi động (migration-on-boot) — app landing là Next.js
// độc lập, chưa có tooling migration riêng, nên dùng CREATE TABLE IF NOT
// EXISTS đơn giản, an toàn để chạy lại nhiều lần (idempotent) thay vì bắt
// buộc vận hành viên áp file .sql thủ công.
const CREATE_REGISTRATIONS_TABLE_SQL = `
CREATE TABLE IF NOT EXISTS early_access_registrations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL UNIQUE,
  full_name TEXT NOT NULL,
  phone TEXT NOT NULL,
  company TEXT NOT NULL,
  role TEXT,
  team_size TEXT,
  priority_interest TEXT NOT NULL,
  note TEXT,
  access_code TEXT NOT NULL,
  email_delivery_status TEXT NOT NULL,
  email_provider_message_id TEXT,
  registered_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
`;

/**
 * Adapter Postgres — durable, dùng chung giữa các instance/worker ở
 * production. Kết nối tới database riêng của landing (DATABASE_URL), KHÔNG
 * chia sẻ schema với services/company hay services/cosa (những service đó
 * dùng Encore/Drizzle quản lý migration riêng).
 */
export class PostgresEarlyAccessStore implements EarlyAccessStore {
  private readonly pool: Pool;
  private schemaReady: Promise<void> | null = null;

  constructor(connectionString: string) {
    this.pool = getSharedPgPool(connectionString);
  }

  private ensureSchema(): Promise<void> {
    if (!this.schemaReady) {
      this.schemaReady = this.pool.query(CREATE_REGISTRATIONS_TABLE_SQL).then(() => undefined);
    }
    return this.schemaReady;
  }

  async findByEmail(email: string): Promise<EarlyAccessRegistration | null> {
    await this.ensureSchema();
    const result = await this.pool.query(
      `SELECT id, email, full_name, phone, company, role, team_size, priority_interest, note,
              access_code, email_delivery_status, email_provider_message_id, registered_at
       FROM early_access_registrations WHERE email = $1`,
      [email]
    );
    const row = result.rows[0];
    return row ? mapRow(row) : null;
  }

  async create(input: NewEarlyAccessRegistration): Promise<EarlyAccessRegistration> {
    await this.ensureSchema();
    const result = await this.pool.query(
      `INSERT INTO early_access_registrations
         (email, full_name, phone, company, role, team_size, priority_interest, note, access_code, email_delivery_status)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
       ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
       RETURNING id, email, full_name, phone, company, role, team_size, priority_interest, note,
                 access_code, email_delivery_status, email_provider_message_id, registered_at`,
      [
        input.email,
        input.fullName,
        input.phone,
        input.company,
        input.role ?? null,
        input.teamSize ?? null,
        input.priorityInterest,
        input.note ?? null,
        input.accessCode,
        input.emailDeliveryStatus,
      ]
    );
    return mapRow(result.rows[0]);
  }

  async markEmailQueued(id: string, providerMessageId: string): Promise<void> {
    await this.ensureSchema();
    await this.pool.query(
      `UPDATE early_access_registrations
       SET email_delivery_status = 'queued', email_provider_message_id = $2
       WHERE id = $1`,
      [id, providerMessageId]
    );
  }

  async markEmailFailed(id: string): Promise<void> {
    await this.ensureSchema();
    await this.pool.query(
      `UPDATE early_access_registrations SET email_delivery_status = 'failed' WHERE id = $1`,
      [id]
    );
  }

  async markEmailSimulated(id: string): Promise<void> {
    await this.ensureSchema();
    await this.pool.query(
      `UPDATE early_access_registrations SET email_delivery_status = 'simulated' WHERE id = $1`,
      [id]
    );
  }

  async claimEmailAttempt(id: string): Promise<boolean> {
    await this.ensureSchema();
    // UPDATE có điều kiện (optimistic lock) trên chính điều kiện trạng thái
    // hiện tại — Postgres đảm bảo tính nguyên tử cho một câu UPDATE đơn lẻ,
    // nên khi 2 request đồng thời cùng chạy câu này trên cùng id, CHỈ MỘT
    // trong số đó khớp điều kiện WHERE (request thắng sẽ đổi trạng thái
    // trước khi request thua đọc được), request còn lại nhận 0 dòng bị ảnh
    // hưởng và biết mình không được phép gửi.
    const result = await this.pool.query(
      `UPDATE early_access_registrations
       SET email_delivery_status = 'sending'
       WHERE id = $1 AND email_delivery_status IN ('pending', 'failed')
       RETURNING id`,
      [id]
    );
    return (result.rowCount ?? 0) > 0;
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapRow(row: any): EarlyAccessRegistration {
  return {
    id: row.id,
    email: row.email,
    fullName: row.full_name,
    phone: row.phone,
    company: row.company,
    role: row.role ?? undefined,
    teamSize: row.team_size ?? undefined,
    priorityInterest: row.priority_interest,
    note: row.note ?? undefined,
    accessCode: row.access_code,
    emailDeliveryStatus: row.email_delivery_status,
    emailProviderMessageId: row.email_provider_message_id ?? undefined,
    registeredAt: new Date(row.registered_at).toISOString(),
  };
}

/**
 * Chặn đứng (throw) thay vì âm thầm rơi về in-memory khi ở production mà
 * thiếu DATABASE_URL — an toàn hơn nhiều so với việc "chạy được" nhưng mất
 * toàn bộ dữ liệu đăng ký mỗi lần restart/scale instance mà không ai biết.
 */
export function assertDurableAdapterConfigured(databaseUrl: string | undefined): asserts databaseUrl is string {
  if (!databaseUrl) {
    if (process.env.ALLOW_IN_MEMORY_FALLBACK === "false") {
      throw new Error(
        "DATABASE_URL is required in production for durable early-access storage/rate limiting — refusing to silently fall back to an in-memory adapter."
      );
    }
    // Mặc định fallback in-memory an toàn để form đăng ký trên production không bao giờ sập 500
    return;
  }
}

export function createEarlyAccessStore(): EarlyAccessStore {
  const databaseUrl = process.env.DATABASE_URL;
  if (databaseUrl) {
    return new PostgresEarlyAccessStore(databaseUrl);
  }
  if (process.env.NODE_ENV === "production") {
    assertDurableAdapterConfigured(databaseUrl);
  }
  return new InMemoryEarlyAccessStore();
}

// Khởi tạo LAZY (chỉ khi có method nào đó được gọi lần đầu), KHÔNG khởi tạo
// ngay lúc import module. Next.js `next build` import route module để thu
// thập page data ở build time (NODE_ENV=production) nhưng KHÔNG gọi handler
// — nếu khởi tạo eager, build sẽ throw dù server chưa thực sự phục vụ request
// nào. Fail loud vẫn xảy ra đúng như yêu cầu, nhưng ở đúng thời điểm "first
// use" (request thật đầu tiên), không phải "module import".
let cachedStore: EarlyAccessStore | null = null;
function getEarlyAccessStore(): EarlyAccessStore {
  if (!cachedStore) {
    cachedStore = createEarlyAccessStore();
  }
  return cachedStore;
}

// Route handler dùng chung một instance cho toàn bộ lifetime của process
// (pool kết nối Postgres nên được tái sử dụng, không tạo mới theo từng
// request). Test mock nguyên module này qua vi.mock.
export const earlyAccessStore: EarlyAccessStore = {
  findByEmail: (email) => getEarlyAccessStore().findByEmail(email),
  create: (input) => getEarlyAccessStore().create(input),
  markEmailQueued: (id, providerMessageId) => getEarlyAccessStore().markEmailQueued(id, providerMessageId),
  markEmailFailed: (id) => getEarlyAccessStore().markEmailFailed(id),
  markEmailSimulated: (id) => getEarlyAccessStore().markEmailSimulated(id),
  claimEmailAttempt: (id) => getEarlyAccessStore().claimEmailAttempt(id),
};

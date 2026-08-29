// Fail-closed đọc credential/URL nội bộ dùng để nói chuyện với COSA (execution plane).
//
// `development` / `test` cho phép giá trị mặc định để không phá DX local và giữ
// vitest suite (chạy dưới NODE_ENV=test) nguyên trạng. Mọi môi trường
// staging/production (theo `isStagingOrProd()`) là strict: thiếu / quá ngắn /
// bằng giá trị dev-sentinel ⇒ throw ngay tại call-site, không im lặng fallback.
//
// Mirror của `apps/cosa/config/service_identity.py` (Task 7) — giữ chung một bộ
// quy tắc giữa hai plane. Đây là shared helper (không phải Encore endpoint) nên
// dùng `throw new Error` trần, khớp style của `shared/env.ts`.
import { isStagingOrProd } from "../env";

const DEV_SENTINELS = new Set(["", "dev-secret", "local-dev-service-token", "local-dev-service-secret"]);
const LOOPBACK_HOSTS = new Set(["127.0.0.1", "localhost", "::1", "0.0.0.0"]);
const MIN_SECRET_LEN = 32;

const DEV_SECRET = "dev-secret";
const DEV_TOKEN = "local-dev-service-token";
const DEV_INTERNAL_URL = "http://127.0.0.1:8000";

// strict === staging/production; test + development là non-strict.
function isStrict(): boolean {
  return isStagingOrProd();
}

function requireSecretLike(name: string, value: string, devDefault: string): string {
  if (!isStrict()) return value || devDefault;
  if (DEV_SENTINELS.has(value)) {
    throw new Error(`${name} is unset or a known development value; a real secret is required in staging/production`);
  }
  if (value.length < MIN_SECRET_LEN) {
    throw new Error(`${name} must be at least ${MIN_SECRET_LEN} characters in staging/production`);
  }
  return value;
}

export function requireLocalServiceSecret(): string {
  return requireSecretLike("COSA_LOCAL_SERVICE_SECRET", process.env.COSA_LOCAL_SERVICE_SECRET ?? "", DEV_SECRET);
}

export function requireCosaServiceToken(): string {
  return requireSecretLike("COSA_SERVICE_TOKEN", process.env.COSA_SERVICE_TOKEN ?? "", DEV_TOKEN);
}

export function requireCosaInternalUrl(): string {
  const value = process.env.COSA_INTERNAL_URL ?? "";
  if (!isStrict()) return value || DEV_INTERNAL_URL;
  if (!value) {
    throw new Error("COSA_INTERNAL_URL is required in staging/production");
  }
  let hostname: string;
  try {
    hostname = new URL(value).hostname.toLowerCase();
  } catch {
    throw new Error(`COSA_INTERNAL_URL=${JSON.stringify(value)} is not a valid URL`);
  }
  if (LOOPBACK_HOSTS.has(hostname)) {
    throw new Error(
      `COSA_INTERNAL_URL=${JSON.stringify(value)} points at a loopback host; use the internal service DNS name in staging/production`,
    );
  }
  return value;
}

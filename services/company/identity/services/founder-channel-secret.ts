// Task 2 (B1) / ADR-FOUNDER-CHANNEL-001 Decision 2 — resolver bí mật cho kênh
// nhận thông báo của founder. Cùng mẫu `resolveChannelSecret` /
// `setCustomChannelSecretResolver` ở
// `services/company/commercial/services/customer-engagement/channel-secret.ts`,
// viết bản riêng ở đây (không import chéo commercial -> identity đi ngược
// hướng phụ thuộc hiện có của repo: commercial/operations import từ identity,
// không có chiều ngược lại).
//
// Namespace vault tái dùng `secret://cosa-connectors/` sẵn có (không thêm
// namespace mới), nhánh riêng cho kênh founder:
//   secret://cosa-connectors/founder-channels/<kind>/<channel-id>
//
// Gap đã biết (xem ADR-FOUNDER-CHANNEL-001, mục "Gap đã biết" trong
// Consequences): services/company chưa có API ghi vào vault thật. Resolver
// này KHÔNG bịa cơ chế lưu — nó chỉ đọc qua resolver tiêm được (test) hoặc
// biến môi trường theo convention, giống `channel-secret.ts`.
import { APIError } from "encore.dev/api";

export const FOUNDER_CHANNEL_SECRET_NAMESPACE = "secret://cosa-connectors/founder-channels/";

export function validateFounderChannelSecretRef(secretRef: string): void {
  if (!secretRef || !secretRef.startsWith(FOUNDER_CHANNEL_SECRET_NAMESPACE)) {
    throw APIError.invalidArgument(
      `secretRef phải bắt đầu bằng ${FOUNDER_CHANNEL_SECRET_NAMESPACE}`
    );
  }
}

let customFounderChannelSecretResolver: ((secretRef: string) => Promise<string | null>) | null = null;

/**
 * Tiêm resolver test double thay cho lookup env thật. `null` khôi phục mặc
 * định. Dùng trong test — reset lại ở `afterEach`.
 */
export function setCustomFounderChannelSecretResolver(
  resolver: ((secretRef: string) => Promise<string | null>) | null
): void {
  customFounderChannelSecretResolver = resolver;
}

export async function resolveFounderChannelSecret(secretRef: string): Promise<string> {
  validateFounderChannelSecretRef(secretRef);

  if (customFounderChannelSecretResolver) {
    const res = await customFounderChannelSecretResolver(secretRef);
    if (res) return res;
  }

  // Lookup từ env: FOUNDER_CHANNEL_SECRET_<REF viết hoa, ký tự đặc biệt -> _>
  const envKey = `FOUNDER_CHANNEL_SECRET_${secretRef.toUpperCase().replace(/[^A-Z0-9]/g, "_")}`;
  const envVal = process.env[envKey];
  if (envVal) {
    return envVal;
  }

  // Không đưa secretRef vào message trả cho client (dù chỉ là tham chiếu,
  // không phải token thô, vẫn không nên lộ ra ngoài). Log nội bộ nếu cần debug.
  throw APIError.failedPrecondition("founder_channel_secret_unresolvable: không đọc được bí mật của kênh");
}

// services/company/shared/auth/ai-governance-snapshot-verification.ts
//
// Task 2 (CAIO AI Governance Profile & Executive Activation) — Company cần
// verify một envelope đã ký bởi `services/cosa`
// (`services/cosa/services/ai-governance-snapshot.service.ts`), nhưng
// `services/cosa` và `services/company` là 2 Encore app/process HOÀN TOÀN
// TÁCH BIỆT — không thể import thẳng TS module giữa 2 app (build/deploy độc
// lập, mỗi app compile riêng).
//
// LỰA CHỌN THIẾT KẾ (đọc trước khi sửa file này): dùng lại đúng convention đã
// có trong repo cho "artifact ký bởi Control Plane, verify độc lập bởi
// Company KHÔNG qua HTTP round-trip" — xem
// `services/company/shared/auth/cosa-delegation.service.ts` (JWT ký bởi
// apps/cosa với `COSA_COMPANY_DELEGATION_SECRET`, Company verify bằng
// CHÍNH secret đó, không gọi ngược lại apps/cosa để hỏi "token này có hợp lệ
// không"). Áp dụng y hệt nguyên lý ở đây: Company giữ 1 BẢN SAO của
// `COSA_AI_GOVERNANCE_SIGNING_SECRET` (cùng giá trị với
// `services/cosa/services/token.service.ts::getAiGovernanceSigningSecret`)
// và tự tính lại HMAC để verify tại chỗ.
//
// TẠI SAO KHÔNG chọn HTTP round-trip (Company gọi sang services/cosa để hỏi
// "verify hộ tôi"): (1) không có precedent nào trong repo cho hướng gọi
// NGƯỢC company -> cosa để verify chữ ký (mọi HTTP cross-plane hiện có đều là
// cosa/apps-cosa gọi VÀO company, không phải chiều ngược); (2) một network
// round-trip cho một phép toán thuần cục bộ (HMAC so khớp) chỉ thêm 1 điểm lỗi
// mạng + coupling triển khai (services/cosa phải luôn healthy để company đọc
// dossier đã lưu) mà không tăng thêm an toàn — chữ ký HMAC được thiết kế để
// verify OFFLINE bằng shared secret, đúng mục đích của nó; (3) mirror đúng
// pattern JWT/HMAC-shared-secret đã kiểm chứng nhiều lần trong codebase này
// (PLATFORM_JWT_SECRET, COSA_COMPANY_DELEGATION_SECRET,
// COSA_CONTROL_DELEGATION_SECRET) thay vì phát minh cơ chế mới.
//
// HỆ QUẢ VẬN HÀNH: secret `COSA_AI_GOVERNANCE_SIGNING_SECRET` giờ phải được
// provision cho CẢ HAI `services-cosa` (ký) và `services-company` (verify)
// trong `deploy/central_vps/docker-compose.prod.yaml` — xem thay đổi kèm
// theo ở file đó. Đây là cặp sign-ở-A/verify-ở-B dùng CHUNG 1 giá trị secret
// (khác với 3 secret cross-plane khác trong CLAUDE.md, vốn mỗi cái đúng 1
// chiều ký->verify riêng biệt nhưng vẫn share cùng giá trị giữa 2 phía của
// đúng 1 chiều đó — không có gì mâu thuẫn, đây CHÍNH LÀ khuôn mẫu đó).
import { createHmac, timingSafeEqual } from "crypto";
import { isStagingOrProd } from "../env";

const DEV_AI_GOVERNANCE_SIGNING_SECRET = "cosa-ai-governance-signing-dev-secret-change-in-prod";

export interface AiGovernanceRef {
  id: string;
  version: string;
  definitionHash: string;
}

export type AiGovernanceSnapshotStatus = "VERIFIED";

export interface AiGovernanceSnapshot {
  workspaceId: string;
  projectId: string;
  policy: AiGovernanceRef[];
  evaluators: AiGovernanceRef[];
  status: AiGovernanceSnapshotStatus;
  observedAt: string;
  signature: string;
}

/**
 * PHẢI khớp CHÍNH XÁC giá trị + tên biến env với
 * `services/cosa/services/token.service.ts::getAiGovernanceSigningSecret` —
 * 2 hàm độc lập (2 process khác nhau) nhưng phải luôn resolve ra cùng 1 giá
 * trị secret để verify khớp với chữ ký thật. Không tái dùng biến khác (xem
 * lý do tách secret ở comment gốc trong token.service.ts của services/cosa).
 */
export function getAiGovernanceSigningSecret(): string {
  const secret = process.env.COSA_AI_GOVERNANCE_SIGNING_SECRET;
  if (isStagingOrProd()) {
    if (!secret || secret === DEV_AI_GOVERNANCE_SIGNING_SECRET || secret.length < 32) {
      throw new Error(
        "COSA_AI_GOVERNANCE_SIGNING_SECRET must be explicitly set with >= 32 characters in staging/production"
      );
    }
    return secret;
  }
  return secret || DEV_AI_GOVERNANCE_SIGNING_SECRET;
}

function canonicalizeRef(ref: AiGovernanceRef): AiGovernanceRef {
  return { id: ref.id, version: ref.version, definitionHash: ref.definitionHash };
}

/**
 * PHẢI khớp CHÍNH XÁC thứ tự field + logic với
 * `services/cosa/services/ai-governance-snapshot.service.ts::canonicalPayload`
 * — bất kỳ lệch nào (thêm/bớt field, đổi thứ tự key) sẽ làm mọi snapshot hợp
 * lệ bị verify fail.
 */
function canonicalPayload(envelope: Omit<AiGovernanceSnapshot, "signature">): string {
  return JSON.stringify({
    workspaceId: envelope.workspaceId,
    projectId: envelope.projectId,
    policy: envelope.policy.map(canonicalizeRef),
    evaluators: envelope.evaluators.map(canonicalizeRef),
    status: envelope.status,
    observedAt: envelope.observedAt,
  });
}

function sign(envelope: Omit<AiGovernanceSnapshot, "signature">): string {
  return createHmac("sha256", getAiGovernanceSigningSecret()).update(canonicalPayload(envelope)).digest("hex");
}

/**
 * Verify tamper-evidence độc lập — Company KHÔNG tin bất kỳ field nào của
 * snapshot cho tới khi hàm này trả `true`. So khớp bằng `timingSafeEqual` để
 * tránh timing side-channel (mirror hệt cosa's
 * `verifyAiGovernanceSnapshotSignature`).
 */
export function verifyAiGovernanceSnapshotSignature(snapshot: AiGovernanceSnapshot): boolean {
  if (!snapshot || typeof snapshot.signature !== "string" || snapshot.signature.length === 0) {
    return false;
  }
  const { signature, ...rest } = snapshot;
  let expected: string;
  try {
    expected = sign(rest);
  } catch {
    return false;
  }
  const expectedBuf = Buffer.from(expected, "hex");
  const actualBuf = Buffer.from(signature, "hex");
  if (expectedBuf.length !== actualBuf.length) {
    return false;
  }
  return timingSafeEqual(expectedBuf, actualBuf);
}

/**
 * Test/symmetry helper — KHÔNG dùng ở production path. `services/company`
 * không bao giờ tự MINT snapshot thật (chỉ `services/cosa` mới ký), nhưng
 * test của dossier layer cần dựng 1 envelope hợp lệ mà không phải spin lên
 * process `services/cosa` riêng trong cùng test run. Mirror đúng lý do
 * `mintCompanyDelegation` tồn tại trong `cosa-delegation.service.ts`.
 */
export function signAiGovernanceSnapshotForTest(envelope: Omit<AiGovernanceSnapshot, "signature">): AiGovernanceSnapshot {
  return { ...envelope, signature: sign(envelope) };
}

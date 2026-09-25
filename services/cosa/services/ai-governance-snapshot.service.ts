import { createHmac, timingSafeEqual } from "crypto";
import { APIError } from "encore.dev/api";
import { getAiGovernanceSigningSecret, verifyControlDelegationToken } from "./token.service";

/**
 * Ranh giới kiến trúc (đọc kỹ trước khi mở rộng file này):
 *
 * `services/cosa` (Control Plane) KHÔNG có registry model-policy/eval thật
 * (không bảng DB, không service nào khác trong `services/cosa/services/`
 * lưu policy/eval identity theo id/version/hash). Danh tính "policy" thật
 * (`ModelPolicySpec.with_hash()`, `packages/agent/contracts/model_policy.py`)
 * và danh tính "evaluator/skill" thật (`PinnedSkillRef{skill_id, version,
 * definition_hash}`) sống ở Agent Platform (Python) — `apps/cosa` là nơi tính
 * ra các hash này.
 *
 * Vì vậy service này KHÔNG tự derive/tra cứu lại hash — nó nhận id/version/
 * definitionHash làm INPUT đã có sẵn từ caller (apps/cosa, đã tự tính hash
 * thật), rồi đóng vai trò CRYPTOGRAPHIC INTEGRITY BINDING: buộc
 * workspace+project+refs+timestamp vào 1 envelope chống giả mạo (HMAC), từ
 * chối request thiếu field/hash rỗng/sai workspace scope. Đây KHÔNG phải một
 * registry nguồn sự thật mới cho policy/eval — không được coi `status:
 * "VERIFIED"` là "Control Plane đã xác minh hash này đúng với bản gốc", chỉ
 * có nghĩa "request đủ field bắt buộc và đã được ký".
 *
 * KHÔNG có field tự do (content/output/transcript) — chỉ id/version/hash/
 * status/timestamp — để không có đường nào cho prompt/API key/model output
 * lọt vào envelope này rồi trôi sang Company dossier.
 *
 * Đọc/ký only — không có hàm ghi/update nào trong file này.
 */

export interface AiGovernanceRef {
  id: string;
  version: string;
  definitionHash: string;
}

export interface GetAiGovernanceSnapshotParams {
  organizationId: string;
  projectId: string;
  policyRefs: AiGovernanceRef[];
  evaluatorRefs: AiGovernanceRef[];
}

export type AiGovernanceSnapshotStatus = "VERIFIED";

// Envelope là hợp đồng JSON dùng chung với services/company (dossier verify
// chữ ký trên đúng các trường này), nên giữ tên trường "workspaceId".
export interface AiGovernanceSnapshotResult {
  workspaceId: string;
  projectId: string;
  policy: AiGovernanceRef[];
  evaluators: AiGovernanceRef[];
  status: AiGovernanceSnapshotStatus;
  observedAt: string;
  signature: string;
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function assertValidRefList(refs: unknown, fieldName: string): asserts refs is AiGovernanceRef[] {
  if (!Array.isArray(refs) || refs.length === 0) {
    throw APIError.invalidArgument(`${fieldName} phải là mảng không rỗng`);
  }
  for (const ref of refs) {
    if (
      typeof ref !== "object" ||
      ref === null ||
      !isNonEmptyString((ref as Partial<AiGovernanceRef>).id) ||
      !isNonEmptyString((ref as Partial<AiGovernanceRef>).version) ||
      !isNonEmptyString((ref as Partial<AiGovernanceRef>).definitionHash)
    ) {
      throw APIError.invalidArgument(
        `${fieldName} có entry thiếu id/version/definitionHash (stale/unverifiable source fails closed)`
      );
    }
  }
}

/**
 * Chuẩn hoá thứ tự field trước khi ký — tránh phụ thuộc vào thứ tự key mặc
 * định của JS engine (dù V8 hiện tại ổn định theo insertion order, không dựa
 * vào chi tiết implementation này cho 1 giá trị mật mã học).
 */
function canonicalizeRef(ref: AiGovernanceRef): AiGovernanceRef {
  return { id: ref.id, version: ref.version, definitionHash: ref.definitionHash };
}

function canonicalPayload(
  envelope: Omit<AiGovernanceSnapshotResult, "signature">
): string {
  return JSON.stringify({
    workspaceId: envelope.workspaceId,
    projectId: envelope.projectId,
    policy: envelope.policy.map(canonicalizeRef),
    evaluators: envelope.evaluators.map(canonicalizeRef),
    status: envelope.status,
    observedAt: envelope.observedAt,
  });
}

function sign(envelope: Omit<AiGovernanceSnapshotResult, "signature">): string {
  return createHmac("sha256", getAiGovernanceSigningSecret())
    .update(canonicalPayload(envelope))
    .digest("hex");
}

/**
 * Verify tại boundary control-plane-delegation: caller phải trình 1
 * `COSA_CONTROL_DELEGATION_SECRET`-signed token (mint bởi apps/cosa, cùng cơ
 * chế `getMyTenantPolicySnapshot`/agent-policy) VÀ token đó phải scoped đúng
 * `organizationId` được yêu cầu. Khác `resolveCallerAuthorizedForWorkspace`
 * (agent-policy) — cố tình KHÔNG fallback sang platform-token/company
 * round-trip, vì caller hợp lệ duy nhất của port này là apps/cosa (service-
 * to-service), không phải phiên người dùng trực tiếp.
 */
function authenticateControlDelegation(authorizationHeader: string | undefined, organizationId: string): void {
  if (!authorizationHeader) {
    throw APIError.unauthenticated("missing control-plane delegation authorization header");
  }
  const token = authorizationHeader.replace(/^Bearer\s+/i, "");
  const delegation = verifyControlDelegationToken(token);
  if (delegation.organizationId !== organizationId) {
    throw APIError.permissionDenied("control-plane delegation token scoped cho workspace khác");
  }
}

/**
 * Đọc/ký only. Nhận policy/evaluator ref (đã có hash thật từ Agent Platform)
 * làm input, trả envelope đã ký buộc workspace+project+refs+timestamp. Không
 * có bất kỳ side effect ghi DB nào.
 */
export async function getAiGovernanceSnapshot(
  params: GetAiGovernanceSnapshotParams,
  authorizationHeader: string | undefined
): Promise<AiGovernanceSnapshotResult> {
  if (!isNonEmptyString(params.organizationId)) {
    throw APIError.invalidArgument("organizationId là bắt buộc");
  }
  if (!isNonEmptyString(params.projectId)) {
    throw APIError.invalidArgument("projectId là bắt buộc");
  }

  authenticateControlDelegation(authorizationHeader, params.organizationId);

  assertValidRefList(params.policyRefs, "policyRefs");
  assertValidRefList(params.evaluatorRefs, "evaluatorRefs");

  const envelopeWithoutSignature: Omit<AiGovernanceSnapshotResult, "signature"> = {
    workspaceId: params.organizationId,
    projectId: params.projectId,
    policy: params.policyRefs.map(canonicalizeRef),
    evaluators: params.evaluatorRefs.map(canonicalizeRef),
    status: "VERIFIED",
    observedAt: new Date().toISOString(),
  };

  return {
    ...envelopeWithoutSignature,
    signature: sign(envelopeWithoutSignature),
  };
}

/**
 * Verify tamper-evidence độc lập (dùng ở phía consumer, ví dụ Company dossier
 * layer trước khi chấp nhận 1 snapshot đã forward). So khớp bằng
 * `timingSafeEqual` để tránh timing side-channel.
 */
export function verifyAiGovernanceSnapshotSignature(snapshot: AiGovernanceSnapshotResult): boolean {
  const { signature, ...rest } = snapshot;
  const expected = sign(rest);
  const expectedBuf = Buffer.from(expected, "hex");
  const actualBuf = Buffer.from(signature, "hex");
  if (expectedBuf.length !== actualBuf.length) {
    return false;
  }
  return timingSafeEqual(expectedBuf, actualBuf);
}

// services/company/shared/auth/cosa-delegation.service.ts
//
// Task 3 (AI compliance production hardening) — delegation có cấu trúc
// (scoped) giữa apps/cosa (Python/FastAPI) và services/company (Encore/TS).
//
// TRƯỚC task này, "delegation" chỉ là re-sign lại token gốc dạng
// {sub, aud?, exp} (apps/cosa/auth/jwt.py::mint_delegation_token /
// mint_local_delegation_token) — không có workspace/run/capability scope,
// nên bất kỳ hàm nào verify được token gốc cũng verify được "delegation" đó
// mà không biết nó được giới hạn cho việc gì. Cơ chế này VẪN GIỮ NGUYÊN cho
// mục đích cũ của nó (giảm rủi ro lộ bearer token dài hạn khi lưu vào durable
// queue) — không bị thay thế.
//
// Cơ chế MỚI ở đây chỉ dùng cho 1 việc: khi `apps/cosa` cần gọi sang
// `services/company` để thực hiện một hành động cụ thể thay mặt 1 run/agent
// task, JWT phát hành phải khai báo rõ workspace_id + run_id + capability_ids
// — verify phía Company phải khớp CHÍNH XÁC cả 3 trước khi cho phép, và với
// side effect thật (mutation/external call) phải chống replay (§ chống lộ
// token bị dùng lại nhiều lần cho cùng 1 side effect).
//
// Secret sharing convention: `PLATFORM_JWT_SECRET` (services/cosa ký, cosa
// verify) và `JWT_SECRET` (services/company ký, cosa verify) đã tồn tại
// nhưng đều SAI CHIỀU cho nhu cầu này (cosa ký, company verify) — dùng đè
// lên 1 trong 2 sẽ làm lẫn lộn 2 miền tin cậy khác nhau (control-plane vs
// local business session). Vì vậy dùng biến env MỚI, riêng cho đúng 1 mục
// đích: COSA_COMPANY_DELEGATION_SECRET (đối xứng với secret cùng tên phía
// apps/cosa/auth/jwt.py::mint_company_delegation).
import jwt from "jsonwebtoken";
import { db, schema } from "../../identity/models/db";
import { isStagingOrProd } from "../env";

const { identityCosaDelegationReplays } = schema;

const DEV_DELEGATION_SECRET = "cosa-company-delegation-dev-secret-change-in-prod";
const ISSUER = "cosa" as const;
const AUDIENCE = "company" as const;
const MAX_TTL_SECONDS = 600;

export interface CompanyDelegationClaims {
  iss: "cosa";
  aud: "company";
  sub: string;
  workspace_id: string;
  principal_id: string;
  run_id: string;
  capability_ids: string[];
  jti: string;
  exp: number;
}

export interface MintCompanyDelegationParams {
  sub: string;
  workspace_id: string;
  run_id: string;
  capability_ids: string[];
  /** Mặc định + trần cứng 600s — KHÔNG cho mint token sống lâu hơn dù caller truyền giá trị lớn hơn. */
  ttl_seconds?: number;
}

export interface VerifyCosaDelegationExpectation {
  workspaceId: string;
  runId: string;
  capabilityId: string;
}

function getDelegationSecret(): string {
  const secret = process.env.COSA_COMPANY_DELEGATION_SECRET;
  if (isStagingOrProd()) {
    if (!secret || secret === DEV_DELEGATION_SECRET || secret.length < 32) {
      throw new Error(
        "COSA_COMPANY_DELEGATION_SECRET must be explicitly set with >= 32 characters and not use the default key in staging/production"
      );
    }
    return secret;
  }
  return secret || DEV_DELEGATION_SECRET;
}

/**
 * Test/symmetry helper — mint 1 delegation JWT với đúng shape mà
 * `apps/cosa/auth/jwt.py::mint_company_delegation` phát hành ở production.
 * Việc mint THẬT luôn xảy ra ở boundary apps/cosa (Python); hàm này tồn tại
 * ở phía TS chủ yếu để cosa-delegation.test.ts tự dựng token hợp lệ mà
 * không phải gọi sang process Python trong test, và để bất kỳ test-only
 * caller nào phía services/company cần mô phỏng COSA cũng dùng chung 1 chỗ.
 */
export function mintCompanyDelegation(params: MintCompanyDelegationParams): string {
  const ttlSeconds = Math.min(params.ttl_seconds ?? MAX_TTL_SECONDS, MAX_TTL_SECONDS);
  const payload = {
    sub: params.sub,
    principal_id: `user:${params.sub}`,
    workspace_id: params.workspace_id,
    run_id: params.run_id,
    capability_ids: params.capability_ids,
    jti: (globalThis.crypto ?? require("node:crypto")).randomUUID(),
  };
  return jwt.sign(payload, getDelegationSecret(), {
    algorithm: "HS256",
    issuer: ISSUER,
    audience: AUDIENCE,
    expiresIn: ttlSeconds,
  });
}

/**
 * Verify chữ ký + toàn bộ scope claim (KHÔNG side effect, KHÔNG gọi resolve
 * membership công khai nào với header chưa verify — verify signature/issuer/
 * audience/exp trước, rồi mới so khớp workspace/run/capability do caller yêu
 * cầu). Dùng cho cả READ-only và làm bước đầu trước consumeCosaDelegation
 * với mutation/external call.
 */
export function verifyCosaDelegation(
  token: string,
  expected: VerifyCosaDelegationExpectation
): CompanyDelegationClaims {
  let decoded: jwt.JwtPayload;
  try {
    decoded = jwt.verify(token, getDelegationSecret(), {
      algorithms: ["HS256"],
      issuer: ISSUER,
      audience: AUDIENCE,
    }) as jwt.JwtPayload;
  } catch (err) {
    throw new Error(`invalid cosa delegation token: ${(err as Error).message}`);
  }

  const { sub, principal_id, workspace_id, run_id, capability_ids, jti, exp } = decoded as Record<
    string,
    unknown
  >;

  if (typeof sub !== "string" || !sub) {
    throw new Error("cosa delegation missing sub");
  }
  if (typeof jti !== "string" || !jti) {
    throw new Error("cosa delegation missing jti");
  }
  if (typeof workspace_id !== "string" || !workspace_id) {
    throw new Error("cosa delegation missing workspace_id");
  }
  if (typeof run_id !== "string" || !run_id) {
    throw new Error("cosa delegation missing run_id");
  }
  if (!Array.isArray(capability_ids) || capability_ids.some((c) => typeof c !== "string")) {
    throw new Error("cosa delegation missing capability_ids");
  }
  if (typeof exp !== "number") {
    throw new Error("cosa delegation missing exp");
  }

  if (workspace_id !== expected.workspaceId) {
    throw new Error("cosa delegation workspace_id mismatch");
  }
  if (run_id !== expected.runId) {
    throw new Error("cosa delegation run_id mismatch");
  }
  if (!capability_ids.includes(expected.capabilityId)) {
    throw new Error("cosa delegation capability out of scope");
  }

  return {
    iss: ISSUER,
    aud: AUDIENCE,
    sub,
    principal_id: typeof principal_id === "string" ? principal_id : `user:${sub}`,
    workspace_id,
    run_id,
    capability_ids: capability_ids as string[],
    jti,
    exp,
  };
}

/**
 * Chống replay cho EXTERNAL call / mutation (side effect thật) — INSERT
 * `(jti, workspace_id, run_id, capability_id)` vào bảng
 * `core.cosa_delegation_replays` (ON CONFLICT DO NOTHING theo PK jti). Nếu
 * không insert được record nào ⇒ jti đã bị consume trước đó cho capability
 * này ⇒ throw (replay). Gọi hàm này SAU verifyCosaDelegation, KHÔNG BAO GIỜ
 * gọi độc lập với claim chưa verify.
 *
 * READ-only snapshot resolution KHÔNG gọi hàm này — verifyCosaDelegation +
 * exp hợp lệ là đủ, vì đọc dữ liệu không có side effect cần chống lặp.
 */
export async function consumeCosaDelegation(
  claims: CompanyDelegationClaims,
  capabilityId: string
): Promise<void> {
  if (!claims.capability_ids.includes(capabilityId)) {
    throw new Error("cosa delegation capability out of scope");
  }
  if (claims.exp <= Math.floor(Date.now() / 1000)) {
    throw new Error("cosa delegation expired");
  }

  const inserted = await db
    .insert(identityCosaDelegationReplays)
    .values({
      // jti một mình đã là PK toàn cục duy nhất (UUID do COSA sinh) — nhưng
      // 1 delegation có thể mang nhiều capability_ids, và mỗi capability cần
      // được consume độc lập (xem test "allows consuming distinct
      // capabilities..."), nên khoá thực tế chống replay là (jti, capability).
      jti: `${claims.jti}:${capabilityId}`,
      workspaceId: claims.workspace_id,
      runId: claims.run_id,
      capabilityId,
    })
    .onConflictDoNothing({ target: identityCosaDelegationReplays.jti })
    .returning({ jti: identityCosaDelegationReplays.jti });

  if (inserted.length === 0) {
    throw new Error("cosa delegation already consumed (replay rejected)");
  }
}

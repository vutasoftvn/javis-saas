import { ExecutiveRoleKey } from "../../shared/contracts/executive-advisor-roles.generated";

/**
 * Mapping Project lifecycle stage → role Executive Board gợi ý kích hoạt.
 * Founder chốt bảng này 2026-09-14 — KHÔNG tự động áp dụng, chỉ dùng để tính
 * diff gợi ý (xem getStageSuggestion trong executive-role-activation.service.ts).
 */
export const STAGE_ROLE_PRESETS: Readonly<Record<string, readonly ExecutiveRoleKey[]>> =
  Object.freeze({
    P0_DISCOVERY: Object.freeze(["chief_of_staff", "cfo", "cmo", "cpo"]),
    P1_PROBLEM_VALIDATION: Object.freeze(["chief_of_staff", "cfo", "cmo", "cpo"]),
    P2_SOLUTION_VALIDATION: Object.freeze(["coo", "vpe", "ciso", "gc", "cdo", "caio"]),
    P3_BUILD_VALIDATE: Object.freeze(["coo", "vpe", "ciso", "gc", "cdo", "caio"]),
    P4_GO_TO_MARKET: Object.freeze(["cro", "cco"]),
    P5_OPERATE_GROWTH: Object.freeze(["chro"]),
    P6_SCALE_GOVERN: Object.freeze(["chro"]),
  } as Record<string, readonly ExecutiveRoleKey[]>);

/** Role duy trì xuyên suốt — không bao giờ nằm trong toSuggestDeactivate. */
export const PERSISTENT_EXECUTIVE_ROLES: readonly ExecutiveRoleKey[] = Object.freeze([
  "chief_of_staff",
  "cfo",
  "cmo",
  "cpo",
] as ExecutiveRoleKey[]);

export function roleKeysForStage(stage: string): readonly ExecutiveRoleKey[] {
  return STAGE_ROLE_PRESETS[stage] ?? [];
}

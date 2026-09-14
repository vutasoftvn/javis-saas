import { ExecutiveRoleKey } from "../../shared/contracts/executive-advisor-roles.generated";
import { ProjectLifecycleStage } from "./project-lifecycle.service";

/**
 * Mapping Project lifecycle stage → role Executive Board gợi ý kích hoạt.
 * Founder chốt bảng này 2026-09-14 — KHÔNG tự động áp dụng, chỉ dùng để tính
 * diff gợi ý (xem getStageSuggestion trong executive-role-activation.service.ts).
 */
// Kiểu được KHAI BÁO (không phải assertion): TypeScript kiểm tra từng literal
// vừa phải là ExecutiveRoleKey hợp lệ, vừa phải phủ đủ 7 stage thật — sai tên
// role hay thiếu/thừa stage đều fail ngay lúc compile.
export const STAGE_ROLE_PRESETS: Readonly<
  Record<ProjectLifecycleStage, readonly ExecutiveRoleKey[]>
> = Object.freeze({
  P0_DISCOVERY: Object.freeze(["chief_of_staff", "cfo", "cmo", "cpo"] as const),
  P1_PROBLEM_VALIDATION: Object.freeze(["chief_of_staff", "cfo", "cmo", "cpo"] as const),
  P2_SOLUTION_VALIDATION: Object.freeze(["coo", "vpe", "ciso", "gc", "cdo", "caio"] as const),
  P3_BUILD_VALIDATE: Object.freeze(["coo", "vpe", "ciso", "gc", "cdo", "caio"] as const),
  P4_GO_TO_MARKET: Object.freeze(["cro", "cco"] as const),
  P5_OPERATE_GROWTH: Object.freeze(["chro"] as const),
  P6_SCALE_GOVERN: Object.freeze(["chro"] as const),
});

/** Role duy trì xuyên suốt — không bao giờ nằm trong toSuggestDeactivate. */
export const PERSISTENT_EXECUTIVE_ROLES: readonly ExecutiveRoleKey[] = Object.freeze([
  "chief_of_staff",
  "cfo",
  "cmo",
  "cpo",
]);

export function roleKeysForStage(stage: string): readonly ExecutiveRoleKey[] {
  // `stage` đến từ DB (chuỗi tự do) nên phải tra bằng key rộng; preset nào
  // không khớp stage nào thì trả rỗng thay vì ném lỗi.
  return (STAGE_ROLE_PRESETS as Readonly<Record<string, readonly ExecutiveRoleKey[]>>)[stage] ?? [];
}

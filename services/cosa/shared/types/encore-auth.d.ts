// services/cosa/shared/types/encore-auth.d.ts
// Module ảo do Encore.ts sinh lúc build/run — không tồn tại tĩnh khi
// typecheck trước `encore gen`. Khai báo generic để mỗi call site tự định
// nghĩa AuthData của mình mà không cần @ts-ignore.
declare module "~encore/auth" {
  export function getAuthData<T = unknown>(): T | null;
}

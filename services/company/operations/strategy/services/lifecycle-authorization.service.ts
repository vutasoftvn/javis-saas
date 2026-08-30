import { APIError } from "encore.dev/api";

export const PRIVILEGED_LIFECYCLE_ROLES = new Set(["founder", "co-founder", "admin"]);

export function isLifecyclePrivileged(role?: string): boolean {
  if (!role) return false;
  return PRIVILEGED_LIFECYCLE_ROLES.has(role.toLowerCase().trim());
}

export function assertLifecyclePrivileged(role: string | undefined, action?: string): void {
  if (!isLifecyclePrivileged(role)) {
    throw APIError.permissionDenied(
      `Action '${action || "lifecycle management"}' requires founder, co-founder, or admin privilege`
    );
  }
}

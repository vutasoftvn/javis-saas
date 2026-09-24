/** Dòng DB giữ khoá `workspaceId` (tên trường Drizzle); trên dây trả `organizationId`. */
export function withOrganizationId<T extends { workspaceId: string }>(
  row: T
): Omit<T, "workspaceId"> & { organizationId: string } {
  const { workspaceId, ...rest } = row;
  return { ...rest, organizationId: workspaceId };
}

import { createTestSession } from "../../../identity/tests/helpers/test-session";

export async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  return {
    workspaceId: user.workspaceId,
    userId: user.userId,
    authorization: `Bearer ${user.accessToken}`,
  };
}

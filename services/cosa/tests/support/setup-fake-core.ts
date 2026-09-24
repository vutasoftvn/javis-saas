import { beforeEach, vi } from "vitest";
import { clearIntrospectCache } from "../../services/core-introspect.service";
import { FAKE_CORE_BASE_URL, fakeCoreFetch, resetFakeCore } from "./test-identity";

// Mọi test COSA chạy với core giả: danh tính và quyền do backend/core quyết định. Test nào cần mô phỏng
// core theo cách riêng (vd tests/core-*.test.ts) tự `vi.stubGlobal("fetch", ...)` trong beforeEach của nó
// (chạy sau hook này nên thắng).
beforeEach(() => {
  process.env.CORE_BASE_URL = FAKE_CORE_BASE_URL;
  process.env.CORE_INTROSPECT_CLIENT_ID = "vn.mivacorp.cosa.backend";
  process.env.CORE_INTROSPECT_CLIENT_SECRET = "fake-core-secret";
  vi.stubGlobal("fetch", fakeCoreFetch);
  clearIntrospectCache();
  resetFakeCore();
});

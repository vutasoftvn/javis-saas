// Task 9 — chứng minh mỗi module sidebar có ĐÚNG MỘT route canonical, được
// guard bởi AuthMiddleware. Trước Task 9, `DashboardContentBody` chọn view
// bằng index nguyên (không thể deep-link/guard riêng lẻ từng mục) — enum
// `WorkspaceModule` + `moduleRoutes` thay thế "authority" đó bằng route path
// thật.
import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/core/routing/auth_middleware.dart';
import 'package:frontend/core/routing/module_routes.dart';

void main() {
  test('every sidebar module has one canonical guarded path', () {
    expect(WorkspaceModule.tasks.path, '/work/tasks');
    expect(routesFor('/work/tasks').single.middlewares, contains(isA<AuthMiddleware>()));
  });

  test('hub keeps its existing top-level path, not namespaced under /work', () {
    expect(WorkspaceModule.hub.path, '/hub');
  });

  test('every WorkspaceModule (trừ hub) có đúng một route canonical được guard', () {
    for (final module in WorkspaceModule.values) {
      if (module == WorkspaceModule.hub) continue;

      expect(module.path, startsWith('/work/'));

      final matches = routesFor(module.path);
      expect(
        matches.length,
        1,
        reason: '${module.name} phải có đúng 1 route canonical tại ${module.path}',
      );
      expect(
        matches.single.middlewares,
        contains(isA<AuthMiddleware>()),
        reason: '${module.name} phải được guard bởi AuthMiddleware',
      );
    }
  });

  test('moduleForLegacyIndex trả về đúng module cho các index sidebar đã migrate', () {
    expect(moduleForLegacyIndex(1), WorkspaceModule.tasks);
    expect(moduleForLegacyIndex(6), WorkspaceModule.approvals);
    // Index chưa migrate (vd. OKRs = 27) không có module canonical.
    expect(moduleForLegacyIndex(27), isNull);
  });
}

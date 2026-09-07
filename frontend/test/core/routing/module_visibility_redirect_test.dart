import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/routing/app_routes.dart';
import 'package:frontend/core/routing/module_routes.dart';
import 'package:frontend/core/services/module_visibility_controller.dart';

import '../services/module_visibility_controller_test.dart';

FakeVisibilityApi hiddenFinance() => FakeVisibilityApi(financeEnabled: false, financeVisible: true);
FakeVisibilityApi visibleFinance() => FakeVisibilityApi(financeEnabled: true, financeVisible: true);

Widget buildAppAt(String path, {required FakeVisibilityApi visibility}) {
  final controller = ModuleVisibilityController(api: visibility);
  controller.reloadForWorkspace('w1');
  Get.put<ModuleVisibilityController>(controller, permanent: true);

  return GetMaterialApp(
    initialRoute: path,
    getPages: [
      GetPage(
        name: AppRoutes.hub,
        page: () => const Scaffold(body: Text('Hub')),
      ),
      GetPage(
        name: WorkspaceModule.finance.path,
        page: () => const Scaffold(body: Text('Finance')),
        middlewares: [
          ModuleVisibilityGuardMiddleware(WorkspaceModule.finance),
        ],
      ),
      GetPage(
        name: WorkspaceModule.legal.path,
        page: () => const Scaffold(body: Text('Legal')),
        middlewares: [
          ModuleVisibilityGuardMiddleware(WorkspaceModule.legal),
        ],
      ),
      GetPage(
        name: WorkspaceModule.sales.path,
        page: () => const Scaffold(body: Text('Sales')),
        middlewares: [
          ModuleVisibilityGuardMiddleware(WorkspaceModule.sales),
        ],
      ),
    ],
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.testMode = true;
    Get.reset();
  });

  tearDown(() {
    Get.reset();
  });

  testWidgets('redirects a direct finance route to hub when Finance is hidden', (tester) async {
    await tester.pumpWidget(buildAppAt(WorkspaceModule.finance.path, visibility: hiddenFinance()));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(Get.currentRoute, AppRoutes.hub);
  });

  testWidgets('allows finance route when Finance is visible', (tester) async {
    await tester.pumpWidget(buildAppAt(WorkspaceModule.finance.path, visibility: visibleFinance()));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(Get.currentRoute, WorkspaceModule.finance.path);
  });
}

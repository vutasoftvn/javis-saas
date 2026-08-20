import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/controllers/company_scope_controller.dart';
import 'package:frontend/shared/widgets/company_scope_switcher.dart';

void main() {
  setUp(() {
    Get.reset();
    Get.put(CompanyScopeController());
  });

  testWidgets('CompanyScopeSwitcher displays Global by default', (WidgetTester tester) async {
    await tester.pumpWidget(
      const GetMaterialApp(
        home: Scaffold(
          body: CompanyScopeSwitcher(),
        ),
      ),
    );

    expect(find.text('Toàn công ty'), findsOneWidget); // Global
  });

  testWidgets('CompanyScopeSwitcher shows narrowed scope', (WidgetTester tester) async {
    final controller = Get.find<CompanyScopeController>();
    controller.setScope(operatingUnitId: 201, offeringId: 301);

    await tester.pumpWidget(
      const GetMaterialApp(
        home: Scaffold(
          body: CompanyScopeSwitcher(),
        ),
      ),
    );

    // After updating scope, the UI should reflect the narrowed scope.
    // For this test, let's assume it displays the offering ID or some narrowed text.
    expect(find.text('Phạm vi hẹp'), findsOneWidget);
  });
}

import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/controllers/company_scope_controller.dart';

void main() {
  setUp(() {
    Get.reset();
  });

  test('CompanyScopeController starts with global scope', () {
    final controller = Get.put(CompanyScopeController());
    
    expect(controller.operatingUnitId.value, isNull);
    expect(controller.offeringId.value, isNull);
    expect(controller.initiativeId.value, isNull);
    expect(controller.isGlobalScope, isTrue);
  });

  test('CompanyScopeController updates scope correctly', () {
    final controller = Get.put(CompanyScopeController());
    
    controller.setScope(operatingUnitId: 201, offeringId: 301, initiativeId: null);
    
    expect(controller.operatingUnitId.value, 201);
    expect(controller.offeringId.value, 301);
    expect(controller.initiativeId.value, isNull);
    expect(controller.isGlobalScope, isFalse);
  });

  test('CompanyScopeController clears scope correctly', () {
    final controller = Get.put(CompanyScopeController());
    
    controller.setScope(operatingUnitId: 201, offeringId: 301, initiativeId: 401);
    controller.clearScope();
    
    expect(controller.operatingUnitId.value, isNull);
    expect(controller.offeringId.value, isNull);
    expect(controller.initiativeId.value, isNull);
    expect(controller.isGlobalScope, isTrue);
  });
}

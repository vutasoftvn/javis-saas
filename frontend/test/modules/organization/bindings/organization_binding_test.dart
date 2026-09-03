import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/organization/bindings/organization_binding.dart';
import 'package:frontend/modules/organization/controllers/organization_controller.dart';

void main() {
  setUp(() {
    Get.reset();
    Get.testMode = true;
  });

  test('registers OrganizationController', () {
    OrganizationBinding().dependencies();
    expect(Get.isRegistered<OrganizationController>(), isTrue);
  });
}

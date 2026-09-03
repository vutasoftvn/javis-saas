import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/skills/bindings/skill_registry_binding.dart';
import 'package:frontend/modules/skills/controllers/skill_registry_controller.dart';

void main() {
  setUp(() {
    Get.reset();
    Get.testMode = true;
  });

  test('registers SkillRegistryController', () {
    SkillRegistryBinding().dependencies();
    expect(Get.isRegistered<SkillRegistryController>(), isTrue);
  });
}

import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/workspace_runtime/bindings/workspace_runtime_binding.dart';
import 'package:frontend/modules/workspace_runtime/controllers/workspace_runtime_controller.dart';

void main() {
  setUp(() {
    Get.reset();
    Get.testMode = true;
  });

  test('registers WorkspaceRuntimeController', () {
    WorkspaceRuntimeBinding().dependencies();
    expect(Get.isRegistered<WorkspaceRuntimeController>(), isTrue);
  });
}

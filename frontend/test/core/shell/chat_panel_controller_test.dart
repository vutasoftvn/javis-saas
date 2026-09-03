import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/shell/app_shell_controller.dart';
import 'package:frontend/core/shell/chat_panel_controller.dart';

void main() {
  test('toggle flips isOpen, open/close set it explicitly', () {
    final controller = ChatPanelController();
    expect(controller.isOpen.value, isFalse);

    controller.toggle();
    expect(controller.isOpen.value, isTrue);

    controller.toggle();
    expect(controller.isOpen.value, isFalse);

    controller.open();
    expect(controller.isOpen.value, isTrue);

    controller.close();
    expect(controller.isOpen.value, isFalse);
  });

  test('updatePosition stores the latest offset', () {
    final controller = ChatPanelController();
    expect(controller.position.value, isNull);

    controller.updatePosition(const Offset(100, 200));
    expect(controller.position.value, const Offset(100, 200));
  });

  test('ensureShellDependencies registers ChatPanelController', () {
    Get.reset();
    Get.testMode = true;
    AppShellController.ensureShellDependencies();
    expect(Get.isRegistered<ChatPanelController>(), isTrue);
  });
}

import 'package:flutter/material.dart';
import 'package:get/get.dart';

/// State chrome-level cho khung chat nổi kéo-thả — thay cho voice orb
/// (`FloatingVoiceHologram`) trước đây chỉ toggle voice. Đăng ký qua
/// `AppShellController.ensureShellDependencies()`, dùng chung bởi mọi nơi
/// hiển thị orb/panel (`AppShell` cho 21 module có sidebar,
/// `HologramHubView` cho Hub không sidebar).
class ChatPanelController extends GetxController {
  final isOpen = false.obs;
  final Rxn<Offset> position = Rxn<Offset>();

  void open() => isOpen.value = true;
  void close() => isOpen.value = false;
  void toggle() => isOpen.value = !isOpen.value;
  void updatePosition(Offset offset) => position.value = offset;
}

import 'package:get/get.dart';

import '../presentation/controllers/voice_session_controller.dart';

/// Registers [VoiceSessionController] the same way every other module in
/// this app registers its controllers - previously it was constructed
/// inline as a plain field on `HologramHubController`, bypassing GetX's
/// binding/DI convention entirely.
class RealtimeVoiceBinding extends Bindings {
  @override
  void dependencies() {
    if (!Get.isRegistered<VoiceSessionController>()) {
      Get.lazyPut<VoiceSessionController>(() => VoiceSessionController());
    }
  }
}

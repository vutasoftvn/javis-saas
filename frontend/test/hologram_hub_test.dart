import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/modules/hologram_hub/controllers/hologram_hub_controller.dart';
import 'package:frontend/modules/hologram_hub/presentation/widgets/miva_hologram_core.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({
      'auth_token': 'test_token',
      'workspace_id': 'ws_123',
    });
    Get.testMode = true;
  });

  tearDown(() {
    Get.reset();
  });

  group('HologramHubController Mobile Interaction & Active Listening', () {
    test('initial state has chat input inactive and voice not listening', () {
      final controller = HologramHubController();
      expect(controller.isChatInputActive.value, isFalse);
      expect(controller.isVoiceListening.value, isFalse);
      expect(controller.runtimeState.value, HologramRuntimeState.idle);
      expect(controller.mobileMessages, isEmpty);
    });

    test('openChatInput activates chat input mode', () {
      final controller = HologramHubController();
      controller.openChatInput();
      expect(controller.isChatInputActive.value, isTrue);
    });

    test('closeChatInput deactivates chat input mode and restores 2 icons', () {
      final controller = HologramHubController();
      controller.openChatInput();
      expect(controller.isChatInputActive.value, isTrue);

      controller.closeChatInput();
      expect(controller.isChatInputActive.value, isFalse);
    });

    test('toggleChatInput toggles state back and forth', () {
      final controller = HologramHubController();
      expect(controller.isChatInputActive.value, isFalse);

      controller.toggleChatInput();
      expect(controller.isChatInputActive.value, isTrue);

      controller.toggleChatInput();
      expect(controller.isChatInputActive.value, isFalse);
    });

    test('clearMobileHistory removes all mobile messages', () {
      final controller = HologramHubController();
      controller.mobileMessages.addAll([
        {'role': 'user', 'text': 'Hello'},
        {'role': 'assistant', 'text': 'Hi!'},
      ]);
      expect(controller.mobileMessages.length, 2);

      controller.clearMobileHistory();
      expect(controller.mobileMessages, isEmpty);
    });
  });
}

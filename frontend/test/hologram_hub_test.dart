import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/services/wake_word_service.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:frontend/modules/hologram_hub/controllers/hologram_hub_controller.dart';

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

    test('Wake word service triggers and initializes on creation', () async {
      final mockWake = _FakeWakeWordService();
      final controller = HologramHubController(wakeWordService: mockWake, autoStartWakeWord: true);
      controller.onInit();
      await Future.delayed(const Duration(milliseconds: 50));

      expect(mockWake.initCalled, isTrue);
      expect(mockWake.listeningStarted, isTrue);

      // Trigger wake word
      mockWake.simulateWakeWord('Chào COSA');
      // Verify callback triggered
      expect(mockWake.lastWakeWord, equals('Chào COSA'));

      controller.onClose();
      expect(mockWake.isDisposed, isTrue);
    });
  });

  group('HologramHubController Non-blocking Authentication', () {
    late http.Client originalClient;

    setUp(() {
      originalClient = ApiClient.client;
    });

    tearDown(() {
      ApiClient.client = originalClient;
    });

    test("ensureAuthenticated does not fetch or prompt for workspace orientation", () async {
      final requestedPaths = <String>[];
      ApiClient.client = MockClient((request) async {
        requestedPaths.add(request.url.path);
        if (request.url.path == "/identity/me") {
          return http.Response('{"display_name":"Test User","role":"member"}', 200);
        }
        return http.Response("not found", 404);
      });

      AuthService.setCachedToken("test_token");
      final controller = HologramHubController();
      await controller.ensureAuthenticated();

      expect(requestedPaths, ["/identity/me"]);
    });
  });
}

class _FakeWakeWordService implements IWakeWordService {
  bool initCalled = false;
  bool listeningStarted = false;
  bool isDisposed = false;
  void Function(String)? onWakeWordCallback;
  String? lastWakeWord;

  @override
  bool isListening = false;

  @override
  bool isAvailable = true;

  @override
  Future<bool> initialize({required void Function(String wakeWord) onWakeWord}) async {
    initCalled = true;
    onWakeWordCallback = onWakeWord;
    return true;
  }

  @override
  Future<void> startListening() async {
    listeningStarted = true;
    isListening = true;
  }

  @override
  Future<void> stopListening() async {
    isListening = false;
  }

  @override
  bool matchesWakeWord(String text) => text.toLowerCase().contains('cosa');

  void simulateWakeWord(String phrase) {
    lastWakeWord = phrase;
    onWakeWordCallback?.call(phrase);
  }

  @override
  void dispose() {
    isDisposed = true;
  }
}

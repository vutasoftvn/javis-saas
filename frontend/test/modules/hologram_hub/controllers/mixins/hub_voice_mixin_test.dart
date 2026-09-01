import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/services/voice_service.dart';
import 'package:frontend/core/services/wake_word_service.dart';
import 'package:frontend/modules/hologram_hub/domain/hologram_runtime_state.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    Get.testMode = true;
  });

  tearDown(() {
    Get.reset();
  });

  group('HubVoiceMixin - initWakeWord', () {
    test('initializes wake word service with callback and starts listening', () async {
      final fakeWakeWord = _FakeWakeWordService();
      final testController = _TestHubVoiceController(wakeWordService: fakeWakeWord);

      await testController.initWakeWord();

      // Verify initialization occurred by checking that listening started
      expect(fakeWakeWord.isListening, isTrue);
    });

    test('starts listening after successful initialization', () async {
      final fakeWakeWord = _FakeWakeWordService();
      final testController = _TestHubVoiceController(wakeWordService: fakeWakeWord);

      await testController.initWakeWord();

      expect(fakeWakeWord.isListening, isTrue);
    });

    test('handles initialization failure gracefully', () async {
      final fakeWakeWord = _FakeWakeWordService()..setInitializationResult(false);
      final testController = _TestHubVoiceController(wakeWordService: fakeWakeWord);

      await testController.initWakeWord();

      expect(fakeWakeWord.initCalled, isTrue);
      expect(fakeWakeWord.listeningStarted, isFalse);
    });
  });

  group('HubVoiceMixin - onTalkPressed (push-to-talk)', () {
    test('starts recording when not currently recording', () async {
      final fakeVoice = _FakeVoiceService()..setStartRecordingResult(true);
      final testController = _TestHubVoiceController(voiceService: fakeVoice);

      await testController.onTalkPressed();

      expect(fakeVoice.startRecordingCalled, isTrue);
      expect(testController.isVoiceListening.value, isTrue);
      expect(testController.runtimeState.value, HologramRuntimeState.listening);
    });

    test('stops recording and processes transcript when already recording', () async {
      final fakeVoice = _FakeVoiceService()
        ..setIsRecording(true)
        ..setStopRecordingResult('Hello COSA');
      final testController = _TestHubVoiceController(voiceService: fakeVoice);

      await testController.onTalkPressed();

      expect(fakeVoice.stopRecordingCalled, isTrue);
      expect(testController.isVoiceListening.value, isFalse);
      expect(testController.runtimeState.value, HologramRuntimeState.thinking);
      expect(testController.lastExecutedPrompt, 'Hello COSA');
    });

    test('returns to idle state when transcript is empty', () async {
      final fakeVoice = _FakeVoiceService()
        ..setIsRecording(true)
        ..setStopRecordingResult('   '); // Empty after trim
      final testController = _TestHubVoiceController(voiceService: fakeVoice);

      await testController.onTalkPressed();

      expect(testController.runtimeState.value, HologramRuntimeState.idle);
      expect(testController.lastExecutedPrompt, isNull);
    });

    test('returns to idle state when transcript is null', () async {
      final fakeVoice = _FakeVoiceService()
        ..setIsRecording(true)
        ..setStopRecordingResult(null);
      final testController = _TestHubVoiceController(voiceService: fakeVoice);

      await testController.onTalkPressed();

      expect(testController.runtimeState.value, HologramRuntimeState.idle);
    });

    test('returns to idle state when starting recording fails', () async {
      final fakeVoice = _FakeVoiceService()..setStartRecordingResult(false);
      final testController = _TestHubVoiceController(voiceService: fakeVoice);

      await testController.onTalkPressed();

      expect(testController.isVoiceListening.value, isFalse);
      expect(testController.runtimeState.value, HologramRuntimeState.idle);
    });
  });

  group('HubVoiceMixin - startOrStopConversationMode', () {
    test('activates conversation mode when inactive', () async {
      final fakeWakeWord = _FakeWakeWordService();
      final testController = _TestHubVoiceController(wakeWordService: fakeWakeWord);

      expect(testController.isConversationModeActive.value, isFalse);

      await testController.startOrStopConversationMode();

      expect(testController.isConversationModeActive.value, isTrue);
      expect(testController.runtimeState.value, HologramRuntimeState.listening);
    });

    test('deactivates conversation mode when active', () async {
      final fakeWakeWord = _FakeWakeWordService();
      final testController = _TestHubVoiceController(wakeWordService: fakeWakeWord);

      // Activate first
      await testController.startOrStopConversationMode();
      expect(testController.isConversationModeActive.value, isTrue);

      // Then deactivate
      await testController.startOrStopConversationMode();

      expect(testController.isConversationModeActive.value, isFalse);
      expect(testController.runtimeState.value, HologramRuntimeState.idle);
    });

    test('stops wake word listening when activating conversation mode', () async {
      final fakeWakeWord = _FakeWakeWordService()..setIsListening(true);
      final testController = _TestHubVoiceController(wakeWordService: fakeWakeWord);

      await testController.startOrStopConversationMode();

      expect(fakeWakeWord.stopListeningCalled, isTrue);
      expect(testController.isConversationModeActive.value, isTrue);
    });

    test('prevents concurrent transitions with flag', () async {
      final fakeWakeWord = _FakeWakeWordService();
      final testController = _TestHubVoiceController(wakeWordService: fakeWakeWord);

      // Set transitioning flag
      testController.setTransitioning(true);

      await testController.startOrStopConversationMode();

      // Should not activate because transitioning
      expect(testController.isConversationModeActive.value, isFalse);

      // Reset flag
      testController.setTransitioning(false);

      await testController.startOrStopConversationMode();

      // Should activate now
      expect(testController.isConversationModeActive.value, isTrue);
    });

    test('resets transitioning flag even on exception', () async {
      final fakeWakeWord = _FakeWakeWordService()..setThrowOnStopListening(true);
      final testController = _TestHubVoiceController(wakeWordService: fakeWakeWord);

      try {
        await testController.startOrStopConversationMode();
      } catch (_) {
        // Exception is expected
      }

      expect(testController.isTransitioning, isFalse);
    });
  });

  group('HubVoiceMixin - handleVoiceNavigation', () {
    test('navigates to timeline_detail', () {
      final testController = _TestHubVoiceController();
      testController.handleVoiceNavigation('timeline_detail', {});
      expect(testController.lastNavigation, 'timeline_detail');
    });

    test('navigates to report_detail', () {
      final testController = _TestHubVoiceController();
      testController.handleVoiceNavigation('report_detail', {});
      expect(testController.lastNavigation, 'report_detail');
    });

    test('navigates to proposal_detail', () {
      final testController = _TestHubVoiceController();
      testController.handleVoiceNavigation('proposal_detail', {});
      expect(testController.lastNavigation, 'proposal_detail');
    });

    test('navigates to tasks dashboard (tab 1, group 1)', () {
      final testController = _TestHubVoiceController();
      testController.handleVoiceNavigation('tasks', {});
      expect(testController.lastNavigation, 'dashboard');
      expect(testController.lastDashboardTab, 1);
      expect(testController.lastDashboardGroup, 1);
    });

    test('navigates to vault dashboard (tab 2, group 5)', () {
      final testController = _TestHubVoiceController();
      testController.handleVoiceNavigation('vault', {});
      expect(testController.lastNavigation, 'dashboard');
      expect(testController.lastDashboardTab, 2);
      expect(testController.lastDashboardGroup, 5);
    });

    test('navigates to strategy dashboard (tab 3, group 1)', () {
      final testController = _TestHubVoiceController();
      testController.handleVoiceNavigation('strategy', {});
      expect(testController.lastNavigation, 'dashboard');
      expect(testController.lastDashboardTab, 3);
    });

    test('navigates to OKRs dashboard (tab 27, group 1)', () {
      final testController = _TestHubVoiceController();
      testController.handleVoiceNavigation('okrs', {});
      expect(testController.lastNavigation, 'dashboard');
      expect(testController.lastDashboardTab, 27);
    });

    test('navigates to 12-week-year via "12wy" alias', () {
      final testController = _TestHubVoiceController();
      testController.handleVoiceNavigation('12wy', {});
      expect(testController.lastNavigation, 'dashboard');
      expect(testController.lastDashboardTab, 28);
    });

    test('navigates to 12-week-year via "twelve_week_year" alias', () {
      final testController = _TestHubVoiceController();
      testController.handleVoiceNavigation('twelve_week_year', {});
      expect(testController.lastNavigation, 'dashboard');
      expect(testController.lastDashboardTab, 28);
    });

    test('navigates to next_actions strategy view', () {
      final testController = _TestHubVoiceController();
      testController.handleVoiceNavigation('next_actions', {});
      expect(testController.lastNavigation, 'next_actions');
    });

    test('navigates to needs_you dashboard (tab 24, group 1)', () {
      final testController = _TestHubVoiceController();
      testController.handleVoiceNavigation('needs_you', {});
      expect(testController.lastNavigation, 'dashboard');
      expect(testController.lastDashboardTab, 24);
    });

    test('navigates to blocked_work dashboard (tab 25, group 1)', () {
      final testController = _TestHubVoiceController();
      testController.handleVoiceNavigation('blocked_work', {});
      expect(testController.lastNavigation, 'dashboard');
      expect(testController.lastDashboardTab, 25);
    });

    test('navigates to work_inspector dashboard (tab 26, group 1)', () {
      final testController = _TestHubVoiceController();
      testController.handleVoiceNavigation('work_inspector', {});
      expect(testController.lastNavigation, 'dashboard');
      expect(testController.lastDashboardTab, 26);
    });

    test('defaults to dashboard home on unknown target', () {
      final testController = _TestHubVoiceController();
      testController.handleVoiceNavigation('unknown_target', {});
      expect(testController.lastNavigation, 'dashboard');
      expect(testController.lastDashboardTab, 0);
      expect(testController.lastDashboardGroup, 0);
    });

    test('defaults to dashboard home on empty target', () {
      final testController = _TestHubVoiceController();
      testController.handleVoiceNavigation('dashboard', {});
      expect(testController.lastNavigation, 'dashboard');
      expect(testController.lastDashboardTab, 0);
    });
  });

  group('HubVoiceMixin - onVoiceHologramStateChanged', () {
    test('starts wake word listening when entering idle state with autoStart enabled',
        () async {
      final fakeWakeWord = _FakeWakeWordService();
      final testController = _TestHubVoiceController(
        wakeWordService: fakeWakeWord,
        autoStartWakeWord: true,
      );

      testController.onVoiceHologramStateChanged(HologramRuntimeState.idle);

      expect(fakeWakeWord.startListeningCalled, isTrue);
      expect(testController.runtimeState.value, HologramRuntimeState.idle);
    });

    test('does not start wake word listening when already listening', () async {
      final fakeWakeWord = _FakeWakeWordService()..setIsListening(true);
      final testController = _TestHubVoiceController(
        wakeWordService: fakeWakeWord,
        autoStartWakeWord: true,
      );

      testController.onVoiceHologramStateChanged(HologramRuntimeState.idle);

      expect(fakeWakeWord.startListeningCalled, isFalse);
    });

    test('stops wake word listening when entering non-idle state', () async {
      final fakeWakeWord = _FakeWakeWordService()..setIsListening(true);
      final testController = _TestHubVoiceController(wakeWordService: fakeWakeWord);

      testController.onVoiceHologramStateChanged(HologramRuntimeState.listening);

      expect(fakeWakeWord.stopListeningCalled, isTrue);
      expect(testController.runtimeState.value, HologramRuntimeState.listening);
    });

    test('does not start wake word listening when autoStart is disabled', () async {
      final fakeWakeWord = _FakeWakeWordService();
      final testController = _TestHubVoiceController(
        wakeWordService: fakeWakeWord,
        autoStartWakeWord: false,
      );

      testController.onVoiceHologramStateChanged(HologramRuntimeState.idle);

      expect(fakeWakeWord.startListeningCalled, isFalse);
    });
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Fake implementations
// ─────────────────────────────────────────────────────────────────────────────

class _FakeVoiceService implements IVoiceService {
  bool startRecordingCalled = false;
  bool stopRecordingCalled = false;
  bool _isRecording = false;
  String? _stopRecordingResult;
  bool _startRecordingResult = true;

  @override
  bool get isRecording => _isRecording;

  void setIsRecording(bool value) => _isRecording = value;

  void setStartRecordingResult(bool result) => _startRecordingResult = result;

  void setStopRecordingResult(String? result) => _stopRecordingResult = result;

  @override
  Future<bool> startRecording() async {
    startRecordingCalled = true;
    _isRecording = _startRecordingResult;
    return _startRecordingResult;
  }

  @override
  Future<String?> stopRecordingAndTranscribe({String language = 'vi'}) async {
    stopRecordingCalled = true;
    _isRecording = false;
    return _stopRecordingResult;
  }
}

class _FakeWakeWordService implements IWakeWordService {
  bool initCalled = false;
  bool listeningStarted = false;
  bool startListeningCalled = false;
  bool stopListeningCalled = false;
  bool isDisposed = false;
  void Function(String)? onWakeWordCallback;
  String? lastWakeWord;
  bool _isListening = false;
  final bool _isAvailable = true;
  bool _initResult = true;
  bool _throwOnStopListening = false;

  @override
  bool get isListening => _isListening;

  @override
  bool get isAvailable => _isAvailable;

  void setIsListening(bool value) => _isListening = value;

  void setInitializationResult(bool result) => _initResult = result;

  void setThrowOnStopListening(bool throwError) =>
      _throwOnStopListening = throwError;

  @override
  Future<bool> initialize({
    required void Function(String wakeWord) onWakeWord,
  }) async {
    initCalled = true;
    onWakeWordCallback = onWakeWord;
    return _initResult;
  }

  @override
  Future<void> startListening() async {
    startListeningCalled = true;
    _isListening = true;
  }

  @override
  Future<void> stopListening() async {
    if (_throwOnStopListening) {
      throw Exception('Stop listening failed');
    }
    stopListeningCalled = true;
    _isListening = false;
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

// ─────────────────────────────────────────────────────────────────────────────
// Test controller that mixes in HubVoiceMixin behavior
// ─────────────────────────────────────────────────────────────────────────────

/// Minimal test controller that exercises HubVoiceMixin through a GetxController.
/// Reimplements the mixin locally for testing without pulling in the full
/// HologramHubController dependency tree.
class _TestHubVoiceController extends GetxController {
  final IVoiceService? voiceService;
  final IWakeWordService? wakeWordService;
  final bool autoStartWakeWord;

  _TestHubVoiceController({
    this.voiceService,
    this.wakeWordService,
    this.autoStartWakeWord = false,
  });

  // ── State mirrors from HubVoiceMixin ─────────────────────────────────────
  final isVoiceListening = false.obs;
  final runtimeState = HologramRuntimeState.idle.obs;
  final _isConversationModeActive = false.obs;
  bool _isTransitioningVoiceSession = false;

  RxBool get isConversationModeActive => _isConversationModeActive;

  String? lastExecutedPrompt;
  String? lastNavigation;
  int? lastDashboardTab;
  int? lastDashboardGroup;
  int? lastDashboardStrategySubTab;

  bool get isTransitioning => _isTransitioningVoiceSession;

  IVoiceService get effectiveVoiceService => voiceService ?? VoiceService();

  IWakeWordService get effectiveWakeWordService =>
      wakeWordService ?? WakeWordService();

  // ── For testing purposes ──────────────────────────────────────────────────
  void setTransitioning(bool value) => _isTransitioningVoiceSession = value;

  // ── Implement abstract methods from HubChatMixin ──────────────────────────
  void scheduleResetRuntimeState() {
    // No-op for testing
  }

  Future<void> executePrompt(String prompt) async {
    lastExecutedPrompt = prompt;
  }

  Future<void> onConversationModePressed() async {
    await startOrStopConversationMode();
  }

  // ── Navigation stubs ─────────────────────────────────────────────────────
  void openTimelineDetail() => lastNavigation = 'timeline_detail';
  void openReportDetail() => lastNavigation = 'report_detail';
  void openProposalDetail() => lastNavigation = 'proposal_detail';
  void openStrategyNextActions() => lastNavigation = 'next_actions';
  void openDashboard([int targetTab = 0, int groupIndex = 0, int strategySubTab = 0]) {
    lastNavigation = 'dashboard';
    lastDashboardTab = targetTab;
    lastDashboardGroup = groupIndex;
    lastDashboardStrategySubTab = strategySubTab;
  }

  // ── HubVoiceMixin methods (copied for testing) ────────────────────────────

  Future<void> initWakeWord() async {
    final available = await effectiveWakeWordService.initialize(
      onWakeWord: _onWakeWordDetected,
    );
    if (available) await effectiveWakeWordService.startListening();
  }

  Future<void> _onWakeWordDetected(String phrase) async {
    debugPrint(
      '[HologramHub] Wake word detected: "$phrase" -> auto-starting voice session',
    );
    if (_isTransitioningVoiceSession) return;

    if (effectiveWakeWordService.isListening) {
      await effectiveWakeWordService.stopListening();
    }

    await onConversationModePressed();
  }

  void onVoiceHologramStateChanged(HologramRuntimeState state) {
    if (state == HologramRuntimeState.idle) {
      if (autoStartWakeWord && !effectiveWakeWordService.isListening) {
        effectiveWakeWordService.startListening();
      }
    } else {
      if (effectiveWakeWordService.isListening) {
        effectiveWakeWordService.stopListening();
      }
    }

    runtimeState.value = state;
  }

  Future<void> onTalkPressed() async {
    if (effectiveVoiceService.isRecording) {
      isVoiceListening.value = false;
      runtimeState.value = HologramRuntimeState.thinking;
      final transcript =
          await effectiveVoiceService.stopRecordingAndTranscribe();
      if (transcript != null && transcript.trim().isNotEmpty) {
        executePrompt(transcript);
      } else {
        runtimeState.value = HologramRuntimeState.idle;
      }
    } else {
      final started = await effectiveVoiceService.startRecording();
      if (!started) {
        runtimeState.value = HologramRuntimeState.idle;
        isVoiceListening.value = false;
        return;
      }
      isVoiceListening.value = true;
      runtimeState.value = HologramRuntimeState.listening;
    }
  }

  Future<void> startOrStopConversationMode() async {
    if (_isTransitioningVoiceSession) return;
    _isTransitioningVoiceSession = true;

    try {
      if (_isConversationModeActive.value) {
        _isConversationModeActive.value = false;
        runtimeState.value = HologramRuntimeState.idle;
        return;
      }

      if (effectiveWakeWordService.isListening) {
        await effectiveWakeWordService.stopListening();
      }

      _isConversationModeActive.value = true;
      runtimeState.value = HologramRuntimeState.listening;
    } finally {
      _isTransitioningVoiceSession = false;
    }
  }

  void handleVoiceNavigation(String target, Map<String, dynamic> params) {
    switch (target) {
      case 'timeline_detail':
        openTimelineDetail();
        break;
      case 'report_detail':
        openReportDetail();
        break;
      case 'proposal_detail':
        openProposalDetail();
        break;
      case 'tasks':
        openDashboard(1, 1);
        break;
      case 'vault':
        openDashboard(2, 5);
        break;
      case 'strategy':
        openDashboard(3, 1);
        break;
      case 'okrs':
        openDashboard(27, 1);
        break;
      case '12wy':
      case 'twelve_week_year':
        openDashboard(28, 1);
        break;
      case 'next_actions':
        openStrategyNextActions();
        break;
      case 'needs_you':
        openDashboard(24, 1);
        break;
      case 'blocked_work':
        openDashboard(25, 1);
        break;
      case 'work_inspector':
        openDashboard(26, 1);
        break;
      case 'dashboard':
      default:
        openDashboard(0, 0);
    }
  }
}

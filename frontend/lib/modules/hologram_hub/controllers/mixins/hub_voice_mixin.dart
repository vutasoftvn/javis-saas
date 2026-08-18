import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/services/voice_service.dart';
import '../../../../core/services/wake_word_service.dart';
import '../../../realtime_voice/domain/hologram_state.dart';
import '../../../realtime_voice/presentation/controllers/voice_session_controller.dart';
import '../../domain/hologram_runtime_state.dart';

mixin HubVoiceMixin on GetxController {
  // ── Abstract service getters ─────────────────────────────────────────────
  VoiceService get voiceService;
  IWakeWordService get wakeWordService;
  bool get autoStartWakeWord;

  // ── Shared state from HubChatMixin ───────────────────────────────────────
  Rx<HologramRuntimeState> get runtimeState;
  void scheduleResetRuntimeState();
  Future<void> executePrompt(String prompt);
  Future<void> onConversationModePressed();

  // ── Observables ──────────────────────────────────────────────────────────
  final isVoiceListening = false.obs;

  // ── Wake word ────────────────────────────────────────────────────────────

  bool _isTransitioningVoiceSession = false;

  VoiceSessionController? get voiceSession =>
      Get.isRegistered<VoiceSessionController>()
          ? Get.find<VoiceSessionController>()
          : null;

  Future<void> initWakeWord() async {
    final available = await wakeWordService.initialize(
      onWakeWord: _onWakeWordDetected,
    );
    if (available) await wakeWordService.startListening();
  }

  Future<void> _onWakeWordDetected(String phrase) async {
    debugPrint(
      '[HologramHub] Wake word detected: "$phrase" -> auto-starting voice session',
    );
    if (_isTransitioningVoiceSession) return;

    if (wakeWordService.isListening) {
      await wakeWordService.stopListening();
    }

    final session = voiceSession;
    if (session != null && session.isActive.value) return;

    await onConversationModePressed();
  }

  void onVoiceHologramStateChanged(RealtimeHologramState state) {
    if (state == RealtimeHologramState.idle) {
      if (autoStartWakeWord && !wakeWordService.isListening) {
        wakeWordService.startListening();
      }
    } else {
      if (wakeWordService.isListening) wakeWordService.stopListening();
    }

    switch (state) {
      case RealtimeHologramState.idle:
        runtimeState.value = HologramRuntimeState.idle;
        break;
      case RealtimeHologramState.listening:
        runtimeState.value = HologramRuntimeState.listening;
        break;
      case RealtimeHologramState.thinking:
        runtimeState.value = HologramRuntimeState.thinking;
        break;
      case RealtimeHologramState.retrieving:
        runtimeState.value = HologramRuntimeState.retrieving;
        break;
      case RealtimeHologramState.acting:
        runtimeState.value = HologramRuntimeState.acting;
        break;
      case RealtimeHologramState.speaking:
        runtimeState.value = HologramRuntimeState.speaking;
        break;
      case RealtimeHologramState.error:
        runtimeState.value = HologramRuntimeState.error;
        break;
    }
  }

  // ── Push-to-talk ─────────────────────────────────────────────────────────

  Future<void> onTalkPressed() async {
    if (voiceService.isRecording) {
      isVoiceListening.value = false;
      runtimeState.value = HologramRuntimeState.thinking;
      final transcript = await voiceService.stopRecordingAndTranscribe();
      if (transcript != null && transcript.trim().isNotEmpty) {
        executePrompt(transcript);
      } else {
        runtimeState.value = HologramRuntimeState.idle;
      }
    } else {
      final started = await voiceService.startRecording();
      if (!started) {
        runtimeState.value = HologramRuntimeState.idle;
        isVoiceListening.value = false;
        return;
      }
      isVoiceListening.value = true;
      runtimeState.value = HologramRuntimeState.listening;
    }
  }

  // ── LiveKit conversation mode ─────────────────────────────────────────────

  RxBool get isConversationModeActive =>
      voiceSession?.isActive ?? false.obs;

  Future<void> startOrStopConversationMode() async {
    final session = voiceSession;
    if (session == null) return;
    if (_isTransitioningVoiceSession) return;
    _isTransitioningVoiceSession = true;

    try {
      if (session.isActive.value) {
        await session.stopVoiceSession();
        runtimeState.value = HologramRuntimeState.idle;
        return;
      }

      if (wakeWordService.isListening) {
        await wakeWordService.stopListening();
      }

      final deviceType = GetPlatform.isDesktop ? 'desktop' : 'mobile';
      final started = await session.startVoiceSession(
        deviceType: deviceType,
        onNavigate: handleVoiceNavigation,
      );
      if (!started && autoStartWakeWord && !wakeWordService.isListening) {
        wakeWordService.startListening();
      }
    } finally {
      _isTransitioningVoiceSession = false;
    }
  }

  // ── Voice navigation ──────────────────────────────────────────────────────

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

  // ── Must be implemented by HubCommandMixin ───────────────────────────────
  void openTimelineDetail();
  void openReportDetail();
  void openProposalDetail();
  void openStrategyNextActions();
  void openDashboard([int targetTab = 0, int groupIndex = 0, int strategySubTab = 0]);
}

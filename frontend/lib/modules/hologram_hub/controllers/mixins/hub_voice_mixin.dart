import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/services/voice_service.dart';
import '../../../../core/services/wake_word_service.dart';
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

  final bool _isTransitioningVoiceSession = false;

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

    await onConversationModePressed();
  }

  void onVoiceHologramStateChanged(HologramRuntimeState state) {
    if (state == HologramRuntimeState.idle) {
      if (autoStartWakeWord && !wakeWordService.isListening) {
        wakeWordService.startListening();
      }
    } else {
      if (wakeWordService.isListening) wakeWordService.stopListening();
    }

    runtimeState.value = state;
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

  bool _isTransitioningVoiceSession = false;
  final RxBool _isConversationModeActive = false.obs;
  RxBool get isConversationModeActive => _isConversationModeActive;

  Future<void> startOrStopConversationMode() async {
    if (_isTransitioningVoiceSession) return;
    _isTransitioningVoiceSession = true;

    try {
      if (_isConversationModeActive.value) {
        _isConversationModeActive.value = false;
        runtimeState.value = HologramRuntimeState.idle;
        return;
      }

      if (wakeWordService.isListening) {
        await wakeWordService.stopListening();
      }

      _isConversationModeActive.value = true;
      runtimeState.value = HologramRuntimeState.listening;
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

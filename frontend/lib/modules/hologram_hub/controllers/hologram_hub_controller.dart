import 'dart:async';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/network/realtime_service.dart';
import '../../../core/services/voice_service.dart';
import '../../../core/routing/app_routes.dart';
import '../../../data/services/auth_service.dart';
import '../../../data/services/hub_service.dart';
import '../../../data/services/strategy_service.dart';
import '../../dashboard/controllers/dashboard_controller.dart';
import '../../chat/controllers/chat_controller.dart';
import '../presentation/widgets/miva_hologram_core.dart';

class HologramHubController extends GetxController {
  final AuthService _authService = AuthService();
  final HubService _hubService = HubService();
  final StrategyService _strategyService = StrategyService();
  final RealtimeService _realtimeService = RealtimeService();
  final VoiceService _voiceService = VoiceService();

  final isLoading = false.obs;
  final hubSummary = Rxn<Map<String, dynamic>>();
  final runtimeState = HologramRuntimeState.idle.obs;

  // mCOSA V12 Sprint 10 — CEO Next Best Actions Brief (Spec §37, §50)
  final ceoNextActions = <dynamic>[].obs;

  final currentTime = ''.obs;
  final currentDate = ''.obs;
  final userName = 'Dzu Nguyen'.obs;
  final userRole = 'Founder Mode'.obs;

  Timer? _clockTimer;
  Timer? _refreshTimer;
  Worker? _sendWorker;
  Timer? _resetStateTimer;

  @override
  void onInit() {
    super.onInit();
    _ensureAuthenticated();
    _updateClock();
    _clockTimer = Timer.periodic(const Duration(seconds: 1), (_) => _updateClock());
    loadHubSummary();
    loadCeoNextActions();
    _refreshTimer = Timer.periodic(const Duration(seconds: 60), (_) {
      loadHubSummary(showLoading: false);
      loadCeoNextActions();
    });

    // Connect to real-time SSE stream
    _realtimeService.connect();
    _realtimeService.addListener(_onRealtimeEvent);
  }

  Future<void> _ensureAuthenticated() async {
    if (!AuthService.isAuthenticated) {
      await _authService.logout();
      Get.offAllNamed(AppRoutes.login);
      return;
    }
    final me = await _authService.getMe();
    if (me == null) {
      debugPrint('[HologramHub] Token không hợp lệ hoặc đã hết hạn -> Tự động chuyển về màn Đăng nhập');
      await _authService.logout();
      Get.offAllNamed(AppRoutes.login);
      return;
    }
    if (me['display_name'] != null && (me['display_name'] as String).isNotEmpty) {
      userName.value = me['display_name'] as String;
    }
    if (me['role'] != null) {
      userRole.value = me['role'] == 'admin' ? 'Founder Mode' : (me['role'] as String);
    }
  }

  Future<void> logout() async {
    await _authService.logout();
    Get.offAllNamed(AppRoutes.login);
  }

  @override
  void onClose() {
    _clockTimer?.cancel();
    _refreshTimer?.cancel();
    _resetStateTimer?.cancel();
    _sendWorker?.dispose();
    _realtimeService.removeListener(_onRealtimeEvent);
    super.onClose();
  }

  void _onRealtimeEvent(String eventType, Map<String, dynamic> data) {
    debugPrint('[HologramHub] Received realtime event: $eventType');
    loadHubSummary(showLoading: false);
    loadCeoNextActions();
  }

  void _updateClock() {
    final now = DateTime.now();
    final hour = now.hour.toString().padLeft(2, '0');
    final minute = now.minute.toString().padLeft(2, '0');
    currentTime.value = '$hour:$minute';

    final weekdays = [
      'Thứ 2',
      'Thứ 3',
      'Thứ 4',
      'Thứ 5',
      'Thứ 6',
      'Thứ 7',
      'Chủ nhật'
    ];
    final weekday = weekdays[now.weekday - 1];
    currentDate.value = '$weekday, ${now.day} tháng ${now.month}, ${now.year}';
  }

  Future<void> loadHubSummary({bool showLoading = true}) async {
    if (showLoading) isLoading.value = true;
    try {
      final prefs = await SharedPreferences.getInstance();
      final wsId = prefs.getString('workspace_id');

      if (wsId == null || wsId.isEmpty) {
        final me = await _authService.getMe();
        if (me != null && me['display_name'] != null) {
          userName.value = me['display_name'] as String;
        }
      }

      final data = await _hubService.getHubSummary();
      if (data != null) {
        hubSummary.value = data;
      }
    } catch (e) {
      debugPrint('Error loading hub summary: $e');
    } finally {
      if (showLoading) isLoading.value = false;
    }
  }

  Future<void> loadCeoNextActions() async {
    try {
      ceoNextActions.value = await _strategyService.getCeoNextActions(limit: 3);
    } catch (e) {
      debugPrint('[HologramHub] Error loading CEO next actions: $e');
    }
  }

  /// Mở module Chiến lược & OKRs (nơi CEO Next Best Actions được xử lý đầy đủ - Spec §50).
  void openStrategyNextActions() {
    openDashboard(3, 2); // Chiến lược & OKRs
  }

  void openDashboard([int targetTab = 0, int groupIndex = 0]) {
    if (Get.isRegistered<DashboardController>()) {
      final dashCtrl = Get.find<DashboardController>();
      dashCtrl.changePage(targetTab, groupIndex);
    }
    Get.toNamed(AppRoutes.dashboard);
  }

  void handleQuickCommand(String command) {
    if (command == 'Tổng quan hôm nay') {
      executePrompt('Tóm tắt tổng quan công việc, OKRs và tình hình vận hành hôm nay.');
    } else if (command == 'Kiểm tra công việc') {
      openDashboard(1, 1); // Tasks
    } else if (command == 'Mở Knowledge Studio') {
      openDashboard(2, 2); // Vault
    } else if (command == 'Báo cáo tài chính') {
      executePrompt('Tạo báo cáo tóm tắt tài chính và các chỉ số vận hành gần nhất.');
    } else {
      executePrompt(command);
    }
  }

  void executePrompt(String prompt) {
    runtimeState.value = HologramRuntimeState.thinking;
    openDashboard(0, 0); // Open Chat

    if (Get.isRegistered<ChatController>()) {
      final chatCtrl = Get.find<ChatController>();
      chatCtrl.sendMessage(prompt);
      _watchSendResult(chatCtrl);
    }
  }

  /// Reflects the orb's runtime state off the real outcome of the chat send
  /// (success/error), instead of leaving it stuck on "thinking" forever.
  void _watchSendResult(ChatController chatCtrl) {
    _sendWorker?.dispose();
    _resetStateTimer?.cancel();
    _sendWorker = ever<bool>(chatCtrl.isSending, (sending) {
      if (sending) return;
      final messages = chatCtrl.messages;
      final lastStatus = messages.isNotEmpty
          ? (messages.last as Map)['status'] as String?
          : null;
      runtimeState.value = lastStatus == 'error'
          ? HologramRuntimeState.error
          : HologramRuntimeState.success;
      _resetStateTimer?.cancel();
      _resetStateTimer = Timer(const Duration(seconds: 2), () {
        runtimeState.value = HologramRuntimeState.idle;
      });
      _sendWorker?.dispose();
      _sendWorker = null;
    });
  }

  Future<void> onTalkPressed() async {
    if (_voiceService.isRecording) {
      runtimeState.value = HologramRuntimeState.thinking;
      final transcript = await _voiceService.stopRecordingAndTranscribe();
      if (transcript != null && transcript.trim().isNotEmpty) {
        Get.snackbar(
          'Đã ghi nhận giọng nói',
          transcript,
          backgroundColor: const Color(0xFF00F0FF).withValues(alpha: 0.2),
          colorText: const Color(0xFF00F0FF),
          icon: const Icon(Icons.mic, color: Color(0xFF00F0FF)),
          snackPosition: SnackPosition.TOP,
          duration: const Duration(seconds: 2),
        );
        executePrompt(transcript);
      } else {
        runtimeState.value = HologramRuntimeState.idle;
      }
    } else {
      final started = await _voiceService.startRecording();
      if (!started) {
        // Don't claim to be listening when the mic never actually started
        // (permission denied, or web platform not supported yet).
        runtimeState.value = HologramRuntimeState.idle;
        Get.snackbar(
          'Không thể ghi âm',
          'Chưa có quyền truy cập micro, hoặc nền tảng hiện tại chưa hỗ trợ ghi âm giọng nói.',
          backgroundColor: const Color(0xFFEF4444).withValues(alpha: 0.2),
          colorText: const Color(0xFFEF4444),
          icon: const Icon(Icons.mic_off, color: Color(0xFFEF4444)),
          snackPosition: SnackPosition.TOP,
          duration: const Duration(seconds: 3),
        );
        return;
      }
      runtimeState.value = HologramRuntimeState.listening;
      Get.snackbar(
        'Đang lắng nghe...',
        'Nói mệnh lệnh của bạn. Bấm lại nút Mic để xử lý.',
        backgroundColor: const Color(0xFF00F0FF).withValues(alpha: 0.15),
        colorText: Colors.white,
        icon: const Icon(Icons.mic, color: Color(0xFF00F0FF)),
        snackPosition: SnackPosition.TOP,
        duration: const Duration(seconds: 4),
      );
    }
  }

  void onSettingsPressed() {
    openDashboard(13, 4); // Settings view
  }

  void onThemeToggle() {
    Get.snackbar(
      'Chế độ hiển thị',
      'COSA Hologram HUD đã được tối ưu hóa ở chế độ Stark Dark Cyberpunk.',
      backgroundColor: const Color(0xFF1E293B),
      colorText: Colors.white,
      snackPosition: SnackPosition.BOTTOM,
      duration: const Duration(seconds: 2),
    );
  }
}

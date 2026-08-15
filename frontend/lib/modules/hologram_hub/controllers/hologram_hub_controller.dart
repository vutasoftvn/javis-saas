import 'dart:async';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';
import '../../../core/network/realtime_service.dart';
import '../../../core/services/voice_service.dart';
import '../../../core/routing/app_routes.dart';
import '../../../data/services/auth_service.dart';
import '../../../data/services/hub_service.dart';
import '../../../data/services/strategy_service.dart';
import '../../../data/services/chat_service.dart';
import '../../../data/services/company_runtime_service.dart';
import '../../dashboard/controllers/dashboard_controller.dart';
import '../../realtime_voice/domain/hologram_state.dart';
import '../../realtime_voice/presentation/controllers/voice_session_controller.dart';
import '../presentation/widgets/miva_hologram_core.dart';

class HologramHubController extends GetxController {
  final AuthService _authService = AuthService();
  final HubService _hubService = HubService();
  final StrategyService _strategyService = StrategyService();
  final CompanyRuntimeService _runtimeService = CompanyRuntimeService();
  final RealtimeService _realtimeService = RealtimeService();
  final VoiceService _voiceService = VoiceService();
  final ChatService _chatService = ChatService();
  VoiceSessionController get _voiceSession => Get.find<VoiceSessionController>();
  final _uuid = const Uuid();

  String? _activeChatSessionId;
  StreamSubscription<Map<String, dynamic>>? _hubChatStreamSub;

  final isLoading = false.obs;
  final hubSummary = Rxn<Map<String, dynamic>>();
  final runtimeState = HologramRuntimeState.idle.obs;

  // mCOSA V12 Sprint 10 — CEO Next Best Actions Brief (Spec §37, §50)
  final ceoNextActions = <dynamic>[].obs;

  // mCOSA V13.1 — Founder Exception Queue
  final needsYouItems = <dynamic>[].obs;

  // Strategic Execution Loop Timeline
  final activeCycleTimeline = Rxn<Map<String, dynamic>>();

  // Mobile chat history (inline hologram display)
  final mobileMessages = <Map<String, String>>[].obs;
  final showMobileHistory = true.obs;
  final isChatInputActive = false.obs;
  final isVoiceListening = false.obs;

  void openChatInput() {
    isChatInputActive.value = true;
  }

  void closeChatInput() {
    isChatInputActive.value = false;
  }

  void toggleChatInput() {
    isChatInputActive.value = !isChatInputActive.value;
  }

  final currentTime = ''.obs;
  final currentDate = ''.obs;
  final userName = 'Dzu Nguyen'.obs;
  final userRole = 'Founder Mode'.obs;

  Timer? _clockTimer;
  Timer? _refreshTimer;
  Worker? _sendWorker;
  Worker? _voiceHologramWorker;
  Timer? _resetStateTimer;

  @override
  void onInit() {
    super.onInit();
    // Must await so workspace_id/brain_id are cached in SharedPrefs before any
    // chat session creation is attempted (race-condition fix).
    _ensureAuthenticated().then((_) {
      loadHubSummary();
      loadCeoNextActions();
      loadActiveCycleTimeline();
    });
    _updateClock();
    _clockTimer = Timer.periodic(const Duration(seconds: 1), (_) => _updateClock());
    _refreshTimer = Timer.periodic(const Duration(seconds: 60), (_) {
      loadHubSummary(showLoading: false);
      loadCeoNextActions();
      loadActiveCycleTimeline();
    });

    // Connect to real-time SSE stream
    _realtimeService.connect();
    _realtimeService.addListener(_onRealtimeEvent);

    // Translate the voice session's own state into this controller's
    // runtimeState - VoiceSessionController no longer knows about
    // HologramRuntimeState directly (see realtime_voice/domain/hologram_state.dart).
    _voiceHologramWorker = ever<RealtimeHologramState>(
      _voiceSession.hologramState,
      _onVoiceHologramStateChanged,
    );
  }

  void _onVoiceHologramStateChanged(RealtimeHologramState state) {
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
    _voiceHologramWorker?.dispose();
    _hubChatStreamSub?.cancel();
    _realtimeService.removeListener(_onRealtimeEvent);
    _voiceSession.stopVoiceSession();
    super.onClose();
  }

  void _onRealtimeEvent(String eventType, Map<String, dynamic> data) {
    debugPrint('[HologramHub] Received realtime event: $eventType');
    if (eventType == 'system.connected') return;
    loadHubSummary(showLoading: false);
    loadCeoNextActions();
    loadNeedsYou();
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
      await loadNeedsYou();
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

  Future<void> loadActiveCycleTimeline() async {
    try {
      final cycles = await _strategyService.getTwelveWeekCycles();
      if (cycles.isNotEmpty) {
        final activeCycle = cycles.firstWhere(
          (c) => c['status'] == 'active',
          orElse: () => cycles.first,
        );
        final cycleId = activeCycle['id']?.toString();
        if (cycleId != null) {
          activeCycleTimeline.value = await _strategyService.getCycleTimeline(cycleId);
        }
      }
    } catch (e) {
      debugPrint('[HologramHub] Error loading cycle timeline: $e');
    }
  }

  Future<void> loadNeedsYou() async {
    try {
      needsYouItems.value = await _runtimeService.getNeedsYou();
    } catch (e) {
      debugPrint('[HologramHub] Error loading Needs You items: $e');
    }
  }

  void openNeedsYou() {
    openDashboard(24, 1);
  }

  /// Mở module Chiến lược (Vision, Mission, Values) - Nền tảng doanh nghiệp.
  void openStrategyNextActions() {
    openDashboard(3, 1); // Chiến lược Vision, Mission, Values
  }

  /// Mở module OKRs (Mục tiêu & Kết quả Then chốt).
  void openOkrs() {
    openDashboard(27, 1); // OKRs
  }

  /// Mở module 12WY (Kế hoạch Thực thi 12 Tuần).
  void openTwelveWeekYear() {
    openDashboard(28, 1); // 12WY
  }

  void openDashboard([int targetTab = 0, int groupIndex = 0]) {
    if (Get.isRegistered<DashboardController>()) {
      final dashCtrl = Get.find<DashboardController>();
      dashCtrl.changePage(targetTab, groupIndex);
    }
    Get.toNamed(AppRoutes.dashboard);
  }

  void handleQuickCommand(String command) {
    final isMobile = Get.width < 600;

    if (command == 'Tổng quan hôm nay') {
      executePrompt('Tóm tắt tổng quan công việc, OKRs và tình hình vận hành hôm nay.');
    } else if (command == 'Kiểm tra công việc') {
      if (isMobile) {
        executePrompt('Báo cáo và kiểm tra danh sách các công việc, nhiệm vụ cần làm hôm nay.');
      } else {
        openDashboard(1, 1); // Tasks
      }
    } else if (command == 'Mở Knowledge Studio') {
      if (isMobile) {
        executePrompt('Tra cứu các tài liệu và kho kiến thức quan trọng gần đây.');
      } else {
        openDashboard(2, 5); // Vault (Knowledge group)
      }
    } else if (command == 'Báo cáo tài chính') {
      executePrompt('Tạo báo cáo tóm tắt tài chính và các chỉ số vận hành gần nhất.');
    } else {
      executePrompt(command);
    }
  }

  Future<void> executePrompt(String prompt) async {
    final trimmedPrompt = prompt.trim();
    if (trimmedPrompt.isEmpty) return;

    runtimeState.value = HologramRuntimeState.thinking;

    // 1. Add user message
    mobileMessages.add({'role': 'user', 'text': trimmedPrompt});
    showMobileHistory.value = true;

    // 2. Add an initial assistant placeholder for immediate feedback
    final int assistantIndex = mobileMessages.length;
    mobileMessages.add({
      'role': 'assistant',
      'text': '',
      'status': 'streaming',
    });

    try {
      // Ensure session exists. If the workspace_id / brain_id cache is stale
      // (e.g. after a cold-start that skipped the login flow), refresh via
      // getMe() so _chatService._scope() resolves correctly.
      if (_activeChatSessionId == null) {
        final prefs = await SharedPreferences.getInstance();
        if (prefs.getString('workspace_id') == null ||
            prefs.getString('brain_id') == null) {
          debugPrint('[HologramHub] workspace_id/brain_id missing – refreshing via getMe()');
          await _authService.getMe();
        }
        final session = await _chatService.createSession(title: 'COSA Hub Chat');
        debugPrint('[HologramHub] createSession response: $session');
        _activeChatSessionId = session?['id'] as String?;
      }

      if (_activeChatSessionId == null) {
        mobileMessages[assistantIndex] = {
          'role': 'assistant',
          'text': 'Không thể kết nối phiên làm việc với COSA Brain.',
          'status': 'error',
        };
        runtimeState.value = HologramRuntimeState.error;
        _scheduleResetRuntimeState();
        return;
      }

      // Send user message
      final userMsg = await _chatService.sendUserMessage(
        sessionId: _activeChatSessionId!,
        content: trimmedPrompt,
        clientMessageId: _uuid.v4(),
      );

      if (userMsg == null) {
        mobileMessages[assistantIndex] = {
          'role': 'assistant',
          'text': 'Không thể gửi tin nhắn đến máy chủ.',
          'status': 'error',
        };
        runtimeState.value = HologramRuntimeState.error;
        _scheduleResetRuntimeState();
        return;
      }

      // Stream assistant response in real-time
      _hubChatStreamSub?.cancel();
      String fullAssistantText = '';

      _hubChatStreamSub = _chatService
          .streamSession(
            _activeChatSessionId!,
            afterMessageId: userMsg['id'] as String?,
          )
          .listen(
        (event) {
          final type = event['type'];
          if (type == 'delta') {
            final chunk = (event['text'] as String?) ?? '';
            fullAssistantText += chunk;
            if (assistantIndex < mobileMessages.length) {
              mobileMessages[assistantIndex] = {
                'role': 'assistant',
                'text': fullAssistantText,
                'status': 'streaming',
              };
            }
          } else if (type == 'message') {
            final content = (event['content'] as String?) ?? (event['text'] as String?) ?? '';
            if (content.isNotEmpty) {
              fullAssistantText = content;
            }
            final status = event['status'] as String? ?? 'delivered';
            if (assistantIndex < mobileMessages.length) {
              mobileMessages[assistantIndex] = {
                'role': 'assistant',
                'text': fullAssistantText,
                'status': status,
              };
            }
            if (status == 'delivered' || status == 'error' || status == 'cancelled') {
              runtimeState.value = status == 'error'
                  ? HologramRuntimeState.error
                  : HologramRuntimeState.success;
              _scheduleResetRuntimeState();
              _hubChatStreamSub?.cancel();
            }
          }
        },
        onError: (err) async {
          debugPrint('[HologramHub] Stream error: $err, fallback fetching messages');
          try {
            final msgs = await _chatService.getMessages(_activeChatSessionId!);
            final lastAssistant = msgs.reversed.firstWhere(
              (m) => (m as Map)['role'] == 'assistant',
              orElse: () => null,
            );
            if (lastAssistant != null) {
              final content = (lastAssistant as Map)['content'] as String? ?? '';
              if (assistantIndex < mobileMessages.length) {
                mobileMessages[assistantIndex] = {
                  'role': 'assistant',
                  'text': content,
                  'status': 'delivered',
                };
              }
              runtimeState.value = HologramRuntimeState.success;
            } else {
              if (assistantIndex < mobileMessages.length) {
                mobileMessages[assistantIndex] = {
                  'role': 'assistant',
                  'text': 'Đã nhận yêu cầu nhưng máy chủ chưa phản hồi.',
                  'status': 'error',
                };
              }
              runtimeState.value = HologramRuntimeState.error;
            }
          } catch (_) {
            if (assistantIndex < mobileMessages.length) {
              mobileMessages[assistantIndex] = {
                'role': 'assistant',
                'text': 'Không thể kết nối đến máy chủ.',
                'status': 'error',
              };
            }
            runtimeState.value = HologramRuntimeState.error;
          }
          _scheduleResetRuntimeState();
        },
      );
    } catch (e) {
      debugPrint('[HologramHub] Error executing prompt: $e');
      if (assistantIndex < mobileMessages.length) {
        mobileMessages[assistantIndex] = {
          'role': 'assistant',
          'text': 'Lỗi tạo phản hồi: $e',
          'status': 'error',
        };
      }
      runtimeState.value = HologramRuntimeState.error;
      _scheduleResetRuntimeState();
    }
  }

  void _scheduleResetRuntimeState() {
    _resetStateTimer?.cancel();
    _resetStateTimer = Timer(const Duration(seconds: 2), () {
      runtimeState.value = HologramRuntimeState.idle;
    });
  }

  void clearMobileHistory() {
    mobileMessages.clear();
  }

  void toggleMobileHistory() {
    showMobileHistory.value = !showMobileHistory.value;
  }

  Future<void> onTalkPressed() async {
    if (_voiceService.isRecording) {
      isVoiceListening.value = false;
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
        runtimeState.value = HologramRuntimeState.idle;
        isVoiceListening.value = false;
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
      isVoiceListening.value = true;
      runtimeState.value = HologramRuntimeState.listening;
      Get.snackbar(
        'Đang lắng nghe chủ động...',
        'Hệ thống đang chủ động lắng nghe. Chạm lại nút Mic để kết thúc & xử lý.',
        backgroundColor: const Color(0xFF00F0FF).withValues(alpha: 0.18),
        colorText: Colors.white,
        icon: const Icon(Icons.graphic_eq, color: Color(0xFF00F0FF)),
        snackPosition: SnackPosition.TOP,
        duration: const Duration(seconds: 3),
      );
    }
  }

  /// LiveKit Conversation Mode (mCOSA V12.1 §15.2) - kept alongside the older
  /// push-to-talk `onTalkPressed()`/`VoiceService` flow above as a fallback,
  /// not a replacement.
  RxBool get isConversationModeActive => _voiceSession.isActive;

  Future<void> onConversationModePressed() async {
    if (_voiceSession.isActive.value) {
      await _voiceSession.stopVoiceSession();
      runtimeState.value = HologramRuntimeState.idle;
      return;
    }

    final deviceType = GetPlatform.isDesktop ? 'desktop' : 'mobile';
    final started = await _voiceSession.startVoiceSession(
      deviceType: deviceType,
      onNavigate: handleVoiceNavigation,
    );
    if (!started) {
      Get.snackbar(
        'Không thể bắt đầu phiên hội thoại',
        'Kiểm tra kết nối mạng hoặc thử lại sau.',
        backgroundColor: const Color(0xFFEF4444).withValues(alpha: 0.2),
        colorText: const Color(0xFFEF4444),
        icon: const Icon(Icons.mic_off, color: Color(0xFFEF4444)),
        snackPosition: SnackPosition.TOP,
        duration: const Duration(seconds: 3),
      );
    }
  }

  final activeContextualPage = 'none'.obs; // 'none', 'timeline_detail', 'report_detail', 'proposal_detail'
  final isContextPinned = false.obs;

  void openTimelineDetail() {
    activeContextualPage.value = 'timeline_detail';
  }

  void openReportDetail() {
    activeContextualPage.value = 'report_detail';
  }

  void openProposalDetail() {
    activeContextualPage.value = 'proposal_detail';
  }

  void closeContextualPage() {
    if (!isContextPinned.value) {
      activeContextualPage.value = 'none';
    }
  }

  void forceCloseContextualPage() {
    isContextPinned.value = false;
    activeContextualPage.value = 'none';
  }

  void togglePinContext() {
    isContextPinned.value = !isContextPinned.value;
  }

  /// Structured UI navigation event received from the voice agent's data
  /// channel (spec §57-58). `target` is validated server-side against a
  /// fixed whitelist in services/realtime_agent - anything unrecognized here
  /// falls back to opening chat rather than silently failing.
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
        openDashboard(3, 1); // Chiến lược Vision, Mission, Values
        break;
      case 'okrs':
        openDashboard(27, 1); // OKRs
        break;
      case '12wy':
      case 'twelve_week_year':
        openDashboard(28, 1); // 12WY
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

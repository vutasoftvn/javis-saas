import 'dart:async';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';
import '../../../core/network/realtime_service.dart';
import '../../../core/services/voice_service.dart';
import '../../../core/services/wake_word_service.dart';
import '../../../core/routing/app_routes.dart';
import '../../../data/services/auth_service.dart';
import '../../../data/services/hub_service.dart';
import '../../../data/services/strategy_service.dart';
import '../../../data/services/chat_service.dart';
import '../../../data/services/company_runtime_service.dart';
import '../../../data/services/control_plane_service.dart';
import '../../dashboard/controllers/dashboard_controller.dart';
import '../../realtime_voice/domain/hologram_state.dart';
import '../../realtime_voice/presentation/controllers/voice_session_controller.dart';
import '../presentation/widgets/miva_hologram_core.dart';
import '../views/widgets/mission_inspector_dialog.dart';

class HologramHubController extends GetxController {
  final AuthService _authService;
  final HubService _hubService;
  final StrategyService _strategyService;
  final CompanyRuntimeService _runtimeService;
  final RealtimeService _realtimeService;
  final VoiceService _voiceService;
  final ChatService _chatService;
  final ControlPlaneService _controlPlaneService;
  final IWakeWordService _wakeWordService;
  final bool autoStartWakeWord;

  HologramHubController({
    AuthService? authService,
    HubService? hubService,
    StrategyService? strategyService,
    CompanyRuntimeService? runtimeService,
    RealtimeService? realtimeService,
    VoiceService? voiceService,
    ChatService? chatService,
    ControlPlaneService? controlPlaneService,
    IWakeWordService? wakeWordService,
    this.autoStartWakeWord = true,
  }) : _authService = authService ?? AuthService(),
       _hubService = hubService ?? HubService(),
       _strategyService = strategyService ?? StrategyService(),
       _runtimeService = runtimeService ?? CompanyRuntimeService(),
       _realtimeService = realtimeService ?? RealtimeService(),
       _voiceService = voiceService ?? VoiceService(),
       _chatService = chatService ?? ChatService(),
       _controlPlaneService = controlPlaneService ?? ControlPlaneService(),
       _wakeWordService = wakeWordService ?? WakeWordService();

  VoiceSessionController? get _voiceSession =>
      Get.isRegistered<VoiceSessionController>() ? Get.find<VoiceSessionController>() : null;
  final _uuid = const Uuid();

  bool _isTransitioningVoiceSession = false;
  String? _activeChatSessionId;
  StreamSubscription<Map<String, dynamic>>? _hubChatStreamSub;

  final isLoading = false.obs;
  final hubSummary = Rxn<Map<String, dynamic>>();
  final commandCenterData = Rxn<Map<String, dynamic>>();
  final runtimeState = HologramRuntimeState.idle.obs;

  // mCOSA V12 Sprint 10 — CEO Next Best Actions Brief (Spec §37, §50)
  final ceoNextActions = <dynamic>[].obs;

  // mCOSA V13.1 — Founder Exception Queue
  final needsYouItems = <dynamic>[].obs;
  final resolvedProposalIds = <String>{}.obs;
  final snoozedProposalIds = <String>{}.obs;

  // Strategic Execution Loop Timeline
  final activeCycleTimeline = Rxn<Map<String, dynamic>>();

  // Agent activity & pending approvals (Control Plane)
  final pendingApprovals = <Map<String, dynamic>>[].obs;
  final agentRuns = <Map<String, dynamic>>[].obs;

  // Mobile chat history (inline hologram display)
  final mobileMessages = <Map<String, dynamic>>[].obs;
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
      loadCommandCenterData();
      loadCeoNextActions();
      loadActiveCycleTimeline();
      loadPendingApprovals();
      loadAgentRuns();
    });
    _updateClock();
    _clockTimer = Timer.periodic(const Duration(seconds: 1), (_) => _updateClock());
    _refreshTimer = Timer.periodic(const Duration(seconds: 60), (_) {
      loadHubSummary(showLoading: false);
      loadCommandCenterData();
      loadCeoNextActions();
      loadActiveCycleTimeline();
      loadPendingApprovals();
      loadAgentRuns();
    });

    // Connect to real-time SSE stream
    _realtimeService.connect();
    _realtimeService.addListener(_onRealtimeEvent);

    // Initialize Hands-free Wake Word Detection
    if (autoStartWakeWord) {
      _initWakeWord();
    }

    // Translate the voice session's own state into this controller's
    // runtimeState - VoiceSessionController no longer knows about
    // HologramRuntimeState directly (see realtime_voice/domain/hologram_state.dart).
    final voiceSession = _voiceSession;
    if (voiceSession != null) {
      _voiceHologramWorker = ever<RealtimeHologramState>(
        voiceSession.hologramState,
        _onVoiceHologramStateChanged,
      );
    }
  }

  Future<void> _initWakeWord() async {
    final available = await _wakeWordService.initialize(
      onWakeWord: _onWakeWordDetected,
    );
    if (available) {
      await _wakeWordService.startListening();
    }
  }

  Future<void> _onWakeWordDetected(String phrase) async {
    debugPrint('[HologramHub] Wake word detected: "$phrase" -> auto-starting voice session');
    if (_isTransitioningVoiceSession) return;

    if (_wakeWordService.isListening) {
      await _wakeWordService.stopListening();
    }

    final voiceSession = _voiceSession;
    if (voiceSession != null && voiceSession.isActive.value) {
      return;
    }

    await onConversationModePressed();
  }

  void _onVoiceHologramStateChanged(RealtimeHologramState state) {
    if (state == RealtimeHologramState.idle) {
      if (autoStartWakeWord && !_wakeWordService.isListening) {
        _wakeWordService.startListening();
      }
    } else {
      if (_wakeWordService.isListening) {
        _wakeWordService.stopListening();
      }
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
    _wakeWordService.dispose();
    _clockTimer?.cancel();
    _refreshTimer?.cancel();
    _resetStateTimer?.cancel();
    _sendWorker?.dispose();
    _voiceHologramWorker?.dispose();
    _hubChatStreamSub?.cancel();
    _realtimeService.removeListener(_onRealtimeEvent);
    _voiceSession?.stopVoiceSession();
    super.onClose();
  }

  void _onRealtimeEvent(String eventType, Map<String, dynamic> data) {
    debugPrint('[HologramHub] Received realtime event: $eventType');
    if (eventType == 'system.connected') return;

    if (eventType.startsWith('agent.')) {
      final state = data['state'] as String? ?? eventType.replaceFirst('agent.', '');
      switch (state) {
        case 'understanding':
        case 'routing':
          runtimeState.value = HologramRuntimeState.thinking;
          break;
        case 'priming':
          runtimeState.value = HologramRuntimeState.retrieving;
          break;
        case 'tool_running':
          runtimeState.value = HologramRuntimeState.acting;
          break;
        case 'waiting_approval':
          runtimeState.value = HologramRuntimeState.waitingApproval;
          break;
        case 'completed':
          runtimeState.value = HologramRuntimeState.success;
          _scheduleResetRuntimeState();
          break;
        case 'error':
          runtimeState.value = HologramRuntimeState.error;
          _scheduleResetRuntimeState();
          break;
        case 'idle':
          runtimeState.value = HologramRuntimeState.idle;
          break;
      }
    }

    loadHubSummary(showLoading: false);
    loadCommandCenterData(showLoading: false);
    loadCeoNextActions();
    loadNeedsYou();
    if (eventType.startsWith('agent.')) {
      loadPendingApprovals();
      loadAgentRuns();
    }
  }

  Future<void> loadCommandCenterData({bool showLoading = true}) async {
    if (showLoading && commandCenterData.value == null) isLoading.value = true;
    try {
      final data = await _hubService.getCommandCenterData();
      if (data != null) {
        commandCenterData.value = data;
      }
    } catch (e) {
      debugPrint('Error loading command center data: $e');
    } finally {
      if (showLoading) isLoading.value = false;
    }
  }

  Future<void> handleQuickApprove(String approvalId, String decision, [String? reason]) async {
    // Optimistic UI update: Remove approval from local list immediately
    if (commandCenterData.value != null) {
      final currentData = Map<String, dynamic>.from(commandCenterData.value!);
      final waitingList = List<dynamic>.from(currentData['waiting_for_you'] ?? []);
      waitingList.removeWhere((item) => (item['approval_id']?.toString() ?? '') == approvalId);
      currentData['waiting_for_you'] = waitingList;
      commandCenterData.value = currentData;
    }

    try {
      final res = await _hubService.quickApprove(
        approvalId: approvalId,
        decision: decision,
        reason: reason,
      );
      // Re-sync command center data
      await loadCommandCenterData(showLoading: false);
    } catch (e) {
      debugPrint('Error executing quick approve: $e');
      await loadCommandCenterData(showLoading: false);
    }
  }

  Future<void> openMissionInspector(String missionId) async {
    try {
      final detail = await _hubService.getMissionDetail(missionId);
      if (detail != null && Get.context != null) {
        MissionInspectorDialog.show(Get.context!, detail);
        return;
      }
    } catch (e) {
      debugPrint('openMissionInspector error: $e');
    }
    // Fallback: lookup in current commandCenterData active_missions
    if (commandCenterData.value != null && Get.context != null) {
      final missions = commandCenterData.value!['active_missions'] as List<dynamic>? ?? [];
      final found = missions.firstWhereOrNull((m) => m['mission_id']?.toString() == missionId);
      if (found != null) {
        MissionInspectorDialog.show(Get.context!, Map<String, dynamic>.from(found as Map));
        return;
      }
    }
    // Final fallback: open strategy dashboard
    openDashboard(3, 0);
  }

  Future<void> togglePriorityTask(String taskId) async {
    if (commandCenterData.value != null) {
      final currentData = Map<String, dynamic>.from(commandCenterData.value!);
      final priorities = List<dynamic>.from(currentData['today_priorities'] ?? []);
      for (var i = 0; i < priorities.length; i++) {
        final item = Map<String, dynamic>.from(priorities[i] as Map);
        if (item['id']?.toString() == taskId) {
          final isDone = item['status'] == 'done';
          item['status'] = isDone ? 'todo' : 'done';
          priorities[i] = item;
          break;
        }
      }
      currentData['today_priorities'] = priorities;
      commandCenterData.value = currentData;
    }
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

  Future<void> loadPendingApprovals() async {
    try {
      pendingApprovals.value = await _controlPlaneService.getPendingApprovals();
    } catch (e) {
      debugPrint('[HologramHub] Error loading pending approvals: $e');
    }
  }

  Future<void> loadAgentRuns() async {
    try {
      agentRuns.value = await _controlPlaneService.listRuns(limit: 5);
    } catch (e) {
      debugPrint('[HologramHub] Error loading agent runs: $e');
    }
  }

  Future<void> approveTaskCard(String approvalId) async {
    final ok = await _controlPlaneService.approveAction(approvalId);
    if (ok) {
      pendingApprovals.removeWhere((a) => (a['id'] ?? '').toString() == approvalId);
    }
  }

  Future<void> rejectTaskCard(String approvalId) async {
    final ok = await _controlPlaneService.rejectAction(approvalId);
    if (ok) {
      pendingApprovals.removeWhere((a) => (a['id'] ?? '').toString() == approvalId);
    }
  }

  Future<bool> resolveNeedsYouItem(String itemId, {String? actionName}) async {
    try {
      resolvedProposalIds.add(itemId);
      snoozedProposalIds.remove(itemId);

      // Cập nhật trạng thái proposals trong tin nhắn chat
      for (int i = 0; i < mobileMessages.length; i++) {
        final msg = Map<String, dynamic>.from(mobileMessages[i]);
        if (msg['proposals'] is List) {
          final props = (msg['proposals'] as List).map((p) {
            final pMap = Map<String, dynamic>.from(p as Map);
            if (pMap['id']?.toString() == itemId || pMap['proposal_id']?.toString() == itemId) {
              pMap['status'] = 'RESOLVED';
            }
            return pMap;
          }).toList();
          msg['proposals'] = props;
          mobileMessages[i] = msg;
        }
      }
      needsYouItems.removeWhere((item) => (item['id'] ?? '').toString() == itemId);

      final ok = await _runtimeService.resolveNeedsYou(itemId);
      if (ok) {
        await loadHubSummary(showLoading: false);
        await loadNeedsYou();
        await loadActiveCycleTimeline();

        final targetAction = actionName?.trim();
        if (targetAction != null && targetAction.isNotEmpty) {
          await executePrompt(
            'Tôi đã xác nhận & khởi tạo đề xuất: "$targetAction". '
            'Hãy xác nhận kết quả đã lưu vào hệ thống và đề xuất các bước tiếp theo cần triển khai ngay.',
          );
        }
        return true;
      }
    } catch (e) {
      debugPrint('[HologramHub] resolveNeedsYouItem error: $e');
    }
    return false;
  }

  Future<bool> snoozeNeedsYouItem(
    String itemId, {
    String? actionName,
    Duration duration = const Duration(days: 1),
  }) async {
    try {
      snoozedProposalIds.add(itemId);
      resolvedProposalIds.remove(itemId);

      // Cập nhật trạng thái proposals trong tin nhắn chat
      for (int i = 0; i < mobileMessages.length; i++) {
        final msg = Map<String, dynamic>.from(mobileMessages[i]);
        if (msg['proposals'] is List) {
          final props = (msg['proposals'] as List).map((p) {
            final pMap = Map<String, dynamic>.from(p as Map);
            if (pMap['id']?.toString() == itemId || pMap['proposal_id']?.toString() == itemId) {
              pMap['status'] = 'SNOOZED';
            }
            return pMap;
          }).toList();
          msg['proposals'] = props;
          mobileMessages[i] = msg;
        }
      }
      needsYouItems.removeWhere((item) => (item['id'] ?? '').toString() == itemId);

      final until = DateTime.now().add(duration);
      final ok = await _runtimeService.snoozeNeedsYou(itemId, until);
      if (ok) {
        await loadNeedsYou();

        final targetAction = actionName?.trim();
        if (targetAction != null && targetAction.isNotEmpty) {
          await executePrompt(
            'Tôi đã tạm hoãn đề xuất: "$targetAction". '
            'Hãy ghi chú lại và cho tôi biết có cần điều chỉnh thông tin gì không.',
          );
        }
        return true;
      }
    } catch (e) {
      debugPrint('[HologramHub] snoozeNeedsYouItem error: $e');
    }
    return false;
  }


  void openAgentActivity() {
    activeContextualPage.value = 'agent_activity';
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

  // 3 Operating Modes: 'founder', 'operator', 'developer'
  final operatingMode = 'founder'.obs;
  final latestTelemetry = Rxn<Map<String, dynamic>>();

  void setOperatingMode(String mode) {
    operatingMode.value = mode;
    userRole.value = mode == 'developer'
        ? 'Developer Mode'
        : (mode == 'operator' ? 'Operator Mode' : 'Founder Mode');
  }

  void handleQuickCommand(String command) {
    if (command == 'Tổng quan hôm nay' || command == 'daily_brief') {
      runQuickAction('daily_brief', 'Tổng quan vận hành hôm nay');
    } else if (command == 'Kiểm tra công việc' || command == 'Kiểm tra tiến độ OKRs' || command == 'okr_check') {
      runQuickAction('okr_check', 'Kiểm tra tiến độ OKRs');
    } else if (command == 'Nhiệm vụ ưu tiên' || command == 'Nhiệm vụ cần ưu tiên giải quyết' || command == 'task_prioritize') {
      runQuickAction('task_prioritize', 'Nhiệm vụ cần ưu tiên giải quyết');
    } else if (command == 'Báo cáo tài chính' || command == 'Tóm tắt tài chính' || command == 'finance_summary') {
      runQuickAction('finance_summary', 'Báo cáo tóm tắt tài chính');
    } else {
      executePrompt(command);
    }
  }

  Future<void> runQuickAction(String actionKey, String userLabel) async {
    runtimeState.value = HologramRuntimeState.thinking;
    mobileMessages.add({'role': 'user', 'text': userLabel});
    showMobileHistory.value = true;
    final int assistantIndex = mobileMessages.length;
    mobileMessages.add({
      'role': 'assistant',
      'text': 'Đang kết nối COSA Capability Pipeline...',
      'status': 'streaming',
    });

    try {
      final res = await _hubService.executeQuickAction(actionKey);
      if (res != null) {
        final content = res['content_markdown'] as String? ?? 'Hoàn thành xử lý.';
        latestTelemetry.value = res;
        mobileMessages[assistantIndex] = {
          'role': 'assistant',
          'text': content,
          'status': 'delivered',
          'run_id': res['run_id']?.toString() ?? '',
          'capability': res['capability']?.toString() ?? '',
          'prompt_version': res['prompt_version']?.toString() ?? '',
          'tools_used': (res['tools_used'] as List?)?.join(', ') ?? '',
          'latency_ms': res['latency_ms']?.toString() ?? '',
        };
        runtimeState.value = HologramRuntimeState.success;
      } else {
        mobileMessages[assistantIndex] = {
          'role': 'assistant',
          'text': 'Không thể thực thi capability $actionKey.',
          'status': 'error',
        };
        runtimeState.value = HologramRuntimeState.error;
      }
    } catch (e) {
      mobileMessages[assistantIndex] = {
        'role': 'assistant',
        'text': 'Lỗi khi gọi capability: $e',
        'status': 'error',
      };
      runtimeState.value = HologramRuntimeState.error;
    } finally {
      _scheduleResetRuntimeState();
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
            final proposals = (event['proposals'] as List?) ??
                (event['citations'] is Map ? (event['citations']['proposals'] as List?) : null);

            if (assistantIndex < mobileMessages.length) {
              mobileMessages[assistantIndex] = {
                'role': 'assistant',
                'text': fullAssistantText,
                'status': status,
                if (proposals != null && proposals.isNotEmpty) 'proposals': proposals,
              };
            }
            if (status == 'delivered' || status == 'error' || status == 'cancelled') {
              runtimeState.value = status == 'error'
                  ? HologramRuntimeState.error
                  : HologramRuntimeState.success;
              _scheduleResetRuntimeState();
              _hubChatStreamSub?.cancel();
              if (status == 'delivered') {
                loadNeedsYou();
              }
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
              final proposals = lastAssistant['proposals'] ??
                  (lastAssistant['citations'] is Map
                      ? lastAssistant['citations']['proposals']
                      : null);
              if (assistantIndex < mobileMessages.length) {

                mobileMessages[assistantIndex] = {
                  'role': 'assistant',
                  'text': content.isNotEmpty ? content : fullAssistantText,
                  'status': 'delivered',
                  if (proposals != null && (proposals is List) && proposals.isNotEmpty)
                    'proposals': proposals,
                };
              }
              runtimeState.value = HologramRuntimeState.success;
              loadNeedsYou();
            } else {
              if (assistantIndex < mobileMessages.length) {
                mobileMessages[assistantIndex] = {
                  'role': 'assistant',
                  'text': fullAssistantText.isNotEmpty ? fullAssistantText : 'Đã nhận yêu cầu nhưng máy chủ chưa phản hồi.',
                  'status': fullAssistantText.isNotEmpty ? 'delivered' : 'error',
                };
              }
              runtimeState.value = fullAssistantText.isNotEmpty
                  ? HologramRuntimeState.success
                  : HologramRuntimeState.error;
            }
          } catch (_) {
            if (assistantIndex < mobileMessages.length) {
              mobileMessages[assistantIndex] = {
                'role': 'assistant',
                'text': fullAssistantText.isNotEmpty ? fullAssistantText : 'Không thể kết nối đến máy chủ.',
                'status': fullAssistantText.isNotEmpty ? 'delivered' : 'error',
              };
            }
            runtimeState.value = fullAssistantText.isNotEmpty
                ? HologramRuntimeState.success
                : HologramRuntimeState.error;
          }
          _scheduleResetRuntimeState();
        },
        onDone: () {
          if (assistantIndex < mobileMessages.length &&
              mobileMessages[assistantIndex]['status'] == 'streaming') {
            mobileMessages[assistantIndex] = {
              'role': 'assistant',
              'text': fullAssistantText,
              'status': 'delivered',
            };
            runtimeState.value = HologramRuntimeState.success;
            _scheduleResetRuntimeState();
            loadNeedsYou();
          }
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
        executePrompt(transcript);
      } else {
        runtimeState.value = HologramRuntimeState.idle;
      }
    } else {
      final started = await _voiceService.startRecording();
      if (!started) {
        runtimeState.value = HologramRuntimeState.idle;
        isVoiceListening.value = false;
        return;
      }
      isVoiceListening.value = true;
      runtimeState.value = HologramRuntimeState.listening;
    }
  }

  /// LiveKit Conversation Mode (mCOSA V12.1 §15.2) - kept alongside the older
  /// push-to-talk `onTalkPressed()`/`VoiceService` flow above as a fallback,
  /// not a replacement.
  RxBool get isConversationModeActive => _voiceSession?.isActive ?? false.obs;

  Future<void> onConversationModePressed() async {
    final voiceSession = _voiceSession;
    if (voiceSession == null) return;
    if (_isTransitioningVoiceSession) return;
    _isTransitioningVoiceSession = true;

    try {
      if (voiceSession.isActive.value) {
        await voiceSession.stopVoiceSession();
        runtimeState.value = HologramRuntimeState.idle;
        return;
      }

      if (_wakeWordService.isListening) {
        await _wakeWordService.stopListening();
      }

      final deviceType = GetPlatform.isDesktop ? 'desktop' : 'mobile';
      final started = await voiceSession.startVoiceSession(
        deviceType: deviceType,
        onNavigate: handleVoiceNavigation,
      );
      if (!started) {
        if (autoStartWakeWord && !_wakeWordService.isListening) {
          _wakeWordService.startListening();
        }
      }
    } finally {
      _isTransitioningVoiceSession = false;
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
    // Hologram HUD uses Stark Dark Cyberpunk theme
  }
}

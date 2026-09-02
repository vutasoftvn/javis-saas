import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/network/realtime_service.dart';
import '../../../core/session/session_controller.dart';
import '../../../core/services/voice_service.dart';
import '../../../core/services/wake_word_service.dart';
import '../../../modules/auth/services/auth_service.dart';
import '../../../modules/dashboard/services/hub_service.dart';
import '../../../modules/strategy/services/strategy_service.dart';
import '../../../modules/hologram_hub/services/chat_service.dart';
import '../../../modules/workspace_runtime/services/workspace_runtime_service.dart';
import '../../../modules/workforce/services/workforce_mvp_service.dart';
import '../../../modules/agents/services/agent_platform_service.dart';
import '../../../modules/strategy/services/stage_service.dart';
import '../../../modules/vault/services/evidence_service.dart';
import '../../../modules/strategy/services/strategy_lens_service.dart';
import '../../../modules/strategy/services/stage_gate_service.dart';
import '../../../modules/strategy/services/twelve_wy_service.dart';
import '../domain/hologram_runtime_state.dart';
import 'mixins/hub_auth_mixin.dart';
import 'mixins/hub_command_mixin.dart';
import 'mixins/hub_chat_mixin.dart';
import 'mixins/hub_voice_mixin.dart';
import 'mixins/hub_stage_mixin.dart';
import 'mixins/hub_evidence_mixin.dart';
import 'mixins/hub_lenses_mixin.dart';
import 'mixins/hub_gate_mixin.dart';
import 'mixins/hub_twelve_wy_mixin.dart';
import 'mixins/hub_control_plane_mixin.dart';

export '../domain/hologram_runtime_state.dart';

class HologramHubController extends GetxController
    with
        HubAuthMixin,
        HubCommandMixin,
        HubChatMixin,
        HubVoiceMixin,
        HubStageMixin,
        HubEvidenceMixin,
        HubLensesMixin,
        HubGateMixin,
        HubTwelveWyMixin,
        HubControlPlaneMixin {
  // ── Services (injected) ──────────────────────────────────────────────────
  final AuthService _authService;
  final HubService _hubService;
  final StrategyService _strategyService;
  final StageService _stageService;
  final EvidenceService _evidenceService;
  final StrategyLensService _lensService;
  final StageGateService _stageGateService;
  final TwelveWyService _twelveWyService;
  final WorkspaceRuntimeService _runtimeService;
  final RealtimeService _realtimeService;
  final VoiceService _voiceService;
  final ChatService _chatService;
  final WorkforceMvpService _workforceMvpService;
  final AgentPlatformService _agentPlatformService;
  final IWakeWordService _wakeWordService;

  @override
  final bool autoStartWakeWord;

  HologramHubController({
    AuthService? authService,
    HubService? hubService,
    StrategyService? strategyService,
    StageService? stageService,
    EvidenceService? evidenceService,
    StrategyLensService? lensService,
    StageGateService? stageGateService,
    TwelveWyService? twelveWyService,
    WorkspaceRuntimeService? runtimeService,
    RealtimeService? realtimeService,
    VoiceService? voiceService,
    ChatService? chatService,
    WorkforceMvpService? workforceMvpService,
    AgentPlatformService? agentPlatformService,
    IWakeWordService? wakeWordService,
    this.autoStartWakeWord = false,
  })  : _authService = authService ?? AuthService(),
        _hubService = hubService ?? HubService(),
        _strategyService = strategyService ?? StrategyService(),
        _stageService = stageService ?? StageService(),
        _evidenceService = evidenceService ?? EvidenceService(),
        _lensService = lensService ?? StrategyLensService(),
        _stageGateService = stageGateService ?? StageGateService(),
        _twelveWyService = twelveWyService ?? TwelveWyService(),
        _runtimeService = runtimeService ?? WorkspaceRuntimeService(),
        _realtimeService = realtimeService ?? RealtimeService(),
        _voiceService = voiceService ?? VoiceService(),
        _chatService = chatService ?? ChatService(),
        _workforceMvpService = workforceMvpService ?? WorkforceMvpService(),
        _agentPlatformService = agentPlatformService ?? AgentPlatformService(),
        _wakeWordService = wakeWordService ?? WakeWordService();

  // ── Mixin abstract getters — all resolved here ───────────────────────────
  @override AuthService get authService => _authService;
  @override HubService get hubService => _hubService;
  @override StrategyService get strategyService => _strategyService;
  @override StageService get stageService => _stageService;
  @override EvidenceService get evidenceService => _evidenceService;
  @override StrategyLensService get lensService => _lensService;
  @override StageGateService get stageGateService => _stageGateService;
  @override TwelveWyService get twelveWyService => _twelveWyService;
  @override WorkspaceRuntimeService get runtimeService => _runtimeService;
  @override VoiceService get voiceService => _voiceService;
  @override ChatService get chatService => _chatService;
  @override WorkforceMvpService get workforceMvpService => _workforceMvpService;
  @override AgentPlatformService get agentPlatformService => _agentPlatformService;
  @override IWakeWordService get wakeWordService => _wakeWordService;

  /// Convenience getter used by evidence & lenses mixins
  @override
  int? get selectedProjectIdValue => selectedProjectId.value;

  // Bridge: HubVoiceMixin.onConversationModePressed → startOrStopConversationMode
  @override
  Future<void> onConversationModePressed() => startOrStopConversationMode();

  // ── Timers ───────────────────────────────────────────────────────────────
  Timer? _clockTimer;
  Timer? _refreshTimer;
  // Task 8 — debounce cho reload do sự kiện realtime kích hoạt: nhiều sự
  // kiện dồn dập (vd. một loạt agent event trong vài trăm ms) chỉ nên gây
  // đúng một lần fetch lại authoritative, không phải một lần mỗi sự kiện.
  Timer? _realtimeDebounce;

  // Task 10 — bộ đếm CHỈ dùng cho test (không đọc ở đâu trong production
  // code): chứng minh timer THẬT SỰ bị huỷ sau `onClose()` bằng cách đếm số
  // lần callback thực thi, thay vì suy diễn qua giá trị Rx (Rx chỉ notify
  // khi giá trị đổi — `currentTime` không đổi trong cùng một phút nên không
  // dùng được làm proxy tin cậy cho "timer có đang chạy hay không").
  @visibleForTesting
  int clockTickCountForTest = 0;
  @visibleForTesting
  int refreshTickCountForTest = 0;

  // ── Lifecycle ────────────────────────────────────────────────────────────

  @override
  void onInit() {
    super.onInit();

    // Task 8 — chỉ khởi động loading/timers/SSE khi THẬT SỰ có một
    // `SessionSnapshot` active (đã qua `SessionController.activateWorkspace`
    // xác minh). Trước đây controller tự chạy toàn bộ init ngay cả khi chưa
    // có phiên nào được xác thực — lãng phí và có thể mở SSE cho một
    // workspace rỗng/sai rồi phải dọn dẹp lại sau khi login xong.
    final sessionController =
        Get.isRegistered<SessionController>() ? Get.find<SessionController>() : null;
    final activeSession = sessionController?.active.value;
    if (activeSession == null) {
      if (autoStartWakeWord) initWakeWord();
      return;
    }

    ensureAuthenticated().then((_) {
      loadStageContext();
      loadProjectsList();
      loadHubSummary();
      loadCommandCenterData();
      loadCeoNextActions();
      loadActiveCycleTimeline();
      loadPendingApprovals();
      loadAgentRuns();
      loadControlPlaneSummary();
      loadWorkforceAgents();
      loadControlPlaneApprovals();
      loadWorkProducts();
      // Phase 6: Load exception escalations on startup
      loadOpenEscalations();
    });

    updateClock();
    _clockTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      updateClock();
      clockTickCountForTest++;
    });
    _refreshTimer = Timer.periodic(const Duration(seconds: 60), (_) {
      refreshTickCountForTest++;
      loadStageContext(projectId: selectedProjectId.value);
      loadHubSummary(showLoading: false);
      loadCommandCenterData();
      loadCeoNextActions();
      loadActiveCycleTimeline();
      loadPendingApprovals();
      loadAgentRuns();
      loadControlPlaneSummary(showLoading: false);
      loadControlPlaneApprovals();
      // Phase 6: Refresh exception escalations every 60 seconds
      loadOpenEscalations();
    });

    _realtimeService.connectForWorkspace(activeSession.workspaceId);
    _realtimeService.addListener(_onRealtimeEvent);

    if (autoStartWakeWord) initWakeWord();
  }

  @override
  void onClose() {
    _wakeWordService.dispose();
    _clockTimer?.cancel();
    _refreshTimer?.cancel();
    _realtimeDebounce?.cancel();
    cancelResetTimer();
    cancelChatStream();
    _realtimeService.removeListener(_onRealtimeEvent);
    super.onClose();
  }

  // ── Realtime event handler ───────────────────────────────────────────────

  void _onRealtimeEvent(String eventType, Map<String, dynamic> data) {
    debugPrint('[HologramHub] Received realtime event: $eventType');
    if (eventType == 'system.connected') return;

    if (eventType.startsWith('agent.')) {
      // Đây là cue hoạt ảnh tức thời (đang nghĩ/đang chạy tool/...), KHÔNG
      // phải state nghiệp vụ authoritative — an toàn để set trực tiếp từ
      // payload sự kiện vì nó chỉ điều khiển UI runtime indicator, không
      // phải dữ liệu nghiệp vụ cần load lại từ service.
      final state =
          data['state'] as String? ?? eventType.replaceFirst('agent.', '');
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
          scheduleResetRuntimeState();
          break;
        case 'error':
          runtimeState.value = HologramRuntimeState.error;
          scheduleResetRuntimeState();
          break;
        case 'idle':
          runtimeState.value = HologramRuntimeState.idle;
          break;
      }
    }

    _scheduleAuthoritativeReload(eventType);
  }

  /// Task 8 — nguyên tắc cốt lõi: payload của một sự kiện realtime KHÔNG BAO
  /// GIỜ được coi là toàn bộ state để render trực tiếp. Sự kiện chỉ là tín
  /// hiệu "có gì đó đổi" để trigger một lần fetch lại từ service (nguồn sự
  /// thật) — debounce 400ms để một loạt sự kiện dồn dập không gây spam gọi
  /// lại nhiều lần.
  void _scheduleAuthoritativeReload(String eventType) {
    _realtimeDebounce?.cancel();
    _realtimeDebounce = Timer(const Duration(milliseconds: 400), () {
      loadHubSummary(showLoading: false);
      loadCommandCenterData(showLoading: false);
      loadCeoNextActions();
      loadNeedsYou();
      if (eventType.startsWith('agent.')) {
        loadPendingApprovals();
        loadAgentRuns();
      }
      // Phase 6: Reload escalations on exception events
      if (eventType.startsWith('exception.') || eventType == 'budget.overflow') {
        loadOpenEscalations();
      }
    });
  }
}

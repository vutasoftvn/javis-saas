import 'dart:async';

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/widgets/app_toast.dart';
import '../../../data/models/company_pulse_model.dart';
import '../../../data/models/founder_decision_model.dart';
import '../../../data/models/workforce_pack_model.dart';
import '../../../modules/hologram_hub/services/cofounder_api_service.dart';
import '../../../modules/hologram_hub/services/active_project_store.dart';
import '../../../modules/projects/models/project_operating_loop.dart';
import '../../../modules/projects/services/project_operating_loop_service.dart';
import '../../../modules/chat/services/agent_chat_service.dart';
import '../../../modules/chat/models/data_access_declaration.dart';

import '../../../core/network/api_result.dart';
import '../../../core/routing/app_routes.dart';
import '../../../core/services/secure_storage_service.dart';
import '../../../core/network/realtime_service.dart';
import '../../../core/session/session_controller.dart';
import '../../../data/models/execution_plan_model.dart';
import '../../../modules/strategy/services/execution_plan_service.dart';
import '../../../modules/strategy/services/strategy_service.dart';
import '../../../modules/workforce/models/workforce_mvp_models.dart';
import '../../../modules/workforce/services/workforce_mvp_service.dart';
import '../models/project_startup_team.dart';
import '../services/project_startup_team_service.dart';
import '../../projects/widgets/p0_core_setup_banner.dart';

/// Fix-review (2026-09-01, Task 3) — trạng thái tải Workforce Packs cần phân
/// biệt rõ "chưa tải xong"/"đã tải, hợp lệ (có thể rỗng)"/"tải thất bại,
/// không có canonical route hoặc lỗi mạng" — không để lỗi/404 và "workspace
/// thật sự chưa gán agent nào" trông giống hệt nhau trên UI.
enum WorkforceLoadState { idle, loading, loaded, unavailable }

class FounderCommandCenterController extends GetxController {
  // Fix-review (2026-09-02, final review I-1) — `/agent/approvals` (router cũ
  // trong `apps/cosa/api/approval_routes.py`) chỉ còn là stub deprecated,
  // KHÔNG được mount trong `app.py` ⇒ luôn 404. `ApprovalsService` trước đây
  // nuốt lỗi đó thành `[]`, khiến "route không tồn tại" và "không có approval
  // nào" trông giống hệt nhau trên UI. Route canonical đã mount thật là
  // `/agent/workforce/approvals` (workforce_routes.py), có sẵn client typed
  // `WorkforceMvpService` (dùng chung với `MissionControlController`) trả về
  // `ApiResult` — tái dùng thẳng thay vì vá lại `ApprovalsService`.
  final WorkforceMvpService _workforceMvpService;
  final ProjectStartupTeamService _startupTeamService;
  final AgentChatService _chatService = AgentChatService();

  // Fix-review (2026-09-02, final review I-1) — cho phép inject
  // `WorkforceMvpService` trong test (mirror DI pattern của
  // `MissionControlController`) thay vì luôn tạo instance thật gọi mạng.
  FounderCommandCenterController({
    WorkforceMvpService? workforceMvpService,
    ProjectStartupTeamService? startupTeamService,
  })  : _workforceMvpService = workforceMvpService ?? WorkforceMvpService(),
        _startupTeamService = startupTeamService ?? ProjectStartupTeamService();

  // Task 5 (`/agent/conversations/{id}/messages`) đòi hỏi phân loại
  // `data_access` không rỗng cho mọi tin nhắn — chat sheet này là kênh trao
  // đổi business (không nhập PII), nên khai báo cố định BUSINESS_CONFIDENTIAL,
  // không cần subject_reference.
  static const _chatDataAccess = DataAccessDeclaration(
    categories: {DataAccessCategory.businessConfidential},
  );

  String? _cofounderConversationId;
  StreamSubscription<Map<String, dynamic>>? _chatSseSubscription;

  /// Chỉ dùng trong test để seed/kiểm tra `_cofounderConversationId` — chứng
  /// minh `resetForWorkspace()` (final review C-1) thực sự xoá conversation
  /// id của workspace CŨ, không rò rỉ tin nhắn của phiên/workspace mới vào
  /// conversation cũ.
  @visibleForTesting
  void seedConversationIdForTest(String id) => _cofounderConversationId = id;

  @visibleForTesting
  String? get cofounderConversationIdForTest => _cofounderConversationId;

  // Fix (2026-09-02, epoch-guard) — xem chú thích tại
  // `SessionController.workspaceGeneration`: `sendChatMessage` capture giá
  // trị này trước khi await `createConversation`/`sendMessage`; nếu generation
  // đổi trong lúc chờ (workspace switch/logout xảy ra giữa chừng), discard
  // toàn bộ kết quả — không gán conversation-id của workspace CŨ hay ghi tin
  // nhắn vào state của workspace MỚI.
  int get _workspaceGeneration => Get.isRegistered<SessionController>()
      ? Get.find<SessionController>().workspaceGeneration
      : 0;

  // Task 10 — quyết định đã duyệt: `/chat` redirect sang `/hub?panel=chat`
  // (xem `app_pages.dart`); Hub phải tự mở chat sheet hiện có khi nhận
  // query param này, đúng MỘT lần cho mỗi lần vào route bằng cờ này — nếu
  // không, `HologramHubView.build()` (chạy lại mỗi khi Obx bên trong nó
  // rebuild) sẽ mở lại bottom sheet liên tục.
  bool _chatPanelAutoOpenHandled = false;

  /// Mở chat sheet nếu route hiện tại mang `?panel=chat` VÀ chưa xử lý lần
  /// nào trong vòng đời controller này. `openSheet` do view truyền vào vì
  /// việc build/mở `showModalBottomSheet` cần `BuildContext` — controller
  /// (tầng logic) không tự giữ context.
  void maybeAutoOpenChatFromRoute(void Function() openSheet) {
    if (_chatPanelAutoOpenHandled) return;
    if (Get.parameters['panel'] != 'chat') return;
    _chatPanelAutoOpenHandled = true;
    openSheet();
  }

  // Reactive state
  final RxBool isLoading = false.obs;
  final RxBool hasProjects = true.obs;
  final RxList<dynamic> projectsList = <dynamic>[].obs;
  /// Lỗi tải danh sách dự án (401/403/409/5xx, mất mạng...) — trước đây bị
  /// nuốt thành `[]`, khiến `hasProjects` hiểu nhầm "chưa có dự án nào" và
  /// đẩy Founder vào lại flow onboarding dù họ đã có dự án. Field này expose
  /// lỗi thật để UI hiển thị banner/thử lại thay vì trạng thái rỗng giả.
  final RxnString projectsError = RxnString();

  /// Fix race (2026-09-03, Task 5) — `ProjectSetupGuardMiddleware` đồng bộ
  /// không phân biệt được "workspace thật sự 0 project" với "FCC đã đăng ký
  /// nhưng `loadDashboardData()` còn đang chạy" — cả hai đều là `projectsList`
  /// rỗng + `projectsError` null. Cờ này bật `true` sau khi `loadDashboardData()`
  /// xử lý xong danh sách project (kể cả khi fetch lỗi) để middleware chỉ
  /// quyết định khi state đã biết; khoảng trước lúc tải xong do backstop async
  /// `_enforceZeroProjectRedirect()` lo.
  final RxBool projectsLoadedOnce = false.obs;
  final Rx<CompanyPulseModel?> pulse = Rx<CompanyPulseModel?>(null);
  final RxList<NextBestActionModel> top3Actions = <NextBestActionModel>[].obs;

  /// WGA — id dự án đang active (để gọi weekly-goal / execution-plans).
  /// Task 6 — không tự auto-select projects.first, phụ thuộc vào local
  /// restoration hoặc user picker. Generation counter để detect Project switch
  /// race.
  final RxnString activeProjectId = RxnString();
  String? get selectedProjectId => activeProjectId.value;
  final RxString activeProjectTitle = ''.obs;
  final RxBool requiresProjectSelection = false.obs;

  /// Operating Loop của Project đã chọn (Cycle, Tuần hiện tại, Cam kết/Tasks)
  final Rxn<ProjectOperatingLoop> currentOperatingLoop = Rxn<ProjectOperatingLoop>();
  final RxBool isOperatingLoopLoading = false.obs;
  final RxnString operatingLoopError = RxnString();
  int _operatingLoopToken = 0;

  Future<void> loadOperatingLoop(String projectId) async {
    final token = ++_operatingLoopToken;
    isOperatingLoopLoading.value = true;
    operatingLoopError.value = null;

    try {
      final service = ProjectOperatingLoopService();
      final result = await service.get(projectId);
      if (token != _operatingLoopToken) return;

      if (result.isSuccess && result.dataOrNull != null) {
        currentOperatingLoop.value = result.dataOrNull;
        operatingLoopError.value = null;
      } else {
        currentOperatingLoop.value = null;
        operatingLoopError.value = result.failureOrNull?.message ?? 'Không thể tải chu kỳ hoạt động của dự án';
      }
    } catch (e) {
      if (token != _operatingLoopToken) return;
      currentOperatingLoop.value = null;
      operatingLoopError.value = 'Lỗi kết nối chu kỳ hoạt động: $e';
    } finally {
      if (token == _operatingLoopToken) {
        isOperatingLoopLoading.value = false;
      }
    }
  }

  /// Đội ngũ khởi nghiệp của Project active (Task 5)
  final RxList<ProjectStartupTeamMember> startupTeam = <ProjectStartupTeamMember>[].obs;
  final RxBool isTeamLoading = false.obs;
  final RxnString teamError = RxnString();
  int _startupTeamToken = 0;

  Future<void> loadStartupTeam(String? projectId) async {
    if (projectId == null || projectId.isEmpty) {
      startupTeam.clear();
      isTeamLoading.value = false;
      teamError.value = null;
      return;
    }

    final token = ++_startupTeamToken;
    isTeamLoading.value = true;
    teamError.value = null;

    try {
      final result = await _startupTeamService.listTeam(projectId);
      if (token != _startupTeamToken) return;

      if (result.isSuccess && result.dataOrNull != null) {
        startupTeam.assignAll(result.dataOrNull!);
        teamError.value = null;
      } else {
        startupTeam.clear();
        teamError.value =
            result.failureOrNull?.message ?? 'Không thể tải đội ngũ dự án';
      }
    } catch (e) {
      if (token != _startupTeamToken) return;
      startupTeam.clear();
      teamError.value = 'Lỗi kết nối đội ngũ dự án: $e';
    } finally {
      if (token == _startupTeamToken) {
        isTeamLoading.value = false;
      }
    }
  }

  Future<bool> activateTeamMember(String profileKey, int expectedVersion) async {
    final pid = activeProjectId.value;
    if (pid == null || pid.isEmpty) {
      AppToast.warning('Chưa chọn dự án active');
      return false;
    }
    final result = await _startupTeamService.activateMember(
      projectId: pid,
      profileKey: profileKey,
      expectedVersion: expectedVersion,
    );
    if (result.isSuccess && result.dataOrNull != null) {
      final updated = result.dataOrNull!;
      final idx = startupTeam.indexWhere((m) => m.profileKey == profileKey);
      if (idx != -1) {
        startupTeam[idx] = updated;
      } else {
        startupTeam.add(updated);
      }
      AppToast.success('Đã kích hoạt ${updated.label}');
      return true;
    } else {
      final failure = result.failureOrNull;
      final msg = failure?.message ?? 'Kích hoạt thất bại';
      AppToast.error(msg);
      await loadStartupTeam(pid);
      return false;
    }
  }

  Future<bool> pauseTeamMember(
    String profileKey,
    int expectedVersion, {
    String? reason,
  }) async {
    final pid = activeProjectId.value;
    if (pid == null || pid.isEmpty) {
      AppToast.warning('Chưa chọn dự án active');
      return false;
    }
    final result = await _startupTeamService.pauseMember(
      projectId: pid,
      profileKey: profileKey,
      expectedVersion: expectedVersion,
      reason: reason,
    );
    if (result.isSuccess && result.dataOrNull != null) {
      final updated = result.dataOrNull!;
      final idx = startupTeam.indexWhere((m) => m.profileKey == profileKey);
      if (idx != -1) {
        startupTeam[idx] = updated;
      } else {
        startupTeam.add(updated);
      }
      AppToast.info('Đã tạm dừng ${updated.label}');
      return true;
    } else {
      final failure = result.failureOrNull;
      final msg = failure?.message ?? 'Tạm dừng thất bại';
      AppToast.error(msg);
      await loadStartupTeam(pid);
      return false;
    }
  }

  /// Task 6 — generation counter độc lập với workspace generation, dùng để
  /// discard stale Project A response khi user đã switch sang Project B.
  int _projectGeneration = 0;
  int get projectGeneration => _projectGeneration;

  /// WGA — kế hoạch triển khai (draft) agent đề xuất từ mục tiêu tuần.
  final RxList<ExecutionPlan> draftPlans = <ExecutionPlan>[].obs;
  final RxBool isDecomposing = false.obs;
  final ExecutionPlanService _executionPlanService = ExecutionPlanService();

  /// WGA #6a — "Việc của bạn": task FOUNDER_ONLY + task AI bị chặn.
  final RxList<FounderInboxTask> founderInboxTasks = <FounderInboxTask>[].obs;

  /// WGA #2 — cho phép vòng thực thi tự động (sweep) chạy hay không.
  final RxBool sweepEnabled = true.obs;
  final RxList<FounderDecisionModel> pendingDecisions =
      <FounderDecisionModel>[].obs;
  final RxList<Map<String, dynamic>> pendingApprovals =
      <Map<String, dynamic>>[].obs;
  final RxList<WorkforcePackModel> workforcePacks = <WorkforcePackModel>[].obs;
  // Fix-review (2026-09-01, Task 3) — cho phép UI phân biệt "đang tải" /
  // "đã tải" / "không tải được" cho Workforce Packs, thay vì suy diễn từ
  // việc `workforcePacks` rỗng (rỗng có thể là hợp lệ: workspace chưa gán
  // agent nào).
  final Rx<WorkforceLoadState> workforceState = WorkforceLoadState.idle.obs;
  // Fix-review (2026-09-02, final review I-1) — tái dùng cùng idiom
  // `WorkforceLoadState` cho Approvals: `pendingApprovals` rỗng có thể là hợp
  // lệ (thật sự không có gì chờ duyệt) hoặc là hệ quả của 404/5xx bị nuốt —
  // hai trường hợp này phải phân biệt được trên UI.
  final Rx<WorkforceLoadState> approvalsState = WorkforceLoadState.idle.obs;
  final RxInt selectedTabIndex = 0.obs; // 0: Command Center, 1: AI Workforce

  // Co-Founder Chat Sheet State
  final RxList<Map<String, String>> chatMessages = <Map<String, String>>[].obs;
  final TextEditingController chatInputController = TextEditingController();
  final RxBool isChatLoading = false.obs;

  /// Founder cần vào luồng thiết lập project khi: chưa có project nào, HOẶC
  /// đúng một project và setup của nó chưa `ACTIVE` (tạo project rồi bỏ dở
  /// kickoff — cần resume). Lỗi tải danh sách project KHÔNG kích hoạt điều
  /// này: giữ nguyên hành vi "lỗi tạm thời không đẩy Founder ra onboarding".
  /// Nhiều hơn một project ⇒ không can thiệp (workspace đã vận hành).
  bool get needsProjectSetup {
    if (projectsError.value != null) return false;
    return projectsList.isEmpty;
  }

  @override
  void onInit() {
    super.onInit();
    loadDashboardData();
  }

  @override
  void onClose() {
    _chatSseSubscription?.cancel();
    chatInputController.dispose();
    super.onClose();
  }

  /// WGA #6b — poll nhẹ draftPlans + inbox; gọi bởi widget wrapper của tab
  /// Command Center (`_WgaPollWrapper`), timer gắn với vòng đời widget đó.
  Future<void> refreshWgaSurfaces() async {
    if (!hasProjects.value || (activeProjectId.value?.isEmpty ?? true)) return;
    await loadDraftPlans();
    await loadFounderInbox();
  }

  Future<void> loadExecutionSettings() async {
    try {
      sweepEnabled.value = await _executionPlanService.getSweepEnabled();
    } catch (e) {
      debugPrint('[FounderCommandCenter] loadExecutionSettings error: $e');
    }
  }

  Future<void> setSweepEnabled(bool enabled) async {
    final prev = sweepEnabled.value;
    sweepEnabled.value = enabled; // optimistic
    try {
      sweepEnabled.value = await _executionPlanService.setSweepEnabled(enabled);
      AppToast.info(
        enabled
            ? 'AI sẽ tự chạy các việc trong quyền hạn.'
            : 'Đã tạm dừng — AI không tự chạy việc nào (việc vẫn được lập kế hoạch).',
      );
    } catch (e) {
      sweepEnabled.value = prev;
      AppToast.error('Không đổi được cài đặt: $e');
    }
  }

  /// Fix-review (2026-09-02, final review C-1) — controller này đăng ký
  /// `permanent: true` tại `AppShellController` nên sống xuyên suốt logout/
  /// chuyển workspace. Không có bước dọn dẹp, `pulse`/`top3Actions`/
  /// `pendingDecisions`/`pendingApprovals`/`workforcePacks` của tenant CŨ tiếp
  /// tục hiển thị trên màn hình Hub chính cho tenant MỚI — vô thời hạn, vì
  /// controller này (khác `HologramHubController`) KHÔNG có timer refresh nào
  /// — và `_cofounderConversationId` (gán một lần qua `??=`) có thể khiến tin
  /// nhắn gõ sau khi chuyển workspace bị nối vào conversation của workspace
  /// TRƯỚC ĐÓ. Gọi bởi `SessionController` ngay sau khi commit snapshot mới
  /// (activateWorkspace) và trong logout().
  ///
  /// [reload] = false khi gọi từ `logout()` — không có workspace mới để tải,
  /// chỉ cần xoá sạch state hiển thị.
  void resetForWorkspace({bool reload = true}) {
    isLoading.value = false;
    hasProjects.value = true;
    projectsList.clear();
    projectsError.value = null;
    // Fix race (2026-09-03, Task 5) — workspace vừa đổi, danh sách project của
    // tenant CŨ đã bị clear và `loadDashboardData()` sắp chạy lại; hạ cờ để
    // `ProjectSetupGuardMiddleware` đồng bộ KHÔNG nhầm cửa sổ reload này là
    // "workspace mới có 0 project" mà bounce sớm sang `/projects/new`.
    projectsLoadedOnce.value = false;
    pulse.value = null;
    top3Actions.clear();
    draftPlans.clear();
    founderInboxTasks.clear();
    activeProjectId.value = null;
    requiresProjectSelection.value = false;
    pendingDecisions.clear();
    pendingApprovals.clear();
    workforcePacks.clear();
    workforceState.value = WorkforceLoadState.idle;
    approvalsState.value = WorkforceLoadState.idle;
    startupTeam.clear();
    isTeamLoading.value = false;
    teamError.value = null;
    currentOperatingLoop.value = null;
    operatingLoopError.value = null;

    // Chat sheet: không được để tin nhắn/gõ dở của workspace cũ lẫn vào
    // workspace mới, và conversation id phải reset để lần gửi tiếp theo tạo
    // conversation MỚI thay vì nối vào conversation của tenant trước.
    _chatSseSubscription?.cancel();
    _chatSseSubscription = null;
    _cofounderConversationId = null;
    chatMessages.clear();
    chatInputController.clear();
    isChatLoading.value = false;

    // Task 6 — reset project context + generation counter
    _projectGeneration = 0;
    RealtimeService().clearActiveProject();

    if (reload) {
      loadDashboardData();
    }
  }

  /// Task 6 — User chọn một Project khác. Hủy subscription cũ, increment
  /// generation counter để discard stale response, xoá UI state của Project cũ,
  /// persist selection, notify RealtimeService về project switch, rồi tải data
  /// Project mới.
  Future<void> selectProject(String projectId) async {
    // Hủy SSE subscription của Project cũ
    _chatSseSubscription?.cancel();
    _chatSseSubscription = null;

    // Increment generation để discard stale response từ Project cũ
    _projectGeneration++;

    // Xoá state UI của Project cũ (chat, plans, inbox, pulse, etc.)
    _cofounderConversationId = null;
    chatMessages.clear();
    chatInputController.clear();
    isChatLoading.value = false;
    draftPlans.clear();
    founderInboxTasks.clear();
    pulse.value = null;
    top3Actions.clear();

    // Task 6 — notify RealtimeService về project switch để filtering SSE events
    final realtimeService = RealtimeService();
    realtimeService.setActiveProject(projectId);

    // Persist selection trong local storage (per workspace)
    final wsId = await SecureStorageService.read('workspace_id');
    if (wsId != null) {
      await ActiveProjectStore.write(wsId, projectId);
    }

    // Set active Project và reload data
    activeProjectId.value = projectId;

    // Tìm title từ projectsList
    dynamic projectData;
    try {
      projectData = projectsList.firstWhere(
        (p) => p['id']?.toString() == projectId,
      );
    } catch (e) {
      projectData = null;
    }

    activeProjectTitle.value =
        projectData?['title']?.toString() ?? 'Dự án';

    requiresProjectSelection.value = false;

    // Tải data Project mới
    currentOperatingLoop.value = null;
    operatingLoopError.value = null;
    startupTeam.clear();
    teamError.value = null;
    unawaited(loadDraftPlans());
    unawaited(loadFounderInbox());
    unawaited(loadOperatingLoop(projectId));
    unawaited(loadStartupTeam(projectId));

    try {
      final projectStage = projectData?['lifecycleStage'] ??
          projectData?['project_stage'] ??
          projectData?['lifecycle_stage'];

      final pulseRes = await CoFounderApiService.getCompanyPulse(
        workspaceId: wsId,
        projectId: projectId,
        stage: projectStage?.toString(),
      );
      final top3Res = await CoFounderApiService.getTop3Focus(
        workspaceId: wsId,
        projectId: projectId,
      );

      pulse.value = pulseRes;
      top3Actions.assignAll(top3Res);
    } catch (e) {
      debugPrint('[FounderCommandCenter] selectProject error: $e');
    }
  }

  /// Tải toàn bộ dữ liệu cho Founder Command Center
  Future<void> loadDashboardData() async {
    isLoading.value = true;
    try {
      final wsId = await SecureStorageService.read('workspace_id');
      final strategyService = StrategyService();

      List<dynamic> projects = [];
      try {
        final result = await strategyService.getProjects();
        if (result.errorMessage != null) {
          // Lỗi thật — không âm thầm coi là "chưa có dự án" (điều đó sẽ đẩy
          // Founder vào lại luồng onboarding tạo dự án đầu tiên dù họ đã có
          // sẵn dự án, chỉ là lần tải này thất bại). Giữ nguyên projectsList
          // hiện tại, chỉ báo lỗi để UI hiển thị banner/thử lại.
          projectsError.value = result.errorMessage;
        } else {
          projects = result.items;
          projectsError.value = null;
        }
      } catch (e) {
        debugPrint('[FounderCommandCenter] getProjects error: $e');
        projectsError.value = 'Không thể tải danh sách dự án: $e';
      }

      projectsList.assignAll(projects);
      hasProjects.value = projects.isNotEmpty || projectsError.value != null;
      // Fix race (2026-09-03, Task 5) — đã xử lý xong danh sách project (dù
      // thành công hay lỗi) ⇒ state đủ để `ProjectSetupGuardMiddleware` đồng
      // bộ quyết định.
      projectsLoadedOnce.value = true;

      // Deterministic Project context resolution:
      // 1. Nếu có stored valid -> giữ nguyên
      // 2. Nếu có stored nhưng stale/unauthorized -> clear store, selectedProjectId = null
      // 3. Nếu chưa có stored -> default min(createdAt, id), persist store
      // 4. Nếu projects rỗng hoặc request lỗi -> selectedProjectId = null, không persist
      String? activeProjectId;
      String? activeProjectTitle;
      dynamic activeProjectStage;

      if (projects.isNotEmpty && wsId != null && projectsError.value == null) {
        final resolution = await ActiveProjectStore.resolve(
          workspaceId: wsId,
          projects: projects,
        );

        if (resolution.project != null) {
          final foundProject = resolution.project;
          activeProjectId = foundProject is Map
              ? foundProject['id']?.toString()
              : (foundProject as dynamic).id?.toString();
          activeProjectTitle = (foundProject is Map
                  ? foundProject['title']?.toString()
                  : (foundProject as dynamic).title?.toString()) ??
              'Dự án chính';
          activeProjectStage = foundProject is Map
              ? (foundProject['lifecycleStage'] ??
                  foundProject['project_stage'] ??
                  foundProject['lifecycle_stage'])
              : (foundProject as dynamic).lifecycleStage;
          requiresProjectSelection.value = false;
        } else {
          requiresProjectSelection.value = true;
        }
      } else {
        requiresProjectSelection.value = true;
      }

      this.activeProjectId.value = activeProjectId;
      this.activeProjectTitle.value = activeProjectTitle ?? '';

      currentOperatingLoop.value = null;
      operatingLoopError.value = null;

      if (activeProjectId != null) {
        unawaited(loadDraftPlans());
        unawaited(loadFounderInbox());
        unawaited(loadOperatingLoop(activeProjectId));
        unawaited(loadStartupTeam(activeProjectId));
      } else {
        draftPlans.clear();
        founderInboxTasks.clear();
        startupTeam.clear();
      }

      try {
        // Chỉ tải KPI nếu có Project đang hoạt động
        CompanyPulseModel? pulseRes;
        List<NextBestActionModel> top3Res = [];
        List<FounderDecisionModel> decisionsRes = [];
        if (activeProjectId != null) {
          pulseRes = await CoFounderApiService.getCompanyPulse(
            workspaceId: wsId,
            projectId: activeProjectId,
            stage: activeProjectStage?.toString(),
          );
          top3Res = await CoFounderApiService.getTop3Focus(
            workspaceId: wsId,
            projectId: activeProjectId,
          );
          // Task 6 — listPendingDecisions giờ yêu cầu projectId. Chỉ fetch
          // decisions cho project đang hoạt động.
          decisionsRes = await CoFounderApiService.listPendingDecisions(
            workspaceId: wsId,
            projectId: activeProjectId,
          );
        }
        workforceState.value = WorkforceLoadState.loading;
        final packsResult = await CoFounderApiService.listWorkforcePacks();

        pulse.value = pulseRes;
        top3Actions.assignAll(top3Res);
        pendingDecisions.assignAll(decisionsRes);
        // Fix-review (2026-09-01, Task 3) — chỉ ghi đè workforcePacks khi tải
        // thành công thật sự; thất bại (404/5xx/mất mạng) chuyển sang trạng
        // thái `unavailable` rõ ràng thay vì âm thầm coi như "rỗng".
        packsResult.when(
          success: (data, _) {
            workforcePacks.assignAll(data);
            workforceState.value = WorkforceLoadState.loaded;
          },
          failure: (failure) {
            debugPrint('[FounderCommandCenter] listWorkforcePacks failure: ${failure.message}');
            workforceState.value = WorkforceLoadState.unavailable;
          },
        );

        // Fix-review (2026-09-02, final review I-1) — load Approvals qua route
        // canonical `/agent/workforce/approvals`; 404/5xx/mất mạng phản ánh
        // thành `WorkforceLoadState.unavailable` thay vì âm thầm coi là rỗng.
        approvalsState.value = WorkforceLoadState.loading;
        final approvalsResult = await _workforceMvpService.listApprovals(
          status: 'PENDING',
        );
        approvalsResult.when(
          success: (data, _) {
            pendingApprovals.assignAll(data.map(_approvalToLegacyMap).toList());
            approvalsState.value = WorkforceLoadState.loaded;
          },
          failure: (failure) {
            debugPrint('[FounderCommandCenter] listApprovals failure: ${failure.message}');
            approvalsState.value = WorkforceLoadState.unavailable;
          },
        );
      } catch (e) {
        debugPrint('[FounderCommandCenter] Error loading secondary dashboard metrics: $e');
      }

    } finally {
      isLoading.value = false;
      // FIX 3 (final review) — backstop phải chạy KỂ CẢ khi một trong các
      // await ở trên ném lỗi (block `try` này không có `catch`, chỉ `finally`).
      // `projectsList` + `projectsError` + `projectsLoadedOnce` đều đã settled
      // quanh dòng ~245 nên predicate `needsProjectSetup` hợp lệ trong `finally`.
      _enforceZeroProjectRedirect();
    }
  }

  /// Backstop cho `ProjectSetupGuardMiddleware`: khi Founder đã điều hướng
  /// vào `/hub` (hoặc `/work/*`) trước lúc danh sách project tải xong,
  /// middleware đồng bộ chưa quyết định được. Sau khi `loadDashboardData()`
  /// hoàn tất, tự đẩy sang `/projects/new` nếu vẫn `needsProjectSetup`.
  /// Chỉ tác động đúng hai bề mặt được guard — không đụng `/login`,
  /// `/workspace-picker`, `/projects/new`, v.v.
  void _enforceZeroProjectRedirect() {
    if (!needsProjectSetup) return;
    // FIX 5 (final review, ledger D1) — `Get.currentRoute` có thể mang query
    // string (`/hub?panel=chat`); so khớp trên `path` đã tách query, nếu không
    // backstop bỏ sót mọi route có tham số.
    final route = Uri.parse(Get.currentRoute).path;
    if (route != AppRoutes.hub && !route.startsWith('/work/')) return;
    Get.offAllNamed(AppRoutes.projectsNew);
  }

  /// Khởi tạo dự án đầu tiên theo flow cơ bản và trả về ID dự án để chuyển tiếp sang Kickoff
  Future<String?> createFirstProject({
    required String title,
    required String description,
  }) async {
    isLoading.value = true;
    try {
      final strategyService = StrategyService();
      final project = await strategyService.createBasicProject(
        title: title,
        description: description.isNotEmpty ? description : null,
      );
      final createdId = project['id']?.toString();
      if (isP0CoreBootstrapIncomplete(project)) {
        AppToast.warning(
          'Dự án đã được tạo nhưng bộ cố vấn P0 Core chưa thiết lập xong. '
          'Mở Hội đồng cố vấn và chọn "Khởi tạo P0 Core" để hoàn tất.',
        );
      }
      await loadDashboardData();
      return createdId;
    } catch (e) {
      debugPrint('[FounderCommandCenter] createFirstProject error: $e');
      AppToast.error('Lỗi: $e', title: 'Không thể tạo dự án');
      return null;
    } finally {
      isLoading.value = false;
    }
  }

  /// Chốt quyết định chiến lược của Founder
  /// Task 6 — projectId là bắt buộc và phải match activeProjectId.
  Future<void> resolveDecision({
    required int decisionId,
    required String optionKey,
    String? founderNotes,
  }) async {
    // Task 6 — projectId là bắt buộc. Nếu không có project đang hoạt động,
    // không nên gọi hàm này.
    if (activeProjectId.value == null || activeProjectId.value!.isEmpty) {
      AppToast.error('Vui lòng chọn một dự án trước khi chốt quyết định.');
      return;
    }

    final success = await CoFounderApiService.resolveDecision(
      decisionId: decisionId,
      projectId: activeProjectId.value!,
      decisionMade: optionKey,
      founderNotes: founderNotes,
    );

    if (success) {
      pendingDecisions.removeWhere((d) => d.id == decisionId);
      AppToast.success(
        'Lựa chọn đã được ghi nhận vào Decision Memory để điều phối Workforce.',
        title: 'Đã chốt quyết định',
      );
    }
  }

  /// Phê duyệt một Task kỹ thuật (Approval)
  Future<void> approveTask(dynamic approvalId) async {
    final result = await _workforceMvpService.decideApproval(
      approvalId.toString(),
      approved: true,
    );
    if (result is ApiSuccess<WorkforceApprovalDecision>) {
      pendingApprovals.removeWhere((a) => a['id'] == approvalId);
      AppToast.success(
        'Agent sẽ tiếp tục tiến trình thực thi ngay lập tức.',
        title: 'Đã phê duyệt tác vụ',
      );
    } else {
      AppToast.error(
        'Yêu cầu phê duyệt chưa được ghi nhận ở backend. Vui lòng thử lại.',
        title: 'Không thể phê duyệt',
      );
    }
  }

  /// Từ chối một Task kỹ thuật (Approval)
  Future<void> rejectTask(dynamic approvalId, String reason) async {
    final result = await _workforceMvpService.decideApproval(
      approvalId.toString(),
      approved: false,
      reason: reason,
    );
    if (result is ApiSuccess<WorkforceApprovalDecision>) {
      pendingApprovals.removeWhere((a) => a['id'] == approvalId);
      AppToast.warning(
        'Lý do từ chối đã được ghi nhận.',
        title: 'Đã từ chối tác vụ',
      );
    } else {
      AppToast.error(
        'Yêu cầu từ chối chưa được ghi nhận ở backend. Vui lòng thử lại.',
        title: 'Không thể từ chối',
      );
    }
  }

  /// Chuyển `WorkforceApproval` (model canonical) sang `Map` để tương thích
  /// ngược với các widget hiện có (`WaitingForYouWidget`) — vốn được xây
  /// trước khi có `WorkforceMvpService`, đọc field rời qua key thay vì model.
  Map<String, dynamic> _approvalToLegacyMap(WorkforceApproval a) => {
        'id': a.approvalId,
        'run_id': a.runId,
        'title': a.action,
        'agent_name': a.subject,
        'risk_level': a.riskLevel,
        'status': a.status,
      };

  /// Bật/Tắt một Optional Pack
  Future<void> togglePack(String packKey, bool value) async {
    final success = await CoFounderApiService.toggleOptionalPack(
      packKey: packKey,
      isActive: value,
    );
    if (success) {
      final index = workforcePacks.indexWhere((p) => p.key == packKey);
      if (index != -1) {
        final old = workforcePacks[index];
        workforcePacks[index] = WorkforcePackModel(
          key: old.key,
          name: old.name,
          roleTitle: old.roleTitle,
          department: old.department,
          category: old.category,
          isCore: old.isCore,
          isActive: value,
          description: old.description,
          toolsCount: old.toolsCount,
        );
      }
      AppToast.info(
        value
            ? 'Đã kích hoạt gói mở rộng cho Workspace.'
            : 'Đã vô hiệu hóa gói mở rộng.',
        title: 'Cập nhật Workforce Pack',
      );
    } else {
      // Fix-review (2026-09-01, Task 3) — `/workforce/packs/:key/toggle`
      // không có canonical backend nên `toggleOptionalPack` luôn trả về
      // `false`. Đây KHÔNG phải lỗi tạm thời nên không gợi ý "thử lại" —
      // thông báo rõ tính năng này hiện chưa khả dụng.
      AppToast.warning(
        'Bật/tắt gói mở rộng hiện chưa khả dụng trên phiên bản này.',
        title: 'Chưa khả dụng',
      );
    }
  }

  // ── WGA: Weekly Goal → Agent Execution ──────────────────────────────────

  /// Tải danh sách kế hoạch triển khai (draft) của dự án active.
  Future<void> loadDraftPlans() async {
    final pid = activeProjectId.value;
    if (pid == null || pid.isEmpty) {
      draftPlans.clear();
      return;
    }
    try {
      final plans = await _executionPlanService.listDraftPlans(pid);
      draftPlans.assignAll(plans);
    } catch (e) {
      debugPrint('[FounderCommandCenter] loadDraftPlans error: $e');
    }
  }

  Future<void> loadFounderInbox() async {
    final pid = activeProjectId.value;
    if (pid == null || pid.isEmpty) {
      founderInboxTasks.clear();
      return;
    }
    try {
      founderInboxTasks.assignAll(await _executionPlanService.listFounderInbox());
    } catch (e) {
      debugPrint('[FounderCommandCenter] loadFounderInbox error: $e');
    }
  }

  /// Founder đặt/sửa mục tiêu tuần và nhờ agent lập kế hoạch triển khai.
  Future<void> requestDecomposition(
    String focus, {
    String origin = 'command_center',
    String? originRef,
  }) async {
    final pid = activeProjectId.value;
    if (pid == null || pid.isEmpty) {
      AppToast.warning('Chưa có dự án active để đặt mục tiêu.');
      return;
    }
    if (focus.trim().isEmpty) {
      AppToast.warning('Mục tiêu tuần không được để trống.');
      return;
    }
    isDecomposing.value = true;
    try {
      await _executionPlanService.setWeeklyGoal(
        pid,
        focus.trim(),
        triggerDecomposition: true,
        origin: origin,
        originRef: originRef,
      );
      AppToast.info(
        'Đã ghi mục tiêu tuần. AI đang lập kế hoạch triển khai — kế hoạch sẽ hiện ở đây trong giây lát.',
      );
      unawaited(_burstReloadDraftPlans());
    } catch (e) {
      AppToast.error('Không thể đặt mục tiêu: $e');
    } finally {
      isDecomposing.value = false;
    }
  }

  /// Kế hoạch được tạo bất đồng bộ ở backend (event → worker) — reload nhanh
  /// vài nhịp để founder thấy kế hoạch ngay thay vì chờ nhịp poll 20s. (bỏ qua
  /// trong test để không rò future delayed.)
  Future<void> _burstReloadDraftPlans() async {
    if (Get.testMode) return;
    for (final s in const [3, 8, 15]) {
      await Future<void>.delayed(Duration(seconds: s));
      if (draftPlans.isNotEmpty) return;
      await loadDraftPlans();
    }
  }

  Future<void> acceptPlan(String planId) async {
    final snapshot = List<ExecutionPlan>.from(draftPlans);
    draftPlans.removeWhere((p) => p.id == planId); // optimistic
    try {
      await _executionPlanService.acceptPlan(planId);
      AppToast.success('Đã duyệt kế hoạch. Các việc đã được tạo cho AI và cho bạn.');
      await loadDraftPlans();
    } catch (e) {
      draftPlans.assignAll(snapshot); // rollback
      AppToast.error('Không thể duyệt kế hoạch: $e');
    }
  }

  Future<void> rejectPlan(String planId) async {
    final snapshot = List<ExecutionPlan>.from(draftPlans);
    draftPlans.removeWhere((p) => p.id == planId);
    try {
      await _executionPlanService.rejectPlan(planId);
      AppToast.info('Đã bỏ kế hoạch đề xuất.');
    } catch (e) {
      draftPlans.assignAll(snapshot);
      AppToast.error('Không thể bỏ kế hoạch: $e');
    }
  }

  /// Sửa 1 item của kế hoạch (đổi class / bỏ). Reload để phản ánh guard phía backend.
  Future<void> updatePlanItem(
    String planId,
    String itemId, {
    AutonomyClass? autonomyClass,
    bool? drop,
    String? title,
  }) async {
    try {
      await _executionPlanService.updateItem(
        planId,
        itemId,
        autonomyClass: autonomyClass,
        drop: drop,
        title: title,
      );
      await loadDraftPlans();
    } catch (e) {
      AppToast.error('Không cập nhật được: $e');
      await loadDraftPlans();
    }
  }

  /// Tạo mới phiên chat: huỷ SSE stream đang chạy, reset conversation ID và dọn dẹp tin nhắn.
  void startNewChat() {
    _chatSseSubscription?.cancel();
    _chatSseSubscription = null;
    _cofounderConversationId = null;
    chatMessages.clear();
    chatInputController.clear();
    isChatLoading.value = false;
  }

  /// Gửi tin nhắn trao đổi với COSA Co-Founder
  ///
  /// G2 P0.8 / G3 §10.4: khi request thất bại, trước đây hiện một câu trả
  /// lời "đã tiếp nhận và đang điều phối" giả — founder tin nhầm là tin nhắn
  /// đã được xử lý dù chưa hề tạo Mission nào. Giờ hiện đúng trạng thái lỗi.
  ///
  /// Trước đây gọi `CoFounderApiService.chatWithCoFounder` → `/cofounder/chat`,
  /// một endpoint chưa từng tồn tại ở bất kỳ backend nào (luôn 404). Chat thật
  /// đi qua AgentOS conversation/message/SSE flow (`apps/cosa/api/routes.py`),
  /// đúng pattern `AgentChatService` module `chat` đã dùng — tái dùng lại thay
  /// vì tạo route giả thứ hai.
  Future<void> sendChatMessage(String message) async {
    final trimmed = message.trim();
    if (trimmed.isEmpty) return;

    // Task 2 (2026-09-11 Project-scoped Founder Hub) — Project là bắt buộc,
    // không auto-select/company-wide. Chưa có Project đang hoạt động thì
    // không được tạo conversation/gửi message nào — chỉ hiện lỗi cục bộ,
    // giống hành vi lỗi thật khác của hàm này (không hiện thành công giả).
    final projectId = activeProjectId.value;
    if (projectId == null || projectId.isEmpty) {
      chatMessages.add({'role': 'user', 'content': trimmed});
      chatInputController.clear();
      chatMessages.add({
        'role': 'error',
        'content': 'Chưa chọn Project — vui lòng chọn một Project trước khi trò chuyện.',
      });
      return;
    }

    final workspaceGenerationAtSend = _workspaceGeneration;
    final projectGenerationAtSend = _projectGeneration;
    chatMessages.add({'role': 'user', 'content': trimmed});
    chatInputController.clear();
    isChatLoading.value = true;

    try {
      if (_cofounderConversationId == null) {
        final created = await _chatService.createConversation(
          projectId: projectId,
          title: 'Founder Command Center',
          activeAgentProfile: 'operations',
        );
        // Task 6 — Kiểm tra cả workspace generation và project generation.
        // Nếu user đã switch Project giữa lúc chờ, discard response.
        if (_workspaceGeneration != workspaceGenerationAtSend ||
            _projectGeneration != projectGenerationAtSend) {
          // Workspace hoặc Project đã đổi — không được gán conversation-id
          return;
        }
        _cofounderConversationId = created?.id;
      }
      final conversationId = _cofounderConversationId;
      if (conversationId == null) {
        throw Exception('Không tạo được conversation với COSA runtime.');
      }

      final response = await _chatService.sendMessage(
        conversationId,
        projectId: projectId,
        content: trimmed,
        dataAccess: _chatDataAccess,
      );
      if (_workspaceGeneration != workspaceGenerationAtSend ||
          _projectGeneration != projectGenerationAtSend) {
        // Cùng lý do — không được thêm tin nhắn assistant/subscribe SSE của
        // request thuộc Project CŨ vào state Project MỚI.
        return;
      }
      final runId = response?['run_id']?.toString();
      if (runId == null) {
        throw Exception('COSA runtime không trả về run_id.');
      }

      final assistantMsg = <String, String>{'role': 'cosa', 'content': ''};
      chatMessages.add(assistantMsg);
      _subscribeChatSse(runId, assistantMsg);
    } catch (e) {
      if (_workspaceGeneration != workspaceGenerationAtSend ||
          _projectGeneration != projectGenerationAtSend) {
        return;
      }
      chatMessages.add({
        'role': 'error',
        'content':
            'Không thể gửi yêu cầu tới COSA runtime. Yêu cầu chưa được tạo thành Mission. ($e)',
      });
      isChatLoading.value = false;
    }
  }

  /// Bong bóng trả lời đang chờ SSE của run hiện tại — để khi stream bị huỷ
  /// (gửi tin nhắn mới, đổi Project) hoặc kết thúc mà chưa có nội dung, nó
  /// được chuyển thành lỗi rõ ràng thay vì nằm lại thành bong bóng rỗng.
  Map<String, String>? _pendingAssistantMsg;

  void _markAssistantFailed(Map<String, String> assistantMsg, String reason) {
    if ((assistantMsg['content'] ?? '').isNotEmpty) return;
    final idx = chatMessages.indexOf(assistantMsg);
    if (idx == -1) return;
    assistantMsg['role'] = 'error';
    assistantMsg['content'] = reason;
    chatMessages[idx] = assistantMsg;
  }

  void _subscribeChatSse(String runId, Map<String, String> assistantMsg) {
    _chatSseSubscription?.cancel();
    final previous = _pendingAssistantMsg;
    if (previous != null && !identical(previous, assistantMsg)) {
      _markAssistantFailed(
        previous,
        'Chưa nhận được phản hồi trước khi gửi yêu cầu mới — xem lại trong Hoạt động dự án.',
      );
    }
    _pendingAssistantMsg = assistantMsg;
    var terminal = false;
    _chatSseSubscription = _chatService
        .streamRunEvents(runId, conversationId: _cofounderConversationId)
        .listen(
          (event) {
            final eventType = event['event_type']?.toString() ?? '';
            final payload = (event['payload'] as Map<String, dynamic>?) ?? {};
            switch (eventType) {
              case 'message.delta':
                final delta = payload['delta']?.toString() ?? '';
                final idx = chatMessages.indexOf(assistantMsg);
                if (idx != -1) {
                  assistantMsg['content'] =
                      (assistantMsg['content'] ?? '') + delta;
                  chatMessages[idx] = assistantMsg;
                }
                break;
              case 'run.completed':
                terminal = true;
                if ((assistantMsg['content'] ?? '').isEmpty &&
                    payload['output'] != null) {
                  final idx = chatMessages.indexOf(assistantMsg);
                  assistantMsg['content'] = payload['output'].toString();
                  if (idx != -1) chatMessages[idx] = assistantMsg;
                }
                _markAssistantFailed(assistantMsg, 'COSA hoàn tất nhưng không có nội dung trả lời.');
                isChatLoading.value = false;
                break;
              case 'run.failed':
              case 'run.cancelled':
                terminal = true;
                final idx = chatMessages.indexOf(assistantMsg);
                if (idx != -1) {
                  // Ưu tiên thông điệp thân thiện từ backend (user_message).
                  final friendly = payload['user_message']?.toString();
                  final reason = payload['error']?.toString() ?? payload['reason']?.toString();
                  assistantMsg['role'] = 'error';
                  assistantMsg['content'] =
                      (assistantMsg['content'] ?? '').isEmpty
                      ? (friendly != null && friendly.isNotEmpty
                          ? friendly
                          : (reason == null || reason.isEmpty
                              ? 'Mission thất bại hoặc bị huỷ.'
                              : 'Mission thất bại: $reason'))
                      : assistantMsg['content']!;
                  chatMessages[idx] = assistantMsg;
                }
                isChatLoading.value = false;
                break;
            }
          },
          onError: (Object e) {
            _markAssistantFailed(assistantMsg, 'Mất kết nối luồng phản hồi của COSA runtime ($e).');
            isChatLoading.value = false;
          },
          onDone: () {
            if (!terminal) {
              _markAssistantFailed(
                assistantMsg,
                'Luồng phản hồi đóng trước khi COSA trả lời — kiểm tra Worker và Model Provider trong Cài đặt.',
              );
            }
            isChatLoading.value = false;
          },
        );
  }
}

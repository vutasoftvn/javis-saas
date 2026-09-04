import 'dart:async';

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/widgets/app_toast.dart';
import '../../../data/models/company_pulse_model.dart';
import '../../../data/models/founder_decision_model.dart';
import '../../../data/models/workforce_pack_model.dart';
import '../../../modules/hologram_hub/services/cofounder_api_service.dart';
import '../../../modules/chat/services/agent_chat_service.dart';
import '../../../modules/chat/models/data_access_declaration.dart';

import '../../../core/network/api_result.dart';
import '../../../core/routing/app_routes.dart';
import '../../../core/services/secure_storage_service.dart';
import '../../../core/session/session_controller.dart';
import '../../../data/models/project_operating_setup_model.dart';
import '../../../data/models/task_kanban_model.dart';
import '../../../modules/strategy/services/project_operating_setup_service.dart';
import '../../../modules/strategy/services/strategy_service.dart';
import '../../../modules/tasks/services/task_service.dart';
import '../../../modules/workforce/models/workforce_mvp_models.dart';
import '../../../modules/workforce/services/workforce_mvp_service.dart';

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
  final AgentChatService _chatService = AgentChatService();

  // Fix-review (2026-09-02, final review I-1) — cho phép inject
  // `WorkforceMvpService` trong test (mirror DI pattern của
  // `MissionControlController`) thay vì luôn tạo instance thật gọi mạng.
  FounderCommandCenterController({WorkforceMvpService? workforceMvpService})
      : _workforceMvpService = workforceMvpService ?? WorkforceMvpService();

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
  final Rxn<ProjectOperatingSetup> activeProjectSetup =
      Rxn<ProjectOperatingSetup>();

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
    if (projectsList.isEmpty) return true;
    if (projectsList.length == 1) {
      return activeProjectSetup.value?.status != OperatingSetupStatus.active;
    }
    return false;
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
    activeProjectSetup.value = null;
    projectsError.value = null;
    // Fix race (2026-09-03, Task 5) — workspace vừa đổi, danh sách project của
    // tenant CŨ đã bị clear và `loadDashboardData()` sắp chạy lại; hạ cờ để
    // `ProjectSetupGuardMiddleware` đồng bộ KHÔNG nhầm cửa sổ reload này là
    // "workspace mới có 0 project" mà bounce sớm sang `/projects/new`.
    projectsLoadedOnce.value = false;
    pulse.value = null;
    top3Actions.clear();
    pendingDecisions.clear();
    pendingApprovals.clear();
    workforcePacks.clear();
    workforceState.value = WorkforceLoadState.idle;
    approvalsState.value = WorkforceLoadState.idle;

    // Chat sheet: không được để tin nhắn/gõ dở của workspace cũ lẫn vào
    // workspace mới, và conversation id phải reset để lần gửi tiếp theo tạo
    // conversation MỚI thay vì nối vào conversation của tenant trước.
    _chatSseSubscription?.cancel();
    _chatSseSubscription = null;
    _cofounderConversationId = null;
    chatMessages.clear();
    chatInputController.clear();
    isChatLoading.value = false;

    if (reload) {
      loadDashboardData();
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

      final activeProjectId = projects.isNotEmpty
          ? projects.first['id']?.toString()
          : null;
      final activeProjectStage = projects.isNotEmpty
          ? (projects.first['lifecycleStage'] ??
                projects.first['project_stage'] ??
                projects.first['lifecycle_stage'])
          : null;

      if (activeProjectId != null) {
        try {
          final setupService = ProjectOperatingSetupService();
          activeProjectSetup.value = await setupService.get(activeProjectId);
        } catch (e) {
          debugPrint('[FounderCommandCenter] get setup error: $e');
          activeProjectSetup.value = null;
        }
      } else {
        activeProjectSetup.value = null;
      }

      final pulseRes = await CoFounderApiService.getCompanyPulse(
        workspaceId: wsId,
        projectId: activeProjectId,
        stage: activeProjectStage?.toString(),
      );
      final top3Res = (activeProjectId != null)
          ? await CoFounderApiService.getTop3Focus(
              workspaceId: wsId,
              projectId: activeProjectId,
            )
          : <NextBestActionModel>[];
      final decisionsRes = await CoFounderApiService.listPendingDecisions(
        workspaceId: wsId,
      );
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
  Future<void> resolveDecision({
    required int decisionId,
    required String optionKey,
    String? founderNotes,
  }) async {
    final success = await CoFounderApiService.resolveDecision(
      decisionId: decisionId,
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

  /// Đánh dấu hoàn thành / chưa hoàn thành 1 "Hành động tuần đầu" — `action.id`
  /// chính là id của `operating.tasks` (đã materialize 1-1 khi lưu/activate
  /// operating setup, xem
  /// docs/superpowers/specs/2026-09-04-command-center-dashboard-redesign-design.md).
  Future<void> toggleFirstWeekActionStatus(FirstWeekActionDraft action) async {
    final actionId = action.id;
    if (actionId == null) return;
    final newStatus = action.status == TaskKanbanStatus.done
        ? TaskKanbanStatus.todo
        : TaskKanbanStatus.done;
    try {
      await TaskService().updateTaskStatus(actionId, newStatus.value);
      await _refreshActiveProjectSetup();
    } catch (e) {
      debugPrint('[FounderCommandCenter] toggleFirstWeekActionStatus error: $e');
      AppToast.error('Không thể cập nhật trạng thái task: $e');
    }
  }

  /// Đặt/xoá giờ dự kiến thực hiện cho 1 "Hành động tuần đầu".
  Future<void> updateFirstWeekActionSchedule(
    FirstWeekActionDraft action,
    DateTime? plannedStartAt,
  ) async {
    final actionId = action.id;
    if (actionId == null) return;
    try {
      await TaskService().updateTaskSchedule(actionId, plannedStartAt);
      await _refreshActiveProjectSetup();
    } catch (e) {
      debugPrint('[FounderCommandCenter] updateFirstWeekActionSchedule error: $e');
      AppToast.error('Không thể cập nhật giờ thực hiện: $e');
    }
  }

  Future<void> _refreshActiveProjectSetup() async {
    final activeProjectId = projectsList.isNotEmpty
        ? projectsList.first['id']?.toString()
        : null;
    if (activeProjectId == null) return;
    try {
      activeProjectSetup.value =
          await ProjectOperatingSetupService().get(activeProjectId);
    } catch (e) {
      debugPrint('[FounderCommandCenter] refresh setup error: $e');
    }
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

    final generationAtSend = _workspaceGeneration;
    chatMessages.add({'role': 'user', 'content': trimmed});
    chatInputController.clear();
    isChatLoading.value = true;

    try {
      if (_cofounderConversationId == null) {
        final created = await _chatService.createConversation(
          title: 'Founder Command Center',
          activeAgentProfile: 'operations',
        );
        if (_workspaceGeneration != generationAtSend) {
          // Workspace đã đổi (switch/logout) trong lúc chờ tạo conversation —
          // `resetForWorkspace()` đã dọn state cho workspace MỚI rồi, không
          // được gán conversation-id của workspace CŨ đè lên đây.
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
        content: trimmed,
        dataAccess: _chatDataAccess,
      );
      if (_workspaceGeneration != generationAtSend) {
        // Cùng lý do — không được thêm tin nhắn assistant/subscribe SSE của
        // request thuộc workspace CŨ vào state workspace MỚI.
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
      if (_workspaceGeneration != generationAtSend) return;
      chatMessages.add({
        'role': 'error',
        'content':
            'Không thể gửi yêu cầu tới COSA runtime. Yêu cầu chưa được tạo thành Mission. ($e)',
      });
      isChatLoading.value = false;
    }
  }

  void _subscribeChatSse(String runId, Map<String, String> assistantMsg) {
    _chatSseSubscription?.cancel();
    _chatSseSubscription = _chatService
        .streamRunEvents(runId)
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
                if ((assistantMsg['content'] ?? '').isEmpty &&
                    payload['output'] != null) {
                  final idx = chatMessages.indexOf(assistantMsg);
                  assistantMsg['content'] = payload['output'].toString();
                  if (idx != -1) chatMessages[idx] = assistantMsg;
                }
                isChatLoading.value = false;
                break;
              case 'run.failed':
              case 'run.cancelled':
                final idx = chatMessages.indexOf(assistantMsg);
                if (idx != -1) {
                  assistantMsg['role'] = 'error';
                  assistantMsg['content'] =
                      (assistantMsg['content'] ?? '').isEmpty
                      ? 'Mission thất bại hoặc bị huỷ.'
                      : assistantMsg['content']!;
                  chatMessages[idx] = assistantMsg;
                }
                isChatLoading.value = false;
                break;
            }
          },
          onError: (_) => isChatLoading.value = false,
          onDone: () => isChatLoading.value = false,
        );
  }
}

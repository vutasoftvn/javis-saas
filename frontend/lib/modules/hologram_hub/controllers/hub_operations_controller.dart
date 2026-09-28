import 'package:get/get.dart';

import '../../../core/network/api_result.dart';
import '../../projects/services/project_agent_deployment_service.dart';
import '../../projects/services/project_operating_loop_service.dart';
import '../../settings/models/settings_models.dart';
import '../../settings/services/permissions_service.dart';
import '../../settings/services/settings_mvp_service.dart';
import '../../skills/services/founder_asset_service.dart';
import '../models/hub_operations_models.dart';
import '../models/project_startup_team.dart';
import '../services/hub_operations_service.dart';
import '../services/project_startup_team_service.dart';

/// Tab của card vận hành ở hub (spec 2026-09-27-hub-operations-workspace-design §2).
enum HubOperationsTab { tasks, schedules, tools, agents }

/// Kết quả một hành động để view hiện thông báo; `ok == false` kèm lỗi đã rút gọn.
class HubActionOutcome {
  const HubActionOutcome(this.ok, [this.message]);
  final bool ok;
  final String? message;
}

/// State cho card vận hành 4 tab — tách khỏi `FounderCommandCenterController` (1400+ dòng).
///
/// - Mỗi tab nạp lười lần đầu được mở; đổi Project thì xoá dữ liệu cũ và nạp lại các tab
///   đã mở. `_epoch` chặn phản hồi của Project cũ ghi đè Project mới (cùng pattern epoch
///   guard của các mixin hub).
/// - Tab Tasks đọc `operatingLoop` do controller hub nạp sẵn; card chỉ đổi trạng thái rồi
///   gọi `onTasksChanged` để hub nạp lại.
class HubOperationsController extends GetxController {
  HubOperationsController({
    HubOperationsService? operationsService,
    ProjectOperatingLoopService? loopService,
    ProjectStartupTeamService? teamService,
    SettingsMvpService? settingsService,
    PermissionsService? permissionsService,
    FounderAssetService? founderAssetService,
    ProjectAgentDeploymentService? agentDeploymentService,
  })  : _operations = operationsService ?? HubOperationsService(),
        _loop = loopService ?? ProjectOperatingLoopService(),
        _team = teamService ?? ProjectStartupTeamService(),
        _settings = settingsService ?? SettingsMvpService(),
        _permissions = permissionsService ?? PermissionsService(),
        founderAssetService = founderAssetService ?? FounderAssetService(),
        agentDeploymentService = agentDeploymentService ?? ProjectAgentDeploymentService();

  final HubOperationsService _operations;
  final ProjectOperatingLoopService _loop;
  final ProjectStartupTeamService _team;
  final SettingsMvpService _settings;
  final PermissionsService _permissions;

  /// C2 (Task 9) — wizard "Tạo agent mới" trong tab Agent dùng chung 2 service này (giữ nguyên
  /// pattern injectable qua constructor của các service khác trong controller, để widget test
  /// thay bằng test double thay vì gọi mạng thật).
  final FounderAssetService founderAssetService;
  final ProjectAgentDeploymentService agentDeploymentService;

  final Rxn<String> projectId = Rxn<String>();
  final Rx<HubOperationsTab> tab = HubOperationsTab.tasks.obs;

  final RxList<HubSchedule> schedules = <HubSchedule>[].obs;
  final RxMap<String, HubScheduleExecution> lastExecutions = <String, HubScheduleExecution>{}.obs;
  final RxBool schedulesLoading = false.obs;
  final RxnString schedulesError = RxnString();

  final RxList<ConnectorStatusModel> connectors = <ConnectorStatusModel>[].obs;
  final RxList<HubAgentGrant> grants = <HubAgentGrant>[].obs;
  final RxBool toolsLoading = false.obs;
  final RxnString toolsError = RxnString();

  final RxList<ProjectStartupTeamMember> team = <ProjectStartupTeamMember>[].obs;
  final RxBool agentsLoading = false.obs;
  final RxnString agentsError = RxnString();

  /// Id đang có hành động dở (task/lịch/grant/profile) để khoá nút tương ứng.
  final RxSet<String> busy = <String>{}.obs;

  final Set<HubOperationsTab> _loaded = {};
  int _epoch = 0;

  /// Gọi khi Project đang chọn đổi (hoặc lần đầu).
  void bindProject(String? id) {
    if (id == projectId.value) return;
    _epoch++;
    projectId.value = id;
    schedules.clear();
    lastExecutions.clear();
    grants.clear();
    connectors.clear();
    team.clear();
    schedulesError.value = null;
    toolsError.value = null;
    agentsError.value = null;
    busy.clear();
    final reload = Set<HubOperationsTab>.from(_loaded);
    _loaded.clear();
    if (id == null) return;
    for (final t in reload) {
      ensureLoaded(t);
    }
    ensureLoaded(tab.value);
  }

  void selectTab(HubOperationsTab next) {
    tab.value = next;
    ensureLoaded(next);
  }

  void ensureLoaded(HubOperationsTab t) {
    if (projectId.value == null || _loaded.contains(t)) return;
    _loaded.add(t);
    refreshTab(t);
  }

  Future<void> refreshTab(HubOperationsTab t) {
    switch (t) {
      case HubOperationsTab.tasks:
        return Future.value();
      case HubOperationsTab.schedules:
        return loadSchedules();
      case HubOperationsTab.tools:
        return loadTools();
      case HubOperationsTab.agents:
        return loadTeam();
    }
  }

  // ── Tasks ──────────────────────────────────────────────────────────────

  Future<HubActionOutcome> advanceTask(
    String taskId,
    String status, {
    Future<void> Function()? onTasksChanged,
  }) async {
    final pid = projectId.value;
    if (pid == null) return const HubActionOutcome(false);
    busy.add(taskId);
    try {
      final res = await _loop.updateTaskStatus(pid, taskId: taskId, status: status);
      if (res is ApiFailure) return HubActionOutcome(false, _failureMessage(res));
      if (onTasksChanged != null) await onTasksChanged();
      return const HubActionOutcome(true);
    } finally {
      busy.remove(taskId);
    }
  }

  // ── Lịch ───────────────────────────────────────────────────────────────

  Future<void> loadSchedules() async {
    final pid = projectId.value;
    if (pid == null) return;
    final epoch = _epoch;
    schedulesLoading.value = true;
    schedulesError.value = null;
    final res = await _operations.listSchedules();
    if (epoch != _epoch) return;
    switch (res) {
      case ApiSuccess(:final data):
        final mine = data.where((s) => s.projectId == pid && !s.isArchived).toList();
        schedules.assignAll(mine);
        _ensureTeamForLabels();
        await _loadLastExecutions(mine, epoch);
      case ApiFailure():
        schedulesError.value = _failureMessage(res);
    }
    if (epoch == _epoch) schedulesLoading.value = false;
  }

  Future<void> _loadLastExecutions(List<HubSchedule> items, int epoch) async {
    final results = await Future.wait(
      items.map((s) => _operations.listScheduleExecutions(s.id, limit: 1)),
    );
    if (epoch != _epoch) return;
    final map = <String, HubScheduleExecution>{};
    for (var i = 0; i < items.length; i++) {
      final latest = results[i].dataOrNull;
      if (latest != null && latest.isNotEmpty) map[items[i].id] = latest.first;
    }
    lastExecutions.assignAll(map);
  }

  Future<HubActionOutcome> setScheduleState(String scheduleId, String state) async {
    busy.add(scheduleId);
    try {
      final res = await _operations.setScheduleState(scheduleId, state);
      switch (res) {
        case ApiSuccess(:final data):
          final idx = schedules.indexWhere((s) => s.id == scheduleId);
          if (data.isArchived) {
            schedules.removeWhere((s) => s.id == scheduleId);
          } else if (idx >= 0) {
            schedules[idx] = data;
          }
          return const HubActionOutcome(true);
        case ApiFailure():
          return HubActionOutcome(false, _failureMessage(res));
      }
    } finally {
      busy.remove(scheduleId);
    }
  }

  Future<HubActionOutcome> runScheduleNow(String scheduleId) async {
    busy.add(scheduleId);
    try {
      final res = await _operations.runScheduleNow(scheduleId);
      if (res is ApiFailure) return HubActionOutcome(false, _failureMessage(res));
      await loadSchedules();
      return const HubActionOutcome(true);
    } finally {
      busy.remove(scheduleId);
    }
  }

  // ── Công cụ ────────────────────────────────────────────────────────────

  Future<void> loadTools() async {
    final pid = projectId.value;
    if (pid == null) return;
    final epoch = _epoch;
    toolsLoading.value = true;
    toolsError.value = null;
    final results = await Future.wait([
      _settings.listConnectors(),
      _operations.listAgentGrants(pid),
    ]);
    if (epoch != _epoch) return;
    final connectorRes = results[0] as ApiResult<List<ConnectorStatusModel>>;
    final grantRes = results[1] as ApiResult<List<HubAgentGrant>>;
    // Connector thuộc organization; lỗi phần này không che danh sách quyền và ngược lại.
    connectors.assignAll(connectorRes.dataOrNull ?? const []);
    switch (grantRes) {
      case ApiSuccess(:final data):
        grants.assignAll(data);
        _ensureTeamForLabels();
      case ApiFailure():
        toolsError.value = _failureMessage(grantRes);
    }
    toolsLoading.value = false;
  }

  Future<HubActionOutcome> revokeGrant(HubAgentGrant grant, {required String reason}) async {
    busy.add(grant.grantId);
    try {
      final res = await _permissions.revokeAgentCapabilityGrant(
        grantId: grant.grantId,
        reason: reason,
      );
      if (res is ApiFailure) return HubActionOutcome(false, _failureMessage(res));
      await loadTools();
      return const HubActionOutcome(true);
    } finally {
      busy.remove(grant.grantId);
    }
  }

  // ── Agent ──────────────────────────────────────────────────────────────

  Future<void> loadTeam() async {
    final pid = projectId.value;
    if (pid == null) return;
    final epoch = _epoch;
    agentsLoading.value = true;
    agentsError.value = null;
    final res = await _team.fetchTeam(pid);
    if (epoch != _epoch) return;
    switch (res) {
      case ApiSuccess(:final data):
        // Co-Founder luôn sẵn sàng trong chat, không có trạng thái để quản lý ở đây.
        team.assignAll(data.where((m) => m.displayState != TeamDisplayState.chatReady));
      case ApiFailure():
        agentsError.value = _failureMessage(res);
    }
    agentsLoading.value = false;
  }

  Future<HubActionOutcome> setAgentActive(ProjectStartupTeamMember member, bool active) async {
    final pid = projectId.value;
    final version = member.assignmentVersion;
    if (pid == null) return const HubActionOutcome(false);
    busy.add(member.profileKey);
    try {
      final ApiResult<ProjectStartupTeamMember> res = active
          ? await _team.activate(
              projectId: pid,
              profileKey: member.profileKey,
              expectedVersion: version ?? 1,
            )
          : await _team.pause(
              projectId: pid,
              profileKey: member.profileKey,
              expectedVersion: version ?? 1,
            );
      if (res is ApiFailure) return HubActionOutcome(false, _failureMessage(res));
      await loadTeam();
      // Kích hoạt/tạm dừng đổi quyền agent; tab Công cụ phải nạp lại khi mở.
      _loaded.remove(HubOperationsTab.tools);
      return const HubActionOutcome(true);
    } finally {
      busy.remove(member.profileKey);
    }
  }

  /// Nhãn hiển thị của profile agent (lấy từ startup team), không hiển thị key thô.
  String? profileLabel(String profileKey) {
    for (final m in team) {
      if (m.profileKey == profileKey) return m.label;
    }
    return null;
  }

  void _ensureTeamForLabels() {
    if (team.isEmpty && !agentsLoading.value) {
      _loaded.add(HubOperationsTab.agents);
      loadTeam();
    }
  }

  String _failureMessage(ApiResult<Object?> res) {
    if (res is ApiFailure<Object?>) return res.failure.message;
    return '';
  }
}

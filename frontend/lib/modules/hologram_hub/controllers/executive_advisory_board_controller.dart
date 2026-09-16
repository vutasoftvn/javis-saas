import 'package:get/get.dart';
import '../models/executive_advisory_board.dart';
import '../services/executive_advisory_board_service.dart';
import '../services/project_startup_team_service.dart';
import '../../projects/services/project_agent_deployment_service.dart';

class ExecutiveAdvisoryBoardController extends GetxController {
  final ExecutiveAdvisoryBoardService _service;
  final ProjectStartupTeamService _startupTeamService;
  final ProjectAgentDeploymentService _deploymentService;

  final RxList<ExecutiveAdvisorRole> roles = <ExecutiveAdvisorRole>[].obs;
  final Rxn<ExecutiveDeliberation> currentDeliberation =
      Rxn<ExecutiveDeliberation>();
  final RxBool isLoading = false.obs;
  final RxBool isMutating = false.obs;
  final RxnString errorMessage = RxnString();

  String? currentProjectId;

  ExecutiveAdvisoryBoardController({
    ExecutiveAdvisoryBoardService? service,
    ProjectStartupTeamService? startupTeamService,
    ProjectAgentDeploymentService? deploymentService,
  }) : _service = service ?? ExecutiveAdvisoryBoardService(),
       _startupTeamService = startupTeamService ?? ProjectStartupTeamService(),
       _deploymentService =
           deploymentService ?? ProjectAgentDeploymentService();

  /// Tải danh sách roles của hội đồng cố vấn theo Project.
  Future<void> loadBoard(String projectId) async {
    currentProjectId = projectId;
    isLoading.value = true;
    errorMessage.value = null;

    final result = await _service.fetchRoles(projectId);
    isLoading.value = false;

    if (result.isSuccess && result.dataOrNull != null) {
      roles.assignAll(result.dataOrNull!);
    } else {
      errorMessage.value =
          result.failureOrNull?.message ?? 'Không thể tải danh sách ban cố vấn';
    }
  }

  /// Kích hoạt vai trò cố vấn (Founder-only) — Workspace-scoped (Task 9:
  /// activation không còn theo Project, không còn khái niệm preset).
  /// `projectId` chỉ dùng để reload lại board hiện tại sau khi mutation
  /// thành công, không phải scope của mutation.
  Future<bool> activateRole({
    required String workspaceId,
    required String projectId,
    required String roleKey,
    required int expectedVersion,
    String? idempotencyKey,
  }) async {
    isMutating.value = true;
    errorMessage.value = null;

    final result = await _service.activateRole(
      workspaceId: workspaceId,
      roleKey: roleKey,
      expectedVersion: expectedVersion,
      idempotencyKey: idempotencyKey,
    );
    isMutating.value = false;

    if (result.isSuccess && result.dataOrNull != null) {
      await loadBoard(projectId);
      if (errorMessage.value != null) {
        return false;
      }
      return true;
    } else {
      errorMessage.value =
          result.failureOrNull?.message ?? 'Không thể kích hoạt vai trò';
      return false;
    }
  }

  /// Kích hoạt agent nền của role trong Project trước khi Founder bật Office.
  Future<bool> activateUnderlyingProfile({
    required String projectId,
    required String profileKey,
  }) async {
    isMutating.value = true;
    errorMessage.value = null;
    final team = await _startupTeamService.fetchTeam(projectId);
    if (!team.isSuccess || team.dataOrNull == null) {
      isMutating.value = false;
      errorMessage.value =
          team.failureOrNull?.message ?? 'Không thể tải agent nền';
      return false;
    }

    final member = team.dataOrNull!.firstWhereOrNull(
      (item) => item.profileKey == profileKey,
    );
    if (member == null || member.assignmentVersion == null) {
      isMutating.value = false;
      errorMessage.value = 'Không tìm thấy agent nền cho role này';
      return false;
    }
    final activation = await _startupTeamService.activateMember(
      projectId: projectId,
      profileKey: profileKey,
      expectedVersion: member.assignmentVersion!,
    );
    isMutating.value = false;
    if (!activation.isSuccess || activation.dataOrNull == null) {
      errorMessage.value =
          activation.failureOrNull?.message ?? 'Không thể kích hoạt agent nền';
      return false;
    }
    await loadBoard(projectId);
    return errorMessage.value == null;
  }

  Future<bool> deployRoleAgent({
    required String projectId,
    required String workspaceAgentId,
  }) async {
    isMutating.value = true;
    errorMessage.value = null;
    final result = await _deploymentService.deploy(
      projectId,
      workspaceAgentId: workspaceAgentId,
    );
    isMutating.value = false;
    if (!result.isSuccess || result.dataOrNull == null) {
      errorMessage.value =
          result.failureOrNull?.message ?? 'Không thể deploy Agent vào Project';
      return false;
    }
    await loadBoard(projectId);
    return errorMessage.value == null;
  }

  /// Repair/retry có chủ đích cho Project P0 cũ. Server là nguồn sự thật cho
  /// stage, quyền Founder và trạng thái idempotent của cả bốn role.
  Future<bool> bootstrapP0Core({required String projectId}) async {
    isMutating.value = true;
    errorMessage.value = null;
    final result = await _service.bootstrapP0Core(projectId: projectId);
    isMutating.value = false;
    if (!result.isSuccess || result.dataOrNull != true) {
      errorMessage.value =
          result.failureOrNull?.message ?? 'Không thể khởi tạo P0 Core';
      return false;
    }
    await loadBoard(projectId);
    return errorMessage.value == null;
  }

  /// Tạm dừng / vô hiệu hoá vai trò cố vấn — Workspace-scoped. Reload lại
  /// board từ server bằng `projectId` hiện tại.
  Future<bool> disableRole({
    required String workspaceId,
    required String projectId,
    required String roleKey,
    required int expectedVersion,
    String? reason,
    String? idempotencyKey,
  }) async {
    isMutating.value = true;
    errorMessage.value = null;

    final result = await _service.disableRole(
      workspaceId: workspaceId,
      roleKey: roleKey,
      expectedVersion: expectedVersion,
      reason: reason,
      idempotencyKey: idempotencyKey,
    );
    isMutating.value = false;

    if (result.isSuccess && result.dataOrNull != null) {
      await loadBoard(projectId);
      if (errorMessage.value != null) {
        return false;
      }
      return true;
    } else {
      errorMessage.value =
          result.failureOrNull?.message ?? 'Không thể tạm dừng vai trò';
      return false;
    }
  }

  /// Tạo bản nháp Deliberation mới.
  Future<ExecutiveDeliberation?> createDraft({
    required String projectId,
    required String title,
  }) async {
    isMutating.value = true;
    errorMessage.value = null;

    final result = await _service.createDraft(
      projectId: projectId,
      title: title,
    );
    isMutating.value = false;

    if (result.isSuccess && result.dataOrNull != null) {
      currentDeliberation.value = result.dataOrNull;
      return result.dataOrNull;
    } else {
      errorMessage.value =
          result.failureOrNull?.message ?? 'Không thể tạo bản nháp nghị sự';
      return null;
    }
  }

  /// Đóng khung Deliberation.
  Future<bool> frameDeliberation({
    required String projectId,
    required String deliberationId,
    required String question,
    required List<String> roleKeys,
    int? expectedVersion,
    String? idempotencyKey,
  }) async {
    isMutating.value = true;
    errorMessage.value = null;

    final result = await _service.frameDeliberation(
      projectId: projectId,
      deliberationId: deliberationId,
      question: question,
      roleKeys: roleKeys,
      expectedVersion: expectedVersion,
      idempotencyKey: idempotencyKey,
    );
    isMutating.value = false;

    if (result.isSuccess && result.dataOrNull != null) {
      currentDeliberation.value = result.dataOrNull;
      return true;
    } else {
      errorMessage.value =
          result.failureOrNull?.message ?? 'Không thể đóng khung nghị sự';
      return false;
    }
  }

  /// Lấy thông tin chi tiết một Deliberation.
  Future<void> loadDeliberation({
    required String projectId,
    required String deliberationId,
  }) async {
    isLoading.value = true;
    errorMessage.value = null;

    final result = await _service.getDeliberation(
      projectId: projectId,
      deliberationId: deliberationId,
    );
    isLoading.value = false;

    if (result.isSuccess && result.dataOrNull != null) {
      currentDeliberation.value = result.dataOrNull;
    } else {
      errorMessage.value =
          result.failureOrNull?.message ?? 'Không thể tải phiên nghị sự';
    }
  }

  /// Founder ghi nhận quyết định.
  Future<bool> appendDecision({
    required String projectId,
    required String deliberationId,
    required String decisionType,
    String? notes,
  }) async {
    isMutating.value = true;
    errorMessage.value = null;

    final result = await _service.appendDecision(
      projectId: projectId,
      deliberationId: deliberationId,
      decisionType: decisionType,
      notes: notes,
    );
    isMutating.value = false;

    if (result.isSuccess && result.dataOrNull != null) {
      currentDeliberation.value = result.dataOrNull;
      return true;
    } else {
      errorMessage.value =
          result.failureOrNull?.message ?? 'Không thể ghi nhận quyết định';
      return false;
    }
  }

  /// Huỷ Deliberation.
  Future<bool> cancelDeliberation({
    required String projectId,
    required String deliberationId,
    String? reason,
  }) async {
    isMutating.value = true;
    errorMessage.value = null;

    final result = await _service.cancelDeliberation(
      projectId: projectId,
      deliberationId: deliberationId,
      reason: reason,
    );
    isMutating.value = false;

    if (result.isSuccess && result.dataOrNull != null) {
      currentDeliberation.value = result.dataOrNull;
      return true;
    } else {
      errorMessage.value =
          result.failureOrNull?.message ?? 'Không thể huỷ phiên nghị sự';
      return false;
    }
  }
}

import 'package:get/get.dart';
import '../../../core/network/api_result.dart';
import '../models/permission_models.dart';
import '../services/permissions_service.dart';

class PermissionsController extends GetxController {
  final PermissionsService _service;

  PermissionsController({PermissionsService? service})
      : _service = service ?? PermissionsService();

  final RxBool isLoading = false.obs;
  final RxBool isSaving = false.obs;
  final RxBool isSimulating = false.obs;
  final RxBool isFounder = true.obs;

  final RxInt activeTab = 0.obs;

  final Rxn<PermissionsDataModel> permissionsData = Rxn<PermissionsDataModel>();
  final Rxn<WorkspaceAuthorityOverviewModel> overviewData = Rxn<WorkspaceAuthorityOverviewModel>();
  final RxString conflictMessage = ''.obs;
  final RxString successMessage = ''.obs;
  final RxMap<String, String> validationErrors = <String, String>{}.obs;

  // Local draft changes (roleId -> (permissionKey -> effect))
  final RxMap<String, Map<String, String>> draftRolePermissions =
      <String, Map<String, String>>{}.obs;

  // Simulation state
  final RxString selectedSimulationAction = ''.obs;
  final Rxn<SimulatePermissionsResponse> simulationResult =
      Rxn<SimulatePermissionsResponse>();

  @override
  void onInit() {
    super.onInit();
    loadPermissions();
  }

  Future<void> loadOverview() async {
    final result = await _service.fetchOverview();
    if (result is ApiSuccess<WorkspaceAuthorityOverviewModel>) {
      overviewData.value = result.data;
      isFounder.value = true;
    } else if (result is ApiFailure<WorkspaceAuthorityOverviewModel>) {
      if (result.failure.code == ApiFailureCode.forbidden) {
        isFounder.value = false;
        conflictMessage.value = 'Chỉ Founder mới có quyền quản lý phân quyền và lực lượng lao động.';
      } else if (result.failure.code == ApiFailureCode.conflict) {
        conflictMessage.value = 'Xung đột trạng thái: Vui lòng tải lại trang để kiểm tra.';
      } else {
        conflictMessage.value = result.failure.message;
      }
    }
  }

  Future<void> loadPermissions() async {
    isLoading.value = true;
    conflictMessage.value = '';
    successMessage.value = '';
    validationErrors.clear();

    await loadOverview();

    final result = await _service.getPermissions();
    if (result is ApiSuccess<PermissionsDataModel>) {
      permissionsData.value = result.data;
      isFounder.value = true;
      if (result.data.catalog.isNotEmpty && selectedSimulationAction.value.isEmpty) {
        selectedSimulationAction.value = result.data.catalog.first.permissionKey;
      }
    } else if (result is ApiFailure<PermissionsDataModel>) {
      if (result.failure.code == ApiFailureCode.forbidden) {
        isFounder.value = false;
        conflictMessage.value = 'Chỉ Founder mới có quyền quản lý phân quyền và lực lượng lao động.';
      } else if (result.failure.code == ApiFailureCode.conflict) {
        conflictMessage.value = 'Xung đột phiên bản: Vui lòng tải lại và kiểm tra.';
      } else {
        conflictMessage.value = result.failure.message;
      }
    }
    isLoading.value = false;
  }

  void updateDraftPermission(String roleId, String permissionKey, String effect) {
    final currentRolePerms = Map<String, String>.from(
      draftRolePermissions[roleId] ?? {},
    );
    currentRolePerms[permissionKey] = effect;
    draftRolePermissions[roleId] = currentRolePerms;
  }

  String getPermissionEffect(String roleId, String permissionKey) {
    // Ưu tiên draft local
    if (draftRolePermissions[roleId]?.containsKey(permissionKey) == true) {
      return draftRolePermissions[roleId]![permissionKey]!;
    }
    // Lấy từ data hiện tại
    final role = permissionsData.value?.roles.firstWhereOrNull((r) => r.id == roleId);
    final perm = role?.permissions.firstWhereOrNull((p) => p.permissionKey == permissionKey);
    return perm?.effect ?? 'DENY';
  }

  Future<void> savePermissions() async {
    final data = permissionsData.value;
    if (data == null || isSaving.value) return;

    isSaving.value = true;
    conflictMessage.value = '';
    successMessage.value = '';
    validationErrors.clear();

    final mutations = <Map<String, dynamic>>[];

    draftRolePermissions.forEach((roleId, perms) {
      perms.forEach((permissionKey, effect) {
        mutations.add({
          'kind': 'SET_ROLE_PERMISSION',
          'roleId': roleId,
          'permissionKey': permissionKey,
          'effect': effect,
        });
      });
    });

    if (mutations.isEmpty) {
      isSaving.value = false;
      return;
    }

    final result = await _service.updatePermissions(
      expectedVersion: data.version,
      reason: 'Cập nhật phân quyền từ Settings',
      mutations: mutations,
    );

    if (result is ApiSuccess<Map<String, dynamic>>) {
      draftRolePermissions.clear();
      successMessage.value = 'Đã lưu quyền';
      await loadPermissions();
    } else if (result is ApiFailure<Map<String, dynamic>>) {
      if (result.failure.code == ApiFailureCode.forbidden) {
        isFounder.value = false;
      }
      conflictMessage.value = result.failure.message;
    }


    isSaving.value = false;
  }

  Future<bool> createGrant({
    required String agentWorkforceMemberId,
    required String capabilityId,
    String? projectId,
    String? legalEntityId,
    Map<String, dynamic>? constraints,
  }) async {
    if (isSaving.value) return false;
    isSaving.value = true;
    conflictMessage.value = '';
    validationErrors.clear();

    final result = await _service.createAgentCapabilityGrant(
      agentWorkforceMemberId: agentWorkforceMemberId,
      capabilityId: capabilityId,
      projectId: projectId,
      legalEntityId: legalEntityId,
      constraints: constraints,
    );

    isSaving.value = false;

    if (result is ApiSuccess<AgentCapabilityGrantModel>) {
      successMessage.value = 'Đã cấp quyền capability cho AI Agent';
      await loadPermissions();
      return true;
    } else if (result is ApiFailure<AgentCapabilityGrantModel>) {
      if (result.failure.code == ApiFailureCode.forbidden) {
        conflictMessage.value = 'Chỉ Founder mới có quyền cấp capability grant.';
      } else if (result.failure.code == ApiFailureCode.conflict) {
        conflictMessage.value = 'Xung đột quyền: Vui lòng tải lại danh sách.';
      } else if (result.failure.code == ApiFailureCode.invalidRequest) {
        validationErrors['capabilityId'] = result.failure.message;
      } else {
        conflictMessage.value = result.failure.message;
      }
      return false;
    }
    return false;
  }

  Future<bool> revokeGrant({
    required String grantId,
    required String reason,
  }) async {
    if (isSaving.value) return false;
    isSaving.value = true;
    conflictMessage.value = '';

    final result = await _service.revokeAgentCapabilityGrant(
      grantId: grantId,
      reason: reason,
    );

    isSaving.value = false;

    if (result is ApiSuccess<Map<String, dynamic>>) {
      successMessage.value = 'Đã thu hồi quyền capability';
      await loadPermissions();
      return true;
    } else if (result is ApiFailure<Map<String, dynamic>>) {
      if (result.failure.code == ApiFailureCode.forbidden) {
        conflictMessage.value = 'Chỉ Founder mới có quyền thu hồi capability grant.';
      } else {
        conflictMessage.value = result.failure.message;
      }
      return false;
    }
    return false;
  }

  Future<void> simulateAction(String action, {String? memberId}) async {
    isSimulating.value = true;
    selectedSimulationAction.value = action;
    conflictMessage.value = '';

    final result = await _service.simulatePermissions(
      action: action,
      memberId: memberId,
    );

    if (result is ApiSuccess<SimulatePermissionsResponse>) {
      simulationResult.value = result.data;
    } else if (result is ApiFailure<SimulatePermissionsResponse>) {
      conflictMessage.value = result.failure.message;
    }

    isSimulating.value = false;
  }
}

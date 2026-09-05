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

  final Rxn<PermissionsDataModel> permissionsData = Rxn<PermissionsDataModel>();
  final RxString conflictMessage = ''.obs;
  final RxString successMessage = ''.obs;

  // Local draft changes (roleId -> (permissionKey -> effect))
  // Chỉnh dropdown chưa save KHÔNG thay đổi effectivePermissions của permissionsData!
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

  Future<void> loadPermissions() async {
    isLoading.value = true;
    conflictMessage.value = '';
    successMessage.value = '';

    final result = await _service.getPermissions();
    if (result is ApiSuccess<PermissionsDataModel>) {
      permissionsData.value = result.data;
      if (result.data.catalog.isNotEmpty && selectedSimulationAction.value.isEmpty) {
        selectedSimulationAction.value = result.data.catalog.first.permissionKey;
      }
    } else if (result is ApiFailure<PermissionsDataModel>) {
      conflictMessage.value = result.failure.message;
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
    if (data == null) return;

    isSaving.value = true;
    conflictMessage.value = '';
    successMessage.value = '';

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
      // Giữ form và hiển thị lỗi inline / conflict
      conflictMessage.value = result.failure.message;
    }

    isSaving.value = false;
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

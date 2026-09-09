import 'package:flutter/foundation.dart';
import 'package:get/get.dart';
import '../routing/module_routes.dart';
import 'workspace_capability_manifest_controller.dart';
import 'workspace_capability_manifest_model.dart';

/// Founder Trial R1 — module visibility is no longer a second routing authority.
/// It now derives entirely from [WorkspaceCapabilityManifestController]; the old
/// `/platform/workspaces/:id/module-visibility` service is removed.
abstract interface class ModuleVisibilityApi {
  Future<List<ModuleVisibility>> fetchVisibility(String workspaceId);
  Future<bool> setWorkspaceEnabled(String workspaceId, OptionalModule module, bool enabled);
  Future<bool> setUserPreference(String workspaceId, OptionalModule module, bool visible);
}

/// Reads the per-workspace capability manifest and projects the three optional
/// modules onto their R1 surface keys. Operator-only mutations are not exposed
/// to the client in R1 and always return false.
class ManifestBackedVisibilityApi implements ModuleVisibilityApi {
  ManifestBackedVisibilityApi({WorkspaceCapabilityManifestController? manifest})
      : _injected = manifest;

  final WorkspaceCapabilityManifestController? _injected;

  WorkspaceCapabilityManifestController get _manifest =>
      _injected ??
      (Get.isRegistered<WorkspaceCapabilityManifestController>()
          ? Get.find<WorkspaceCapabilityManifestController>()
          : Get.put(WorkspaceCapabilityManifestController()));

  static const Map<OptionalModule, String> _surfaceKey = {
    OptionalModule.crm: 'crm.contact_lead',
    OptionalModule.finance: 'finance.project_budget',
    // No live legal surface in R1 → always hidden.
    OptionalModule.legal: 'strategy.__legal_placeholder__',
  };

  @override
  Future<List<ModuleVisibility>> fetchVisibility(String workspaceId) async {
    await _manifest.reloadForWorkspace(workspaceId);
    return _surfaceKey.entries.map((e) {
      final status = _manifest.statusFor(e.value);
      final visible = status == SurfaceStatus.available ||
          status == SurfaceStatus.pilot ||
          status == SurfaceStatus.configurationRequired;
      return ModuleVisibility(
        module: e.key,
        workspaceEnabled: visible,
        userVisible: true,
      );
    }).toList();
  }

  @override
  Future<bool> setWorkspaceEnabled(String workspaceId, OptionalModule module, bool enabled) async =>
      false;

  @override
  Future<bool> setUserPreference(String workspaceId, OptionalModule module, bool visible) async =>
      false;
}

enum OptionalModule {
  finance,
  legal,
  crm,
}

extension OptionalModuleWire on OptionalModule {
  String get key => switch (this) {
        OptionalModule.finance => 'finance',
        OptionalModule.legal => 'legal',
        OptionalModule.crm => 'crm',
      };

  static OptionalModule? tryParse(String key) {
    return switch (key.toLowerCase().trim()) {
      'finance' => OptionalModule.finance,
      'legal' => OptionalModule.legal,
      'crm' || 'sales' => OptionalModule.crm,
      _ => null,
    };
  }

  WorkspaceModule get workspaceModule => switch (this) {
        OptionalModule.finance => WorkspaceModule.finance,
        OptionalModule.legal => WorkspaceModule.legal,
        OptionalModule.crm => WorkspaceModule.sales,
      };
}

OptionalModule? optionalModuleForWorkspaceModule(WorkspaceModule module) {
  return switch (module) {
    WorkspaceModule.finance => OptionalModule.finance,
    WorkspaceModule.legal => OptionalModule.legal,
    WorkspaceModule.sales => OptionalModule.crm,
    _ => null,
  };
}

class ModuleVisibility {
  const ModuleVisibility({
    required this.module,
    required this.workspaceEnabled,
    required this.userVisible,
  });

  final OptionalModule module;
  final bool workspaceEnabled;
  final bool userVisible;

  bool get effectiveVisible => workspaceEnabled && userVisible;

  ModuleVisibility copyWith({
    bool? workspaceEnabled,
    bool? userVisible,
  }) {
    return ModuleVisibility(
      module: module,
      workspaceEnabled: workspaceEnabled ?? this.workspaceEnabled,
      userVisible: userVisible ?? this.userVisible,
    );
  }
}

class ModuleVisibilityController extends GetxController {
  ModuleVisibilityController({ModuleVisibilityApi? api})
      : _api = api ?? ManifestBackedVisibilityApi();

  final ModuleVisibilityApi _api;
  final RxMap<OptionalModule, ModuleVisibility> entries = <OptionalModule, ModuleVisibility>{}.obs;
  final RxBool isLoading = false.obs;
  final RxBool hasLoadedSnapshot = false.obs;
  String? _currentWorkspaceId;

  String? get currentWorkspaceId => _currentWorkspaceId;

  Future<void> reloadForWorkspace(String workspaceId) async {
    _currentWorkspaceId = workspaceId;
    isLoading.value = true;
    try {
      final list = await _api.fetchVisibility(workspaceId);
      final map = <OptionalModule, ModuleVisibility>{};
      for (final item in list) {
        map[item.module] = item;
      }
      entries.assignAll(map);
      hasLoadedSnapshot.value = true;
    } catch (e) {
      debugPrint('[ModuleVisibilityController] reloadForWorkspace error: $e');
      hasLoadedSnapshot.value = false;
      entries.clear();
    } finally {
      isLoading.value = false;
    }
  }

  void clear() {
    _currentWorkspaceId = null;
    entries.clear();
    hasLoadedSnapshot.value = false;
  }

  bool isVisible(WorkspaceModule module) {
    final opt = optionalModuleForWorkspaceModule(module);
    if (opt == null) return true;
    if (!hasLoadedSnapshot.value) return false;
    final entry = entries[opt];
    if (entry == null) return false;
    return entry.effectiveVisible;
  }

  Future<bool> setMyVisible(OptionalModule module, bool visible) async {
    final wsId = _currentWorkspaceId;
    if (wsId == null) return false;
    final prev = entries[module];
    try {
      final ok = await _api.setUserPreference(wsId, module, visible);
      if (ok) {
        entries[module] = ModuleVisibility(
          module: module,
          workspaceEnabled: prev?.workspaceEnabled ?? true,
          userVisible: visible,
        );
        return true;
      }
      return false;
    } catch (e) {
      debugPrint('[ModuleVisibilityController] setMyVisible error: $e');
      return false;
    }
  }

  Future<bool> setWorkspaceEnabled(OptionalModule module, bool enabled) async {
    final wsId = _currentWorkspaceId;
    if (wsId == null) return false;
    final prev = entries[module];
    try {
      final ok = await _api.setWorkspaceEnabled(wsId, module, enabled);
      if (ok) {
        entries[module] = ModuleVisibility(
          module: module,
          workspaceEnabled: enabled,
          userVisible: prev?.userVisible ?? true,
        );
        return true;
      }
      return false;
    } catch (e) {
      debugPrint('[ModuleVisibilityController] setWorkspaceEnabled error: $e');
      return false;
    }
  }
}

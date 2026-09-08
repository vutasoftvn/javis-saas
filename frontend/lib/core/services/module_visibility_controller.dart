import 'package:flutter/foundation.dart';
import 'package:get/get.dart';
import '../routing/module_routes.dart';
import 'module_visibility_service.dart';

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
      : _api = api ?? ModuleVisibilityService();

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

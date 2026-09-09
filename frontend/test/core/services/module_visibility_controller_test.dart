import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/routing/module_routes.dart';
import 'package:frontend/core/services/module_visibility_controller.dart';

class FakeVisibilityApi implements ModuleVisibilityApi {
  FakeVisibilityApi({
    this.crmEnabled = true,
    this.crmVisible = true,
    this.financeEnabled = true,
    this.financeVisible = true,
    this.legalEnabled = true,
    this.legalVisible = true,
  });

  bool crmEnabled;
  bool crmVisible;
  bool financeEnabled;
  bool financeVisible;
  bool legalEnabled;
  bool legalVisible;

  @override
  Future<List<ModuleVisibility>> fetchVisibility(String workspaceId) async {
    return [
      ModuleVisibility(
        module: OptionalModule.crm,
        workspaceEnabled: crmEnabled,
        userVisible: crmVisible,
      ),
      ModuleVisibility(
        module: OptionalModule.finance,
        workspaceEnabled: financeEnabled,
        userVisible: financeVisible,
      ),
      ModuleVisibility(
        module: OptionalModule.legal,
        workspaceEnabled: legalEnabled,
        userVisible: legalVisible,
      ),
    ];
  }

  @override
  Future<bool> setWorkspaceEnabled(String workspaceId, OptionalModule module, bool enabled) async {
    switch (module) {
      case OptionalModule.crm:
        crmEnabled = enabled;
        break;
      case OptionalModule.finance:
        financeEnabled = enabled;
        break;
      case OptionalModule.legal:
        legalEnabled = enabled;
        break;
    }
    return true;
  }

  @override
  Future<bool> setUserPreference(String workspaceId, OptionalModule module, bool visible) async {
    switch (module) {
      case OptionalModule.crm:
        crmVisible = visible;
        break;
      case OptionalModule.finance:
        financeVisible = visible;
        break;
      case OptionalModule.legal:
        legalVisible = visible;
        break;
    }
    return true;
  }
}

void main() {
  group('ModuleVisibilityController', () {
    test('CRM maps to WorkspaceModule.sales and an absent preference defaults visible', () async {
      final controller = ModuleVisibilityController(api: FakeVisibilityApi(crmEnabled: true, crmVisible: true));
      await controller.reloadForWorkspace('w1');
      expect(controller.isVisible(WorkspaceModule.sales), isTrue);
    });

    test('Workspace disabled module is hidden regardless of user preference', () async {
      final controller = ModuleVisibilityController(
        api: FakeVisibilityApi(financeEnabled: false, financeVisible: true),
      );
      await controller.reloadForWorkspace('w1');
      expect(controller.isVisible(WorkspaceModule.finance), isFalse);
    });

    test('User hidden module is hidden even if workspace enabled', () async {
      final controller = ModuleVisibilityController(
        api: FakeVisibilityApi(legalEnabled: true, legalVisible: false),
      );
      await controller.reloadForWorkspace('w1');
      expect(controller.isVisible(WorkspaceModule.legal), isFalse);
    });

    test('Core modules always return isVisible true', () async {
      final controller = ModuleVisibilityController(
        api: FakeVisibilityApi(financeEnabled: false, legalEnabled: false, crmEnabled: false),
      );
      await controller.reloadForWorkspace('w1');
      expect(controller.isVisible(WorkspaceModule.tasks), isTrue);
      expect(controller.isVisible(WorkspaceModule.hub), isTrue);
      expect(controller.isVisible(WorkspaceModule.settings), isTrue);
      expect(controller.isVisible(WorkspaceModule.approvals), isTrue);
    });

    test('setMyVisible updates userVisible state', () async {
      final api = FakeVisibilityApi(financeEnabled: true, financeVisible: true);
      final controller = ModuleVisibilityController(api: api);
      await controller.reloadForWorkspace('w1');

      final success = await controller.setMyVisible(OptionalModule.finance, false);
      expect(success, isTrue);
      expect(controller.isVisible(WorkspaceModule.finance), isFalse);
      expect(api.financeVisible, isFalse);
    });

    test('setWorkspaceEnabled updates workspaceEnabled state', () async {
      final api = FakeVisibilityApi(legalEnabled: true, legalVisible: true);
      final controller = ModuleVisibilityController(api: api);
      await controller.reloadForWorkspace('w1');

      final success = await controller.setWorkspaceEnabled(OptionalModule.legal, false);
      expect(success, isTrue);
      expect(controller.isVisible(WorkspaceModule.legal), isFalse);
      expect(api.legalEnabled, isFalse);
    });

    test('fail-closed: optional modules are hidden before snapshot is loaded', () {
      final controller = ModuleVisibilityController(api: FakeVisibilityApi());
      // No reloadForWorkspace called yet
      expect(controller.hasLoadedSnapshot.value, isFalse);
      expect(controller.isVisible(WorkspaceModule.finance), isFalse);
      expect(controller.isVisible(WorkspaceModule.legal), isFalse);
      expect(controller.isVisible(WorkspaceModule.sales), isFalse);
      // Core modules remain visible
      expect(controller.isVisible(WorkspaceModule.tasks), isTrue);
      expect(controller.isVisible(WorkspaceModule.hub), isTrue);
    });

    test('fail-closed: optional modules remain hidden if API throws error during reload', () async {
      final controller = ModuleVisibilityController(api: _ThrowingVisibilityApi());
      await controller.reloadForWorkspace('w1');
      expect(controller.hasLoadedSnapshot.value, isFalse);
      expect(controller.isVisible(WorkspaceModule.finance), isFalse);
      expect(controller.isVisible(WorkspaceModule.legal), isFalse);
      expect(controller.isVisible(WorkspaceModule.sales), isFalse);
      expect(controller.isVisible(WorkspaceModule.tasks), isTrue);
    });

    test('fail-closed: clear resets snapshot and hides optional modules', () async {
      final controller = ModuleVisibilityController(api: FakeVisibilityApi());
      await controller.reloadForWorkspace('w1');
      expect(controller.isVisible(WorkspaceModule.finance), isTrue);

      controller.clear();
      expect(controller.hasLoadedSnapshot.value, isFalse);
      expect(controller.isVisible(WorkspaceModule.finance), isFalse);
      expect(controller.isVisible(WorkspaceModule.tasks), isTrue);
    });
  });
}

class _ThrowingVisibilityApi implements ModuleVisibilityApi {
  @override
  Future<List<ModuleVisibility>> fetchVisibility(String workspaceId) async {
    throw Exception('Simulated network error');
  }

  @override
  Future<bool> setWorkspaceEnabled(String workspaceId, OptionalModule module, bool enabled) async {
    throw Exception('Simulated network error');
  }

  @override
  Future<bool> setUserPreference(String workspaceId, OptionalModule module, bool visible) async {
    throw Exception('Simulated network error');
  }
}

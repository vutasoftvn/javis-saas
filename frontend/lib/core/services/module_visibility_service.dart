import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../network/api_client.dart';
import 'module_visibility_controller.dart';

abstract interface class ModuleVisibilityApi {
  Future<List<ModuleVisibility>> fetchVisibility(String workspaceId);
  Future<bool> setWorkspaceEnabled(String workspaceId, OptionalModule module, bool enabled);
  Future<bool> setUserPreference(String workspaceId, OptionalModule module, bool visible);
}

class ModuleVisibilityService implements ModuleVisibilityApi {
  ModuleVisibilityService();

  @override
  Future<List<ModuleVisibility>> fetchVisibility(String workspaceId) async {
    final res = await ApiClient.get('/platform/workspaces/$workspaceId/module-visibility');
    if (res.statusCode == 200) {
      final decoded = jsonDecode(res.body) as Map<String, dynamic>;
      final rawList = (decoded['data'] != null && decoded['data']['modules'] != null)
          ? decoded['data']['modules'] as List<dynamic>
          : (decoded['modules'] ?? decoded['items'] ?? []) as List<dynamic>;

      final result = <ModuleVisibility>[];
      for (final item in rawList) {
        if (item is Map<String, dynamic>) {
          final rawKey = (item['moduleKey'] ?? item['module_key'])?.toString() ?? '';
          final optModule = OptionalModuleWire.tryParse(rawKey);
          if (optModule != null) {
            final wsEnabled = (item['workspaceEnabled'] ?? item['workspace_enabled']) as bool? ?? true;
            final userVis = (item['userVisible'] ?? item['user_visible']) as bool? ?? true;
            result.add(ModuleVisibility(
              module: optModule,
              workspaceEnabled: wsEnabled,
              userVisible: userVis,
            ));
          }
        }
      }
      return result;
    }
    debugPrint('[ModuleVisibilityService] fetchVisibility HTTP ${res.statusCode}: ${res.body}');
    throw Exception('Failed to fetch module visibility');
  }

  @override
  Future<bool> setWorkspaceEnabled(String workspaceId, OptionalModule module, bool enabled) async {
    final res = await ApiClient.put(
      '/platform/workspaces/$workspaceId/module-visibility/${module.key}',
      body: {'enabled': enabled},
    );
    return res.statusCode == 200;
  }

  @override
  Future<bool> setUserPreference(String workspaceId, OptionalModule module, bool visible) async {
    final res = await ApiClient.put(
      '/platform/workspaces/$workspaceId/module-visibility/${module.key}/preference',
      body: {'visible': visible},
    );
    return res.statusCode == 200;
  }
}

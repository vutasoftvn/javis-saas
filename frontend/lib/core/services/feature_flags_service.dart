import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../../core/network/api_client.dart';

class FeatureFlagsService {
  Future<Map<String, bool>> load() async {
    final prefs = await SharedPreferences.getInstance();
    final workspaceId = prefs.getString('workspace_id');
    if (workspaceId == null || workspaceId.isEmpty) return const {};

    final response = await ApiClient.get(
      '/platform/feature-flags?workspace_id=${Uri.encodeQueryComponent(workspaceId)}',
    );
    if (response.statusCode < 200 || response.statusCode >= 300) return const {};

    final decoded = jsonDecode(response.body);
    final flags = decoded is Map ? decoded['flags'] : null;
    if (flags is! Map) return const {};
    return flags.map((key, value) => MapEntry('$key', value == true));
  }
}

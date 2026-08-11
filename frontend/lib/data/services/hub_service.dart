import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/network/api_client.dart';

class HubService {
  Future<String?> _getWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('workspace_id');
  }

  Future<Map<String, dynamic>?> getHubSummary() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.get('/admin/$workspaceId/hub-summary');
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('HubService.getHubSummary error: $e');
    }
    return null;
  }
}

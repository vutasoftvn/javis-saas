import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../core/network/api_client.dart';

class AiService {
  Future<String?> _getWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('workspace_id');
  }

  Future<List<dynamic>> getModels() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) {
      debugPrint('AiService.getModels: no workspace_id cached, skipping call');
      return [];
    }

    final response = await ApiClient.get('/ai/models?workspace_id=$workspaceId');
    if (response.statusCode != 200) {
      debugPrint('AiService.getModels: request failed (${response.statusCode}) ${response.body}');
      return [];
    }
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return data['models'] ?? [];
  }

  Future<Map<String, dynamic>?> getUsage({String period = '30d'}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return null;

    final response = await ApiClient.get('/ai/usage?workspace_id=$workspaceId&period=$period');
    if (response.statusCode != 200) return null;
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<bool> saveOpenRouterKey({required String apiKey}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return false;

    final wsIdNum = int.tryParse(workspaceId);
    final response = await ApiClient.post(
      '/ai/openrouter-key',
      body: {
        'workspace_id': wsIdNum ?? workspaceId,
        'api_key': apiKey,
      },
    );
    return response.statusCode == 200;
  }

  Future<bool> deleteOpenRouterKey() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return false;

    final response = await ApiClient.delete('/ai/openrouter-key?workspace_id=$workspaceId');
    return response.statusCode == 200;
  }
}


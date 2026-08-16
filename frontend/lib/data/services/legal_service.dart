import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/network/api_client.dart';

class LegalService {
  Future<String?> _getWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('workspace_id');
  }

  Future<Map<String, dynamic>> getStatus() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) {
      return {'function': 'LEGAL', 'open_checklist_items': 0, 'open_obligations': 0};
    }
    try {
      final response = await ApiClient.get('/legal/status?workspace_id=$workspaceId');
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('LegalService.getStatus error: $e');
    }
    return {'function': 'LEGAL', 'open_checklist_items': 0, 'open_obligations': 0};
  }

  Future<Map<String, dynamic>?> analyzeContract({
    required String contractText,
    String contractType = 'COMMERCIAL_SERVICE',
  }) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.post(
        '/legal/reviews/analyze?workspace_id=$workspaceId',
        body: {
          'contract_text': contractText,
          'contract_type': contractType,
        },
      );

      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as Map<String, dynamic>?;
      }
    } catch (e) {
      debugPrint('LegalService.analyzeContract error: $e');
    }
    return null;
  }

  Future<List<dynamic>> getChecklist() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return [];

    try {
      final response = await ApiClient.get('/legal/checklist?workspace_id=$workspaceId');
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as List<dynamic>? ?? [];
      }
    } catch (e) {
      debugPrint('LegalService.getChecklist error: $e');
    }
    return [];
  }

  Future<List<dynamic>> getObligations() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return [];

    try {
      final response = await ApiClient.get('/legal/obligations?workspace_id=$workspaceId');
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as List<dynamic>? ?? [];
      }
    } catch (e) {
      debugPrint('LegalService.getObligations error: $e');
    }
    return [];
  }

  Future<Map<String, dynamic>?> createChecklistItem(String title) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.post(
        '/legal/checklist?workspace_id=$workspaceId',
        body: {'title': title},
      );
      if (response.statusCode == 201 || response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('LegalService.createChecklistItem error: $e');
    }
    return null;
  }
}

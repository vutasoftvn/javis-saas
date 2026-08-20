import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/network/api_client.dart';

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

  Future<Map<String, dynamic>?> executeQuickAction(String actionKey) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.post(
        '/admin/$workspaceId/quick-actions/execute',
        body: {'action_key': actionKey},
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('HubService.executeQuickAction error: $e');
    }
    return null;
  }

  Future<Map<String, dynamic>?> getCommandCenterData() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.get('/workspaces/$workspaceId/hub/command-center');
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        if (decoded['data'] != null) {
          return decoded['data'] as Map<String, dynamic>;
        }
        return decoded;
      }
    } catch (e) {
      debugPrint('HubService.getCommandCenterData error: $e');
    }
    return null;
  }

  Future<Map<String, dynamic>?> quickApprove({
    required String approvalId,
    required String decision,
    String? reason,
  }) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.post(
        '/workspaces/$workspaceId/hub/quick-approve',
        body: {
          'approval_id': approvalId,
          'decision': decision,
          if (reason != null && reason.isNotEmpty) 'reason': reason,
        },
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('HubService.quickApprove error: $e');
    }
    return null;
  }

  Future<List<Map<String, dynamic>>> getMissions({String? status}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return [];

    try {
      final queryParam = status != null ? '?status=$status' : '';
      final response = await ApiClient.get('/workspaces/$workspaceId/missions$queryParam');
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        if (decoded['data'] != null) {
          return List<Map<String, dynamic>>.from(decoded['data'] as List);
        }
      }
    } catch (e) {
      debugPrint('HubService.getMissions error: $e');
    }
    return [];
  }

  Future<Map<String, dynamic>?> getMissionDetail(String missionId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.get('/workspaces/$workspaceId/missions/$missionId');
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        if (decoded['data'] != null) {
          return decoded['data'] as Map<String, dynamic>;
        }
        return decoded;
      }
    } catch (e) {
      debugPrint('HubService.getMissionDetail error: $e');
    }
    return null;
  }
}


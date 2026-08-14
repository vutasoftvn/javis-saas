import 'dart:convert';
import '../../../core/network/api_client.dart';
import '../../../data/services/workspace_service.dart';
import '../models/mission_event.dart';

class MissionControlService extends WorkspaceService {
  Future<ChiefOfStaffMission?> orchestrateMission(String goal) async {
    final response = await ApiClient.post(
      '/agents/mission-control/orchestrate',
      body: {'goal': goal},
    );

    if (response.statusCode >= 200 && response.statusCode < 300) {
      final data = jsonDecode(response.body);
      if (data is Map<String, dynamic>) {
        return ChiefOfStaffMission.fromJson(data);
      }
    }
    return null;
  }

  Future<List<dynamic>> getPendingApprovals() async {
    final res = await getJson('/agents/approvals');
    if (res is List) {
      return res;
    }
    return [];
  }

  Future<bool> approveAction(String approvalId) async {
    final response = await ApiClient.post('/agents/approvals/$approvalId/approve');
    return response.statusCode >= 200 && response.statusCode < 300;
  }

  Future<bool> rejectAction(String approvalId, {String? reason}) async {
    final response = await ApiClient.post(
      '/agents/approvals/$approvalId/reject',
      body: {'reason': reason ?? 'Rejected by user'},
    );
    return response.statusCode >= 200 && response.statusCode < 300;
  }
}

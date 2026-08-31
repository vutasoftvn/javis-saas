import 'dart:convert';
import '../../../core/network/api_client.dart';
import '../../../modules/organization/services/workspace_service.dart';
import '../models/mission_event.dart';

class MissionControlService extends WorkspaceService {
  Future<ChiefOfStaffMission?> orchestrateMission(String goal) async {
    final response = await ApiClient.post(
      '/agents/mission-control/orchestrate',
      body: {'goal': goal},
    );

    // 204 No Content không có body — jsonDecode('') sẽ throw FormatException.
    if (response.statusCode >= 200 &&
        response.statusCode < 300 &&
        response.body.isNotEmpty) {
      final data = jsonDecode(response.body);
      if (data is Map<String, dynamic>) {
        return ChiefOfStaffMission.fromJson(data);
      }
    }
    return null;
  }
}

import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/network/api_client.dart';
import 'package:get/get.dart';
import '../../../core/controllers/company_scope_controller.dart';

class WorkflowsService {
  Future<String?> _getWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('workspace_id');
  }

  String _appendScopeParams(String url) {
    if (Get.isRegistered<CompanyScopeController>()) {
      final scope = Get.find<CompanyScopeController>();
      if (scope.operatingUnitId.value != null) {
        url += '&operating_unit_id=${scope.operatingUnitId.value}';
      }
      if (scope.offeringId.value != null) {
        url += '&offering_id=${scope.offeringId.value}';
      }
      if (scope.initiativeId.value != null) {
        url += '&initiative_id=${scope.initiativeId.value}';
      }
    }
    return url;
  }

  Future<List<dynamic>> getDefinitions() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];

    final response = await ApiClient.get(_appendScopeParams('/workflows/definitions?workspace_id=$workspaceId'));
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return data['definitions'] ?? [];
    }
    return [];
  }

  Future<List<dynamic>> getRuns({int limit = 50, int offset = 0}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];

    final response = await ApiClient.get(_appendScopeParams('/workflows/runs?workspace_id=$workspaceId&limit=$limit&offset=$offset'));
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return data['runs'] ?? [];
    }
    return [];
  }

  Future<Map<String, dynamic>?> triggerRun(String definitionId, {Map<String, dynamic>? input}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return null;

    final response = await ApiClient.post(
      _appendScopeParams('/workflows/definitions/$definitionId/run?workspace_id=$workspaceId'),
      body: input != null ? {'input_jsonb': input} : null,
    );
    if (response.statusCode == 201) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  Future<Map<String, dynamic>?> getRunDetails(String runId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return null;

    final response = await ApiClient.get(_appendScopeParams('/workflows/runs/$runId?workspace_id=$workspaceId'));
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }
}

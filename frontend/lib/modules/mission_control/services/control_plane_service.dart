import 'dart:convert';
import '../../../core/network/api_client.dart';

class ControlPlaneService {
  /// Fetch all active and recent goals
  Future<List<Map<String, dynamic>>> getGoals({String? status}) async {
    final statusQuery = status != null ? '?status=$status' : '';
    final response = await ApiClient.get('/agent/goals$statusQuery');
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((e) => e as Map<String, dynamic>).toList();
    }
    return [];
  }

  /// Create a high-level founder goal with auto plan decomposition
  Future<Map<String, dynamic>?> createGoal({
    required String title,
    String? description,
    String goalType = 'business_goal',
    Map<String, dynamic>? targetMetric,
    bool autoPlan = true,
    String? domainHint,
  }) async {
    final response = await ApiClient.post(
      '/agent/goals',
      body: {
        'title': title,
        'description': description,
        'goal_type': goalType,
        'target_metric': targetMetric,
        'auto_plan': autoPlan,
        'domain_hint': domainHint,
      },
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  /// Get details of an execution plan including steps and evaluation
  Future<Map<String, dynamic>?> getPlan(String planId) async {
    final response = await ApiClient.get('/agent/plans/$planId');
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  /// Execute next pending step or a specific step
  Future<Map<String, dynamic>?> executePlanStep(String planId, {String? stepId}) async {
    final query = stepId != null ? '?step_id=$stepId' : '';
    final response = await ApiClient.post('/agent/plans/$planId/execute-step$query');
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  /// List agent runs with optional status and pagination
  Future<List<Map<String, dynamic>>> listRuns({String? status, int limit = 20, int offset = 0}) async {
    final params = <String>[];
    if (status != null) params.add('status=$status');
    params.add('limit=$limit');
    params.add('offset=$offset');
    final queryString = params.isNotEmpty ? '?${params.join('&')}' : '';
    final response = await ApiClient.get('/agent/runs$queryString');
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      if (data is Map<String, dynamic> && data['items'] is List) {
        return (data['items'] as List).map((e) => e as Map<String, dynamic>).toList();
      } else if (data is List) {
        return data.map((e) => e as Map<String, dynamic>).toList();
      }
    }
    return [];
  }

  /// Fetch execution events trace for a run or plan
  Future<List<Map<String, dynamic>>> getRunEvents(String runId) async {
    final response = await ApiClient.get('/agent/runs/$runId/events');
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((e) => e as Map<String, dynamic>).toList();
    }
    return [];
  }

  /// Central Agent Approvals
  Future<List<Map<String, dynamic>>> getPendingApprovals() async {
    final response = await ApiClient.get('/agents/approvals');
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((e) => e as Map<String, dynamic>).toList();
    }
    return [];
  }

  /// Approve an L3A action
  Future<bool> approveAction(String approvalId, {String? reason}) async {
    final response = await ApiClient.post(
      '/agents/approvals/$approvalId/approve',
      body: reason != null ? {'reason': reason} : null,
    );
    return response.statusCode == 200;
  }

  /// Reject an action
  Future<bool> rejectAction(String approvalId, {String? reason}) async {
    final response = await ApiClient.post(
      '/agents/approvals/$approvalId/reject',
      body: reason != null ? {'reason': reason} : null,
    );
    return response.statusCode == 200;
  }
}

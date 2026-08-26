import 'dart:convert';
import '../../../core/services/secure_storage_service.dart';
import '../../../core/network/api_client.dart';
import '../../../data/models/agent_model.dart';

class AgentsService {
  Future<String?> _getWorkspaceId() async {
    return SecureStorageService.read('workspace_id');
  }

  /// Lấy tổng hợp chỉ số Dashboard Master Control Plane
  Future<Map<String, dynamic>?> getDashboardSummary() async {
    final response = await ApiClient.get('/workforce/dashboard-summary');
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  /// Lấy danh sách typed AgentModel
  Future<List<AgentModel>> getAgentsList({String? department}) async {
    final raw = await getAgents(department: department);
    return raw.map((item) {
      if (item is Map<String, dynamic>) {
        return AgentModel.fromJson(item);
      }
      return AgentModel.fromJson(Map<String, dynamic>.from(item as Map));
    }).toList();
  }

  /// Lấy danh sách Agents trong Workspace/Company
  Future<List<dynamic>> getAgents({String? department}) async {
    final deptQuery = department != null && department != 'All' ? '?department=$department' : '';
    final response = await ApiClient.get('/workforce/agents$deptQuery');
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data is List ? data : (data['agents'] ?? []);
    }
    
    // Fallback legacy endpoint
    final workspaceId = await _getWorkspaceId();
    if (workspaceId != null) {
      final fallbackResp = await ApiClient.get('/agents/?workspace_id=$workspaceId');
      if (fallbackResp.statusCode == 200) {
        final data = jsonDecode(fallbackResp.body) as Map<String, dynamic>;
        return data['agents'] ?? [];
      }
    }
    return [];
  }

  /// Lấy sơ đồ cây phân cấp Org Chart
  Future<Map<String, dynamic>?> getOrgChart() async {
    final response = await ApiClient.get('/workforce/org-chart');
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  /// Test run trực tiếp Agent
  Future<Map<String, dynamic>?> testRunAgent(
    String agentKey, {
    required String prompt,
    String? systemPromptOverride,
    String? modelOverride,
    double temperature = 0.2,
  }) async {
    final response = await ApiClient.post(
      '/workforce/agents/$agentKey/test-run',
      body: {
        'prompt': prompt,
        'system_prompt_override': systemPromptOverride,
        'model_override': modelOverride,
        'temperature': temperature,
      },
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  /// Lấy danh sách Runtimes khả dụng
  Future<List<dynamic>> getRuntimes() async {
    final response = await ApiClient.get('/workforce/runtimes');
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as List<dynamic>;
    }
    return [];
  }

  /// Lấy danh sách typed AgentRunModel
  Future<List<AgentRunModel>> getRunsList({String? agentKey, String? status, int limit = 20, int offset = 0}) async {
    final raw = await getRuns(agentKey: agentKey, status: status, limit: limit, offset: offset);
    return raw.map((item) {
      if (item is Map<String, dynamic>) {
        return AgentRunModel.fromJson(item);
      }
      return AgentRunModel.fromJson(Map<String, dynamic>.from(item as Map));
    }).toList();
  }

  /// Lấy danh sách các lần chạy AgentRun
  Future<List<dynamic>> getRuns({String? agentKey, String? status, int limit = 20, int offset = 0}) async {
    final params = <String>[];
    if (agentKey != null) params.add('agent_key=$agentKey');
    if (status != null && status != 'All') params.add('status=$status');
    params.add('limit=$limit');
    params.add('offset=$offset');
    final queryStr = params.isNotEmpty ? '?${params.join('&')}' : '';
    
    final response = await ApiClient.get('/workforce/runs$queryStr');
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as List<dynamic>;
    }
    return [];
  }

  /// Xem chi tiết phiên chạy và các bước AgentStep
  Future<Map<String, dynamic>?> getRunDetail(dynamic runId) async {
    final response = await ApiClient.get('/workforce/runs/$runId');
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  Future<Map<String, dynamic>?> createAgent(Map<String, dynamic> agentData) async {
    final response = await ApiClient.post(
      '/workforce/agents',
      body: agentData,
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  Future<Map<String, dynamic>?> updateAgent(String agentId, Map<String, dynamic> agentData) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return null;

    final response = await ApiClient.patch(
      '/agents/$agentId?workspace_id=$workspaceId',
      body: agentData,
    );
    
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  Future<bool> deleteAgent(String agentId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return false;

    final response = await ApiClient.delete(
      '/agents/$agentId?workspace_id=$workspaceId',
    );

    return response.statusCode == 204;
  }

  Future<Map<String, dynamic>?> resetSystemPrompt(String agentId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return null;

    final response = await ApiClient.post(
      '/agents/$agentId/system_prompt:reset?workspace_id=$workspaceId',
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  Future<List<dynamic>> listPromptRevisions(String agentId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];

    final response = await ApiClient.get(
      '/agents/$agentId/system_prompt/revisions?workspace_id=$workspaceId',
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data is List ? data : (data['revisions'] ?? []);
    }
    return [];
  }
}

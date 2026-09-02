import 'dart:convert';
import '../../../core/services/secure_storage_service.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_result.dart';
import '../../../data/models/agent_model.dart';
import '../../workforce/services/workforce_mvp_service.dart';

class AgentsService {
  // Task 7 — `getOrgChart`/`getRuns` từng gọi `/workforce/org-chart` và
  // `/workforce/runs` (thiếu prefix `/agent`) qua `ApiClient` thô, rơi vào
  // nhánh business/company runtime thay vì AgentOS thật — 404 vĩnh viễn dù
  // `agents_controller.dart` gọi sống. Tái dùng `WorkforceMvpService` đã có
  // sẵn envelope-unwrap cho đúng các route này thay vì tự chép lại.
  //
  // Fix-review (2026-09-02) — bản đầu tiên vẫn nuốt `ApiFailure` thành
  // `null`/`[]`. Trả thẳng `ApiResult<T>` để `agents_controller.dart` biết
  // chắc chắn "request lỗi" khác "backend trả rỗng thật".
  final WorkforceMvpService _workforceMvpService;

  AgentsService({WorkforceMvpService? workforceMvpService})
      : _workforceMvpService = workforceMvpService ?? WorkforceMvpService();

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

  /// Lấy sơ đồ cây phân cấp Org Chart — canonical `/agent/workforce/org-chart`.
  Future<ApiResult<Map<String, dynamic>>> getOrgChart() => _workforceMvpService.getOrgChart();

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

  /// Lấy danh sách typed AgentRunModel. Không có consumer sống nào gọi
  /// method này (đã `rg` toàn repo) — giữ hành vi rỗng-khi-lỗi cũ vì đây là
  /// đường phụ, ngoài phạm vi honest-failure-propagation của `getRuns`.
  Future<List<AgentRunModel>> getRunsList({String? agentKey, String? status, int limit = 20, int offset = 0}) async {
    final result = await getRuns(agentKey: agentKey, status: status, limit: limit, offset: offset);
    final raw = result.dataOrNull ?? const [];
    return raw.map((item) => AgentRunModel.fromJson(item)).toList();
  }

  /// Lấy danh sách các lần chạy AgentRun — canonical `/agent/workforce/runs`.
  /// Backend thật (`apps/cosa/api/workforce_routes.py:list_runs`) hiện chỉ
  /// nhận `limit`, KHÔNG có filter theo `agent_key`/`status`/`offset` — giữ
  /// tham số trong chữ ký để không phá call site cũ, nhưng không giả vờ gửi
  /// filter mà server không đọc.
  Future<ApiResult<List<Map<String, dynamic>>>> getRuns({
    String? agentKey,
    String? status,
    int limit = 20,
    int offset = 0,
  }) async {
    final result = await _workforceMvpService.listRuns(limit: limit);
    return switch (result) {
      ApiSuccess(data: final runs, meta: final meta) => ApiSuccess(
          data: runs
              .map((r) => {
                    'run_id': r.runId,
                    'workspace_id': r.workspaceId,
                    'agent_spec_id': r.agentSpecId,
                    'agent_spec_version': r.agentSpecVersion,
                    'definition_hash': r.definitionHash,
                    'status': r.status,
                    'created_at': r.createdAt.toIso8601String(),
                    'completed_at': r.completedAt?.toIso8601String(),
                    'total_tokens': r.totalTokens,
                    'error_message': r.errorMessage,
                  })
              .toList(),
          meta: meta,
        ),
      ApiFailure(failure: final f) => ApiFailure(f),
    };
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

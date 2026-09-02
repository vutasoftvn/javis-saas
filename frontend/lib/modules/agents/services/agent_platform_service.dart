import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_result.dart';
import '../../workforce/models/workforce_mvp_models.dart';
import '../../workforce/services/workforce_mvp_service.dart';

class AgentPlatformService {
  // Task 7 — `listApprovals/approveRequest/rejectRequest/getOrgChart` từng tự
  // gọi `/workforce/...` (thiếu prefix `/agent`) qua `ApiClient` thô: path đó
  // rơi vào nhánh business/company runtime (Encore, port 4000) thay vì
  // AgentOS thật (port 8001) — 404 vĩnh viễn dù `hub_control_plane_mixin.dart`
  // (Founder Dashboard) vẫn gọi sống mỗi lần refresh. Tái dùng
  // `WorkforceMvpService` (đã có sẵn envelope-unwrap + `ApiFailure` thật cho
  // đúng các route này) thay vì tự chép lại logic decode — tránh nhân bản
  // kiến trúc. Giữ nguyên type trả về (`Map`/`List<Map>`) để không phải sửa
  // toàn bộ call site đang dùng shape cũ.
  final WorkforceMvpService _workforceMvpService;

  AgentPlatformService({WorkforceMvpService? workforceMvpService})
      : _workforceMvpService = workforceMvpService ?? WorkforceMvpService();

  /// Fetch master control plane dashboard summary
  Future<Map<String, dynamic>?> getDashboardSummary() async {
    try {
      final response = await ApiClient.get('/workforce/dashboard-summary');
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
      debugPrint('[AgentPlatformService] getDashboardSummary failed: ${response.statusCode}');
    } catch (e) {
      debugPrint('[AgentPlatformService] getDashboardSummary error: $e');
    }
    return null;
  }

  /// List all agents in the registry with optional department filter
  Future<List<Map<String, dynamic>>> listAgents({String? department}) async {
    try {
      final query = department != null ? '?department=$department' : '';
      final response = await ApiClient.get('/workforce/agents$query');
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        if (data.isNotEmpty) {
          return data.map((e) => e as Map<String, dynamic>).toList();
        }
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] listAgents error: $e');
    }
    return default12Agents;
  }

  static const List<Map<String, dynamic>> default12Agents = [
    {
      'id': 1,
      'key': 'founder_copilot',
      'name': 'Founder Copilot & Chief of Staff',
      'role_title': 'Executive Chief of Staff',
      'department': 'Executive Office',
      'description': 'Đồng hành cùng Founder định hình mục tiêu 12-Week Year, điều phối liên phòng ban và đánh giá rủi ro.',
      'agent_type': 'orchestrator',
      'default_model_profile': 'reasoning',
      'risk_level': 1,
      'status': 'idle',
      'enabled': true,
    },
    {
      'id': 2,
      'key': 'general',
      'name': 'General Assistant',
      'role_title': 'Company Knowledge & Helpdesk',
      'department': 'Operations',
      'description': 'Trợ lý tổng quát xử lý hội thoại, giải đáp thắc mắc và hướng dẫn sử dụng hệ thống.',
      'agent_type': 'general',
      'default_model_profile': 'fast',
      'risk_level': 0,
      'status': 'idle',
      'enabled': true,
    },
    {
      'id': 3,
      'key': 'cfo_agent',
      'name': 'CFO Agent (Finance & Cashflow)',
      'role_title': 'Chief Financial Officer',
      'department': 'Finance',
      'description': 'Phân tích dòng tiền, ngân sách, chi phí, dự báo tài chính và cảnh báo bất thường.',
      'agent_type': 'specialist',
      'default_model_profile': 'reasoning',
      'risk_level': 2,
      'status': 'idle',
      'enabled': true,
    },
    {
      'id': 4,
      'key': 'cmo_agent',
      'name': 'CMO Agent (Marketing & Growth)',
      'role_title': 'Chief Marketing Officer',
      'department': 'Marketing',
      'description': 'Lập kế hoạch chiến dịch marketing, sáng tạo nội dung, quản lý form và đo lường chuyển đổi.',
      'agent_type': 'specialist',
      'default_model_profile': 'reasoning',
      'risk_level': 2,
      'status': 'idle',
      'enabled': true,
    },
    {
      'id': 5,
      'key': 'sales_agent',
      'name': 'Sales Lead Agent',
      'role_title': 'Head of Sales',
      'department': 'Sales',
      'description': 'Quản lý khách hàng tiềm năng, CRM pipeline, follow-up, đánh giá lead và dự báo doanh số.',
      'agent_type': 'specialist',
      'default_model_profile': 'reasoning',
      'risk_level': 2,
      'status': 'idle',
      'enabled': true,
    },
    {
      'id': 6,
      'key': 'tech_lead_agent',
      'name': 'Tech Lead & CTO Agent',
      'role_title': 'Chief Technology Officer',
      'department': 'Engineering',
      'description': 'Quản lý kiến trúc hệ thống, Tech Radar, thiết kế giải pháp và review kỹ thuật.',
      'agent_type': 'specialist',
      'default_model_profile': 'coding',
      'risk_level': 3,
      'status': 'idle',
      'enabled': true,
    },
    {
      'id': 7,
      'key': 'developer',
      'name': 'Developer Agent',
      'role_title': 'Software Engineer',
      'department': 'Engineering',
      'description': 'Hỗ trợ phát triển phần mềm, sinh mã nguồn, review code và thực thi kiểm thử trong Sandbox.',
      'agent_type': 'specialist',
      'default_model_profile': 'coding',
      'risk_level': 3,
      'status': 'idle',
      'enabled': true,
    },
    {
      'id': 8,
      'key': 'devops_agent',
      'name': 'DevOps & Infrastructure Agent',
      'role_title': 'Site Reliability Engineer',
      'department': 'Infrastructure',
      'description': 'Giám sát máy chủ, triển khai hạ tầng, quản lý CI/CD và xử lý sự cố vận hành.',
      'agent_type': 'specialist',
      'default_model_profile': 'coding',
      'risk_level': 3,
      'status': 'idle',
      'enabled': true,
    },
    {
      'id': 9,
      'key': 'legal_agent',
      'name': 'Legal & Compliance Lead',
      'role_title': 'Chief Legal Officer',
      'department': 'Legal & Risk',
      'description': 'Rà soát điều khoản hợp đồng, nghĩa vụ pháp lý và đánh giá hồ sơ ưu đãi chính sách.',
      'agent_type': 'specialist',
      'default_model_profile': 'reasoning',
      'risk_level': 1,
      'status': 'idle',
      'enabled': true,
    },
    {
      'id': 10,
      'key': 'hr_agent',
      'name': 'People & Talent Lead',
      'role_title': 'Head of Human Resources',
      'department': 'People & Culture',
      'description': 'Quản trị cơ cấu nhân sự số, theo dõi hiệu suất làm việc và hỗ trợ onboarding.',
      'agent_type': 'specialist',
      'default_model_profile': 'reasoning',
      'risk_level': 1,
      'status': 'idle',
      'enabled': true,
    },
    {
      'id': 11,
      'key': 'product_agent',
      'name': 'Product Strategy Lead',
      'role_title': 'Head of Product',
      'department': 'Product',
      'description': 'Quản lý Product Spec, User Stories, Roadmap tính năng và phân tích phản hồi người dùng.',
      'agent_type': 'specialist',
      'default_model_profile': 'reasoning',
      'risk_level': 1,
      'status': 'idle',
      'enabled': true,
    },
    {
      'id': 12,
      'key': 'data_analyst_agent',
      'name': 'Scoreboard & Metrics Analyst',
      'role_title': 'Lead Data Analyst',
      'department': 'Analytics',
      'description': 'Tổng hợp chỉ số Scoreboard 12-Week Year, phân tích số liệu kinh doanh và báo cáo tiến độ.',
      'agent_type': 'specialist',
      'default_model_profile': 'reasoning',
      'risk_level': 1,
      'status': 'idle',
      'enabled': true,
    },
  ];

  // Compatibility aliases
  Future<List<Map<String, dynamic>>> getAgents({String? department}) => listAgents(department: department);
  Future<List<Map<String, dynamic>>> getTools() async {
    try {
      final response = await ApiClient.get('/workforce/tools');
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.map((e) => e as Map<String, dynamic>).toList();
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] getTools error: $e');
    }
    return [];
  }

  Future<Map<String, dynamic>?> testRouting(String message) async {
    try {
      final response = await ApiClient.post('/workforce/routing/test', body: {'message': message});
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] testRouting error: $e');
    }
    return null;
  }

  /// Get organization hierarchy — canonical `/agent/workforce/org-chart`.
  Future<Map<String, dynamic>?> getOrgChart() async {
    final result = await _workforceMvpService.getOrgChart();
    if (result case ApiFailure(failure: final f)) {
      debugPrint('[AgentPlatformService] getOrgChart failed: $f');
      return null;
    }
    return (result as ApiSuccess<Map<String, dynamic>>).data;
  }

  /// List pending approvals for human review — canonical
  /// `/agent/workforce/approvals` (KHÔNG PHẢI `/agent/approvals`, stub
  /// `deprecated=True` chưa từng được mount trong `apps/cosa/api/app.py`).
  Future<List<Map<String, dynamic>>> listApprovals({String status = 'PENDING'}) async {
    final result = await _workforceMvpService.listApprovals(status: status);
    if (result case ApiFailure(failure: final f)) {
      debugPrint('[AgentPlatformService] listApprovals failed: $f');
      return [];
    }
    final approvals = (result as ApiSuccess<List<WorkforceApproval>>).data;
    return approvals.map(_approvalToMap).toList();
  }

  Map<String, dynamic> _approvalToMap(WorkforceApproval a) => {
        'id': a.approvalId,
        'approval_id': a.approvalId,
        'run_id': a.runId,
        'tool_call_id': a.toolCallId,
        'checkpoint_ref': a.checkpointRef,
        'action': a.action,
        'subject': a.subject,
        'status': a.status,
        'risk_level': a.riskLevel,
        'required_role': a.requiredRole,
        'policy_id': a.policyId,
        'created_at': a.createdAt.toIso8601String(),
      };

  /// Approve a pending request — canonical decision endpoint
  /// `/agent/workforce/approvals/{id}/decision` (`approved: true`). Backend
  /// không còn 2 route con `/approve`/`/reject` riêng — một endpoint decision
  /// duy nhất nhận cờ `approved`.
  Future<Map<String, dynamic>?> approveRequest(int approvalId, {String? comment}) async {
    final result = await _workforceMvpService.decideApproval(
      '$approvalId',
      approved: true,
      reason: comment ?? 'Approved by Founder via Control Plane UI',
    );
    if (result case ApiFailure(failure: final f)) {
      debugPrint('[AgentPlatformService] approveRequest failed: $f');
      return null;
    }
    return _decisionToMap((result as ApiSuccess<WorkforceApprovalDecision>).data);
  }

  /// Reject a pending request — canonical decision endpoint
  /// `/agent/workforce/approvals/{id}/decision` (`approved: false`).
  Future<Map<String, dynamic>?> rejectRequest(int approvalId, {String? comment}) async {
    final result = await _workforceMvpService.decideApproval(
      '$approvalId',
      approved: false,
      reason: comment ?? 'Rejected by Founder via Control Plane UI',
    );
    if (result case ApiFailure(failure: final f)) {
      debugPrint('[AgentPlatformService] rejectRequest failed: $f');
      return null;
    }
    return _decisionToMap((result as ApiSuccess<WorkforceApprovalDecision>).data);
  }

  Map<String, dynamic> _decisionToMap(WorkforceApprovalDecision d) => {
        'approval_id': d.approvalId,
        'run_id': d.runId,
        'status': d.status,
        'reviewer': d.reviewer,
        'reason': d.reason,
        'decided_at': d.decidedAt.toIso8601String(),
      };

  /// List work products
  Future<List<Map<String, dynamic>>> listWorkProducts({String? status}) async {
    try {
      final query = status != null ? '?status=$status' : '';
      final response = await ApiClient.get('/workforce/work-products$query');
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.map((e) => e as Map<String, dynamic>).toList();
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] listWorkProducts error: $e');
    }
    return [];
  }

  /// Accept a work product
  Future<Map<String, dynamic>?> acceptWorkProduct(int workProductId, {String? feedback}) async {
    try {
      final response = await ApiClient.post(
        '/workforce/work-products/$workProductId/accept',
        body: {'feedback': feedback},
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] acceptWorkProduct error: $e');
    }
    return null;
  }

  /// Request revision for a work product
  Future<Map<String, dynamic>?> requestWorkProductRevision(int workProductId, {required String feedback}) async {
    try {
      final response = await ApiClient.post(
        '/workforce/work-products/$workProductId/revise',
        body: {'feedback': feedback},
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] requestWorkProductRevision error: $e');
    }
    return null;
  }

  /// List ADR Decisions
  Future<List<Map<String, dynamic>>> listDecisions({String? status}) async {
    try {
      final query = status != null ? '?status=$status' : '';
      final response = await ApiClient.get('/workforce/decisions$query');
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.map((e) => e as Map<String, dynamic>).toList();
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] listDecisions error: $e');
    }
    return [];
  }

  /// Accept an ADR Decision
  Future<Map<String, dynamic>?> acceptDecision(int decisionId) async {
    try {
      final response = await ApiClient.post('/workforce/decisions/$decisionId/accept');
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] acceptDecision error: $e');
    }
    return null;
  }

  /// List agent budgets
  Future<List<Map<String, dynamic>>> getBudgets() async {
    try {
      final response = await ApiClient.get('/workforce/budgets');
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.map((e) => e as Map<String, dynamic>).toList();
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] getBudgets error: $e');
    }
    return [];
  }

  /// Set agent budget limit
  Future<Map<String, dynamic>?> setBudget({
    required String agentKey,
    required double limitUsd,
    String cycleType = '12_WEEK_YEAR',
  }) async {
    try {
      final response = await ApiClient.post(
        '/workforce/budgets',
        body: {
          'agent_key': agentKey,
          'limit_usd': limitUsd,
          'cycle_type': cycleType,
        },
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] setBudget error: $e');
    }
    return null;
  }

  /// Fetch Cost Ledger summary and recent entries
  Future<Map<String, dynamic>?> getCostLedger({String? billingCycle}) async {
    try {
      final query = billingCycle != null ? '?billing_cycle=$billingCycle' : '';
      final response = await ApiClient.get('/workforce/cost-ledger$query');
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] getCostLedger error: $e');
    }
    return null;
  }

  // --- Phase D: Heartbeats & Routines Automation ---

  /// List all agent heartbeats
  Future<List<Map<String, dynamic>>> listHeartbeats() async {
    try {
      final response = await ApiClient.get('/workforce/heartbeats');
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.map((e) => e as Map<String, dynamic>).toList();
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] listHeartbeats error: $e');
    }
    return [];
  }

  /// Run stalled runs watchdog recovery
  Future<Map<String, dynamic>?> checkStalledRuns({int timeoutMinutes = 10}) async {
    try {
      final response = await ApiClient.post('/workforce/heartbeats/check-stalled?timeout_minutes=$timeoutMinutes');
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] checkStalledRuns error: $e');
    }
    return null;
  }

  /// List all autonomous routines
  Future<List<Map<String, dynamic>>> listRoutines() async {
    try {
      final response = await ApiClient.get('/workforce/routines');
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.map((e) => e as Map<String, dynamic>).toList();
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] listRoutines error: $e');
    }
    return [];
  }

  /// Manually trigger a routine execution
  Future<Map<String, dynamic>?> triggerRoutine(String key) async {
    try {
      final response = await ApiClient.post('/workforce/routines/$key/trigger');
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] triggerRoutine error: $e');
    }
    return null;
  }

  // --- Custom Agent & Skills/Tools Management ---

  /// Create or update an agent definition
  Future<Map<String, dynamic>?> createOrUpdateAgent(Map<String, dynamic> data) async {
    try {
      final response = await ApiClient.post('/workforce/agents', body: data);
      if (response.statusCode == 200 || response.statusCode == 201) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
      debugPrint('[AgentPlatformService] createOrUpdateAgent failed: ${response.statusCode}');
    } catch (e) {
      debugPrint('[AgentPlatformService] createOrUpdateAgent error: $e');
    }
    return null;
  }

  /// Delete a custom agent
  Future<bool> deleteAgent(dynamic idOrKey) async {
    try {
      final response = await ApiClient.delete('/workforce/agents/$idOrKey');
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('[AgentPlatformService] deleteAgent error: $e');
      return false;
    }
  }

  /// Clone an existing agent
  Future<Map<String, dynamic>?> cloneAgent(String sourceKey, {required String newName, String? newKey}) async {
    try {
      final response = await ApiClient.post(
        '/workforce/agents/$sourceKey/clone',
        body: {'new_name': newName, 'new_key': ?newKey},
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] cloneAgent error: $e');
    }
    return null;
  }

  /// Batch update tools assigned to an agent
  Future<bool> updateAgentTools(String agentKey, List<String> toolKeys) async {
    try {
      final response = await ApiClient.post(
        '/workforce/agents/$agentKey/tools/batch-update',
        body: {'tool_keys': toolKeys},
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('[AgentPlatformService] updateAgentTools error: $e');
      return false;
    }
  }

  /// List all available tools in registry
  Future<List<Map<String, dynamic>>> listTools() async {
    try {
      final response = await ApiClient.get('/workforce/tools');
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.map((e) => e as Map<String, dynamic>).toList();
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] listTools error: $e');
    }
    return [];
  }

  /// Create a new external webhook tool
  Future<Map<String, dynamic>?> createWebhookTool(Map<String, dynamic> data) async {
    try {
      final response = await ApiClient.post('/workforce/tools/webhook', body: data);
      if (response.statusCode == 200 || response.statusCode == 201) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] createWebhookTool error: $e');
    }
    return null;
  }

  /// List physical and registered skills
  Future<List<Map<String, dynamic>>> listSkills({String? department}) async {
    try {
      final query = department != null && department != 'ALL' ? '?department=$department' : '';
      final response = await ApiClient.get('/workforce/skills/physical$query');
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.map((e) => e as Map<String, dynamic>).toList();
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] listSkills error: $e');
    }
    return [];
  }

  /// Upload markdown / SKILL.md SOP content
  Future<Map<String, dynamic>?> uploadSkillMarkdown(String content, {String? name, String? domain}) async {
    try {
      final response = await ApiClient.post(
        '/skills/upload-markdown',
        body: {
          'markdown_content': content,
          'name': ?name,
          'domain': ?domain,
          'auto_promote': true,
        },
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] uploadSkillMarkdown error: $e');
    }
    return null;
  }

  // --- Phase 6: Stage-Aware Workforce Roster ---

  /// Lấy Agent Roster được lọc và xếp hạng theo Stage Policy.
  /// Returns: { stage: {...}, roster: [...], summary: {...} }
  Future<Map<String, dynamic>?> getStageRoster(String stageCode) async {
    try {
      final response = await ApiClient.get('/workforce/stage-roster?stage=$stageCode');
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
      debugPrint('[AgentPlatformService] getStageRoster failed: ${response.statusCode}');
    } catch (e) {
      debugPrint('[AgentPlatformService] getStageRoster error: $e');
    }
    return null;
  }

  /// Kiểm tra mức độ phù hợp của một agent với stage cụ thể.
  Future<Map<String, dynamic>?> checkAgentStageFit(String agentKey, String stageCode) async {
    try {
      final response = await ApiClient.get('/workforce/agents/$agentKey/stage-fit?stage=$stageCode');
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] checkAgentStageFit error: $e');
    }
    return null;
  }

  // --- Phase 6: Exception Escalation Engine ---

  /// Danh sách Exception Escalation Records.
  /// [status]: 'OPEN' | 'RESOLVED' | 'DISMISSED' | null (all)
  Future<Map<String, dynamic>> listEscalations({
    String? status = 'OPEN',
    String? exceptionType,
    String? tier,
    int limit = 50,
  }) async {
    try {
      final params = <String, String>{
        'status': ?status,
        'exception_type': ?exceptionType,
        'tier': ?tier,
        'limit': '$limit',
      };
      final query = params.isNotEmpty
          ? '?${params.entries.map((e) => '${e.key}=${e.value}').join('&')}'
          : '';
      final response = await ApiClient.get('/workforce/exceptions$query');
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
      debugPrint('[AgentPlatformService] listEscalations failed: ${response.statusCode}');
    } catch (e) {
      debugPrint('[AgentPlatformService] listEscalations error: $e');
    }
    return {
      'total': 0,
      'founder_gate_count': 0,
      'lead_notify_count': 0,
      'has_critical': false,
      'escalations': [],
    };
  }

  /// Resolve một escalation với action cụ thể.
  /// [action]: 'retry' | 'reassign' | 'force_approve' | 'dismiss' | 'increase_budget' | 'block_permanently'
  Future<Map<String, dynamic>?> resolveEscalation(
    int escalationId, {
    required String action,
    String? comment,
  }) async {
    try {
      final response = await ApiClient.post(
        '/workforce/exceptions/$escalationId/resolve',
        body: {
          'action': action,
          'comment': ?comment,
        },
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
      debugPrint('[AgentPlatformService] resolveEscalation failed: ${response.statusCode}');
    } catch (e) {
      debugPrint('[AgentPlatformService] resolveEscalation error: $e');
    }
    return null;
  }

  /// Báo cáo STAGE_MISMATCH khi agent bị locked được kích hoạt ở stage không phù hợp.
  Future<Map<String, dynamic>?> reportStageMismatch({
    required String agentKey,
    required String agentName,
    required String stageCode,
    List<String>? deemphasizedDomains,
  }) async {
    try {
      final response = await ApiClient.post(
        '/workforce/exceptions/stage-mismatch',
        body: {
          'agent_key': agentKey,
          'agent_name': agentName,
          'stage_code': stageCode,
          'deemphasized_domains': ?deemphasizedDomains,
        },
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] reportStageMismatch error: $e');
    }
    return null;
  }

  /// Trigger manual watchdog scan cho stall + budget overflow.
  Future<Map<String, dynamic>?> runExceptionWatchdog({int stallTimeoutMinutes = 15}) async {
    try {
      final response = await ApiClient.post(
        '/workforce/exceptions/watchdog-scan?stall_timeout_minutes=$stallTimeoutMinutes',
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] runExceptionWatchdog error: $e');
    }
    return null;
  }

}







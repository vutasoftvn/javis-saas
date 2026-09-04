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
  // kiến trúc.
  //
  // Fix-review (2026-09-02) — bản đầu tiên vẫn pattern-match `ApiFailure` rồi
  // trả `null`/`[]` để giữ nguyên chữ ký cũ — CHÍNH XÁC hành vi nuốt lỗi mà
  // việc migrate sang `WorkforceMvpService` vốn để sửa. `approveRequest`/
  // `rejectRequest` là mutation Founder chạm tới thật (approve/reject qua
  // `hub_control_plane_mixin.dart`), nuốt lỗi ở đây khiến approve/reject thất
  // bại trông giống hệt thành công. 4 method dưới đây giờ trả thẳng
  // `ApiResult<T>` — caller BẮT BUỘC phải xử lý nhánh `ApiFailure` tường minh,
  // không còn suy diễn "null nghĩa là lỗi, nhưng cũng có thể là rỗng".
  final WorkforceMvpService _workforceMvpService;

  AgentPlatformService({WorkforceMvpService? workforceMvpService})
      : _workforceMvpService = workforceMvpService ?? WorkforceMvpService();

  /// Fetch master control plane dashboard summary — canonical
  /// `/agent/workforce/dashboard-summary` qua `WorkforceMvpService`.
  Future<Map<String, dynamic>?> getDashboardSummary() async {
    final result = await _workforceMvpService.getDashboardSummary();
    return result.when(
      success: (data, _) => {
        'roster_total': data.rosterTotal,
        'roster_active': data.rosterActive,
        'open_exceptions': data.openExceptions,
        'pending_approvals': data.pendingApprovals,
        'work_products_total': data.workProductsTotal,
      },
      failure: (failure) {
        debugPrint('[AgentPlatformService] getDashboardSummary failed: ${failure.message}');
        return null;
      },
    );
  }

  /// List all agents in the registry with optional department filter —
  /// canonical `/agent/workforce/roster` qua `WorkforceMvpService`.
  Future<List<Map<String, dynamic>>> listAgents({String? department}) async {
    final result = await _workforceMvpService.listRoster();
    return result.when(
      success: (data, _) {
        final filtered = department == null
            ? data
            : data.where((e) => e.department == department).toList();
        return filtered
            .map((e) => {
                  'id': e.id, 'key': e.key, 'name': e.name, 'role_title': e.roleTitle,
                  'department': e.department, 'agent_type': e.agentType,
                  'default_model_profile': e.defaultModelProfile, 'risk_level': e.riskLevel,
                  'status': e.status, 'enabled': e.enabled,
                })
            .toList();
      },
      failure: (failure) {
        // Follow-up (2026-09-04) — trước đây fallback về `default12Agents`
        // (12 agent hư cấu hard-code), mâu thuẫn với chính lý do Phase 1
        // tồn tại (thay dữ liệu giả bằng registry thật — rule 7: không dữ
        // liệu giả). Trả rỗng để UI hiển thị trạng thái lỗi/rỗng tường
        // minh, không nguỵ trang lỗi mạng thành "vẫn có 12 agent".
        debugPrint('[AgentPlatformService] listAgents error: ${failure.message}');
        return const [];
      },
    );
  }

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
  /// Trả thẳng `ApiResult` của `WorkforceMvpService` — không có gì để biến
  /// đổi ngoài shape dữ liệu, nên không có lý do nuốt `ApiFailure`.
  Future<ApiResult<Map<String, dynamic>>> getOrgChart() => _workforceMvpService.getOrgChart();

  /// List pending approvals for human review — canonical
  /// `/agent/workforce/approvals` (KHÔNG PHẢI `/agent/approvals`, stub
  /// `deprecated=True` chưa từng được mount trong `apps/cosa/api/app.py`).
  Future<ApiResult<List<Map<String, dynamic>>>> listApprovals({String status = 'PENDING'}) async {
    final result = await _workforceMvpService.listApprovals(status: status);
    return switch (result) {
      ApiSuccess(data: final approvals, meta: final meta) =>
        ApiSuccess(data: approvals.map(_approvalToMap).toList(), meta: meta),
      ApiFailure(failure: final f) => ApiFailure(f),
    };
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
  Future<ApiResult<Map<String, dynamic>>> approveRequest(int approvalId, {String? comment}) async {
    final result = await _workforceMvpService.decideApproval(
      '$approvalId',
      approved: true,
      reason: comment ?? 'Approved by Founder via Control Plane UI',
    );
    return switch (result) {
      ApiSuccess(data: final decision, meta: final meta) =>
        ApiSuccess(data: _decisionToMap(decision), meta: meta),
      ApiFailure(failure: final f) => ApiFailure(f),
    };
  }

  /// Reject a pending request — canonical decision endpoint
  /// `/agent/workforce/approvals/{id}/decision` (`approved: false`).
  Future<ApiResult<Map<String, dynamic>>> rejectRequest(int approvalId, {String? comment}) async {
    final result = await _workforceMvpService.decideApproval(
      '$approvalId',
      approved: false,
      reason: comment ?? 'Rejected by Founder via Control Plane UI',
    );
    return switch (result) {
      ApiSuccess(data: final decision, meta: final meta) =>
        ApiSuccess(data: _decisionToMap(decision), meta: meta),
      ApiFailure(failure: final f) => ApiFailure(f),
    };
  }

  Map<String, dynamic> _decisionToMap(WorkforceApprovalDecision d) => {
        'approval_id': d.approvalId,
        'run_id': d.runId,
        'status': d.status,
        'reviewer': d.reviewer,
        'reason': d.reason,
        'decided_at': d.decidedAt.toIso8601String(),
      };

  /// List work products — canonical `/agent/workforce/artifacts` qua
  /// `WorkforceMvpService`. Backend chưa có filter `status` cho route này
  /// (pre-flight decision, 2026-09-04) nên tham số cũ bị bỏ — không call site
  /// nào trong app truyền `status:` vào method này (đã grep xác nhận).
  Future<List<Map<String, dynamic>>> listWorkProducts() async {
    final result = await _workforceMvpService.listWorkProducts();
    return result.when(
      success: (data, _) => data
          .map((p) => {
                'id': p.id, 'title': p.title, 'product_type': p.productType,
                'status': p.status, 'author_agent_key': p.authorAgentKey,
                'object_ref': p.objectRef,
              })
          .toList(),
      failure: (failure) {
        debugPrint('[AgentPlatformService] Error loading work products: ${failure.message}');
        return [];
      },
    );
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
    final result = await _workforceMvpService.getStageRoster(stageCode);
    return result.when(
      success: (data, _) => {
        'stage': {'stage_code': data.stage.stageCode, 'task_count': data.stage.taskCount},
        'roster': data.roster
            .map((t) => {
                  'task_id': t.taskId, 'title': t.title, 'priority': t.priority,
                  'status': t.status, 'project_id': t.projectId,
                })
            .toList(),
        'summary': {
          'total': data.summary.total, 'high_priority': data.summary.highPriority,
          'medium': data.summary.medium, 'locked': data.summary.locked,
        },
      },
      failure: (failure) {
        debugPrint('[AgentPlatformService] Error loading stage roster: ${failure.message}');
        return null;
      },
    );
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
  // `status`/`exceptionType`/`tier`/`limit` kept on this method's own
  // signature (call sites in hub_control_plane_mixin.dart pass `status:
  // 'OPEN'` và must keep compiling) but NOT forwarded to
  // `_workforceMvpService.listExceptions()` anymore — the backend route has
  // no filter to honor yet (pre-flight decision, 2026-09-04; see spec Phase
  // 5 / Global Constraints). Every returned item is always effectively
  // "OPEN" today.
  Future<Map<String, dynamic>> listEscalations({
    String? status = 'OPEN',
    String? exceptionType,
    String? tier,
    int limit = 50,
  }) async {
    final result = await _workforceMvpService.listExceptions();
    return result.when(
      success: (data, _) => {
        'total': data.total,
        'founder_gate_count': data.founderGateCount,
        'lead_notify_count': data.leadNotifyCount,
        'has_critical': data.hasCritical,
        'escalations': data.escalations
            .map((e) => {
                  'id': e.id, 'exception_type': e.exceptionType, 'tier': e.tier,
                  'status': e.status, 'agent_key': e.agentKey,
                })
            .toList(),
      },
      failure: (failure) {
        debugPrint('[AgentPlatformService] listEscalations failed: ${failure.message}');
        return {
          'total': 0, 'founder_gate_count': 0, 'lead_notify_count': 0,
          'has_critical': false, 'escalations': [],
        };
      },
    );
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







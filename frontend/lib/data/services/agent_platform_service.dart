import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../core/network/api_client.dart';

class AgentPlatformService {
  /// Fetch master control plane dashboard summary
  Future<Map<String, dynamic>?> getDashboardSummary() async {
    try {
      final response = await ApiClient.get('/agent-platform/dashboard-summary');
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
      final response = await ApiClient.get('/agent-platform/agents$query');
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.map((e) => e as Map<String, dynamic>).toList();
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] listAgents error: $e');
    }
    return [];
  }

  // Compatibility aliases
  Future<List<Map<String, dynamic>>> getAgents({String? department}) => listAgents(department: department);
  Future<List<Map<String, dynamic>>> getTools() async {
    try {
      final response = await ApiClient.get('/agent-platform/tools');
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
      final response = await ApiClient.post('/agent-platform/routing/test', body: {'message': message});
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] testRouting error: $e');
    }
    return null;
  }

  /// Get organization hierarchy
  Future<Map<String, dynamic>?> getOrgChart() async {
    try {
      final response = await ApiClient.get('/agent-platform/org-chart');
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] getOrgChart error: $e');
    }
    return null;
  }

  /// List pending approvals for human review
  Future<List<Map<String, dynamic>>> listApprovals({String status = 'PENDING'}) async {
    try {
      final response = await ApiClient.get('/agent-platform/approvals?status=$status');
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.map((e) => e as Map<String, dynamic>).toList();
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] listApprovals error: $e');
    }
    return [];
  }

  /// Approve a pending request
  Future<Map<String, dynamic>?> approveRequest(int approvalId, {String? comment}) async {
    try {
      final response = await ApiClient.post(
        '/agent-platform/approvals/$approvalId/approve',
        body: {'comment': comment ?? 'Approved by Founder via Control Plane UI'},
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] approveRequest error: $e');
    }
    return null;
  }

  /// Reject a pending request
  Future<Map<String, dynamic>?> rejectRequest(int approvalId, {String? comment}) async {
    try {
      final response = await ApiClient.post(
        '/agent-platform/approvals/$approvalId/reject',
        body: {'comment': comment ?? 'Rejected by Founder via Control Plane UI'},
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] rejectRequest error: $e');
    }
    return null;
  }

  /// List work products
  Future<List<Map<String, dynamic>>> listWorkProducts({String? status}) async {
    try {
      final query = status != null ? '?status=$status' : '';
      final response = await ApiClient.get('/agent-platform/work-products$query');
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
        '/agent-platform/work-products/$workProductId/accept',
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
        '/agent-platform/work-products/$workProductId/revise',
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
      final response = await ApiClient.get('/agent-platform/decisions$query');
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
      final response = await ApiClient.post('/agent-platform/decisions/$decisionId/accept');
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
      final response = await ApiClient.get('/agent-platform/budgets');
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
        '/agent-platform/budgets',
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
      final response = await ApiClient.get('/agent-platform/cost-ledger$query');
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
      final response = await ApiClient.get('/agent-platform/heartbeats');
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
      final response = await ApiClient.post('/agent-platform/heartbeats/check-stalled?timeout_minutes=$timeoutMinutes');
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
      final response = await ApiClient.get('/agent-platform/routines');
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
      final response = await ApiClient.post('/agent-platform/routines/$key/trigger');
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[AgentPlatformService] triggerRoutine error: $e');
    }
    return null;
  }
}



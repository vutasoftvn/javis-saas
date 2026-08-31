import '../../../core/network/api_client.dart';
import '../models/strategy_list_result.dart';
import 'strategy_service_base.dart';

/// Founder Profile, CEO Next Best Actions, Model Runs & Profiles
class FounderService extends StrategyServiceBase {
  // ====================================================================
  // Founder Profile
  // ====================================================================

  Future<Map<String, dynamic>> getFounderProfile() async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.get('/strategy/founder-profile?workspace_id=$workspaceId');
    return decode(response);
  }

  Future<Map<String, dynamic>> updateFounderProfile({
    double? weeklyCapacityHours,
    int? maxActiveStrategicProjects,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.put(
      '/strategy/founder-profile?workspace_id=$workspaceId',
      body: {
        'weekly_capacity_hours': ?weeklyCapacityHours,
        'max_active_strategic_projects': ?maxActiveStrategicProjects,
      },
    );
    return decode(response);
  }

  // ====================================================================
  // mCOSA V12 Next Best Action Engine (Sprint 9 Spec §37 & V12.6)
  // ====================================================================

  Future<StrategyListResult<Map<String, dynamic>>> getCeoNextActions({int limit = 5}) async {
    final workspaceId = await requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/strategy/ceo/next-actions?workspace_id=$workspaceId&limit=$limit',
      );
      return decodeList(response, 'next_actions');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<StrategyListResult<Map<String, dynamic>>> evaluateCeoNextActions({
    String? projectId,
    String? portfolioId,
  }) async {
    final workspaceId = await requireWorkspaceId();
    try {
      final response = await ApiClient.post(
        '/strategy/ceo/next-actions/evaluate?workspace_id=$workspaceId',
        body: {
          'project_id': ?projectId,
          'portfolio_id': ?portfolioId,
        },
      );
      return decodeList(response, 'rankings');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> updateNextActionStatus(
    String actionId,
    String status,
  ) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.put(
      '/strategy/ceo/next-actions/$actionId/status?workspace_id=$workspaceId',
      body: {'status': status},
    );
    return decode(response);
  }

  Future<StrategyListResult<Map<String, dynamic>>> getModelRunsAudit({int limit = 20}) async {
    final workspaceId = await requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/strategy/model-runs/audit?workspace_id=$workspaceId&limit=$limit',
      );
      return decodeList(response, 'audits');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<StrategyListResult<Map<String, dynamic>>> getModelProfiles() async {
    final workspaceId = await requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/strategy/model-profiles?workspace_id=$workspaceId',
      );
      return decodeList(response, 'profiles');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> updateModelProfile(
    String profileId, {
    String? displayName,
    double? temperature,
    bool? isActive,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.put(
      '/strategy/model-profiles/$profileId?workspace_id=$workspaceId',
      body: {
        'display_name': ?displayName,
        'temperature': ?temperature,
        'is_active': ?isActive,
      },
    );
    return decode(response);
  }
}

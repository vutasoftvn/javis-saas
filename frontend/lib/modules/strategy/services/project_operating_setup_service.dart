import '../../../core/network/api_client.dart';
import '../../../data/models/project_operating_setup_model.dart';
import 'strategy_service_base.dart';

class ProjectOperatingSetupService extends StrategyServiceBase {
  Future<ProjectOperatingSetup> get(String projectId) async {
    final response = await ApiClient.get(
      '/operations/projects/$projectId/operating-setup',
    );
    final data = decode(response);
    if (data is Map<String, dynamic>) {
      if (data.containsKey('setup') && data['setup'] is Map<String, dynamic>) {
        return ProjectOperatingSetup.fromJson(
          data['setup'] as Map<String, dynamic>,
        );
      }
      return ProjectOperatingSetup.fromJson(data);
    }
    throw StrategyApiException(
      response.statusCode,
      'Invalid operating setup response format',
    );
  }

  /// Founder Trial R1 — chỉnh riêng độ dài Operating Cycle (1–12 tuần) mà không
  /// đụng các field khác của setup. Backend giữ nguyên field bị bỏ qua.
  Future<ProjectOperatingSetup> updateCycleDuration(
    String projectId,
    int cycleDurationWeeks,
  ) async {
    final response = await ApiClient.put(
      '/operations/projects/$projectId/operating-setup',
      body: {'cycleDurationWeeks': cycleDurationWeeks},
    );
    final data = decode(response);
    if (data is Map<String, dynamic>) {
      if (data.containsKey('setup') && data['setup'] is Map<String, dynamic>) {
        return ProjectOperatingSetup.fromJson(data['setup'] as Map<String, dynamic>);
      }
      return ProjectOperatingSetup.fromJson(data);
    }
    throw StrategyApiException(
      response.statusCode,
      'Invalid operating setup response format',
    );
  }

  Future<ProjectOperatingSetup> saveDraft(
    String projectId,
    ProjectOperatingSetupDraft draft,
  ) async {
    final response = await ApiClient.put(
      '/operations/projects/$projectId/operating-setup',
      body: draft.toJson(),
    );
    final data = decode(response);
    if (data is Map<String, dynamic>) {
      if (data.containsKey('setup') && data['setup'] is Map<String, dynamic>) {
        return ProjectOperatingSetup.fromJson(
          data['setup'] as Map<String, dynamic>,
        );
      }
      return ProjectOperatingSetup.fromJson(data);
    }
    throw StrategyApiException(
      response.statusCode,
      'Invalid operating setup response format',
    );
  }

  Future<ProjectOperatingSetup> activate(
    String projectId,
    ProjectOperatingSetupDraft draft,
  ) async {
    final response = await ApiClient.post(
      '/operations/projects/$projectId/operating-setup/activate',
      body: draft.toJson(),
    );
    final data = decode(response);
    if (data is Map<String, dynamic>) {
      if (data.containsKey('setup') && data['setup'] is Map<String, dynamic>) {
        return ProjectOperatingSetup.fromJson(
          data['setup'] as Map<String, dynamic>,
        );
      }
      return ProjectOperatingSetup.fromJson(data);
    }
    throw StrategyApiException(
      response.statusCode,
      'Invalid operating setup response format',
    );
  }

  Future<void> requestKickoffSuggestion(
    String projectId, {
    String? locale,
  }) async {
    final response = await ApiClient.post(
      '/operations/projects/$projectId/kickoff-suggestion',
      body: {
        if (locale != null && locale.isNotEmpty) 'locale': locale,
      },
    );
    decode(response); // throws StrategyApiException nếu không phải 2xx
  }
}

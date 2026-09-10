import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_endpoints.g.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import '../models/project_operating_loop.dart';

class ProjectOperatingLoopService {
  final MvpRequestClient _client;

  ProjectOperatingLoopService({MvpRequestClient? client})
      : _client = client ?? MvpRequestClient();

  Future<ApiResult<ProjectOperatingLoop>> get(String projectId) async {
    return _client.request<ProjectOperatingLoop>(
      MvpEndpoint.projectLoopRead,
      pathParams: {'projectId': projectId},
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          final data = raw['data'] is Map<String, dynamic>
              ? raw['data'] as Map<String, dynamic>
              : raw;
          return ProjectOperatingLoop.fromJson(data);
        }
        throw FormatException('Invalid response format for project operating loop');
      },
    );
  }

  Future<ApiResult<Map<String, dynamic>>> createObjective(
    String projectId, {
    required String title,
    String? description,
  }) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.projectOkrWrite,
      pathParams: {'projectId': projectId},
      body: {
        'title': title,
        'description': ?description,
      },
      decode: (raw) => raw is Map<String, dynamic> ? raw : {},
    );
  }

  Future<ApiResult<Map<String, dynamic>>> createCycle(
    String projectId, {
    required int durationWeeks,
    required String startDate,
  }) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.projectCycleWrite,
      pathParams: {'projectId': projectId},
      body: {
        'durationWeeks': durationWeeks,
        'startDate': startDate,
      },
      decode: (raw) => raw is Map<String, dynamic> ? raw : {},
    );
  }

  Future<ApiResult<Map<String, dynamic>>> createWeek(
    String projectId, {
    required String cycleId,
    required int weekNo,
    String? focus,
  }) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.projectWeekWrite,
      pathParams: {'projectId': projectId},
      body: {
        'cycleId': cycleId,
        'weekNo': weekNo,
        'focus': ?focus,
      },
      decode: (raw) => raw is Map<String, dynamic> ? raw : {},
    );
  }

  Future<ApiResult<Map<String, dynamic>>> createCommitment(
    String projectId, {
    required String weeklyPlanId,
    required String title,
    double? targetConfidence,
  }) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.projectCommitmentWrite,
      pathParams: {'projectId': projectId},
      body: {
        'weeklyPlanId': weeklyPlanId,
        'title': title,
        'targetConfidence': ?targetConfidence,
      },
      decode: (raw) => raw is Map<String, dynamic> ? raw : {},
    );
  }

  Future<ApiResult<Map<String, dynamic>>> createTask(
    String projectId, {
    required String title,
    required String weeklyCommitmentId,
    String? priority,
  }) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.projectTaskWrite,
      pathParams: {'projectId': projectId},
      body: {
        'title': title,
        'weeklyCommitmentId': weeklyCommitmentId,
        'priority': ?priority,
      },
      decode: (raw) => raw is Map<String, dynamic> ? raw : {},
    );
  }
}

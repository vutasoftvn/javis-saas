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

  // Task 4 (2026-09-14 remediation) — body key `why` khớp đúng
  // `CreateObjectiveBody` thật ở `project-operating-loop.handler.ts` (trước
  // đây gửi nhầm `description`, backend không đọc field này).
  Future<ApiResult<Map<String, dynamic>>> createObjective(
    String projectId, {
    required String title,
    String? why,
    String? ownerMemberId,
  }) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.projectOkrWrite,
      pathParams: {'projectId': projectId},
      body: {
        'title': title,
        'why': ?why,
        'ownerMemberId': ?ownerMemberId,
      },
      decode: (raw) => raw is Map<String, dynamic> ? raw : {},
    );
  }

  // `CreateKeyResultBody` — endpoint mới Task 3 (`project.key_result.write`).
  Future<ApiResult<Map<String, dynamic>>> createKeyResult(
    String projectId, {
    required String objectiveId,
    required String title,
    String? metricId,
    double? targetValue,
    String? unit,
  }) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.projectKeyResultWrite,
      pathParams: {'projectId': projectId},
      body: {
        'objectiveId': objectiveId,
        'title': title,
        'metricId': ?metricId,
        'targetValue': ?targetValue,
        'unit': ?unit,
      },
      decode: (raw) => raw is Map<String, dynamic> ? raw : {},
    );
  }

  // `CreateInitiativeBody` — endpoint mới Task 3 (`project.initiative.write`).
  Future<ApiResult<Map<String, dynamic>>> createInitiative(
    String projectId, {
    required String keyResultId,
    required String title,
    String? description,
    String? intendedOutcome,
    String? ownerMemberId,
  }) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.projectInitiativeWrite,
      pathParams: {'projectId': projectId},
      body: {
        'keyResultId': keyResultId,
        'title': title,
        'description': ?description,
        'intendedOutcome': ?intendedOutcome,
        'ownerMemberId': ?ownerMemberId,
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

  // Task 4 — body key `plannedEffort` khớp đúng `CreateWeeklyCommitmentBody`
  // thật (trước đây gửi nhầm `targetConfidence`, không tồn tại ở backend).
  Future<ApiResult<Map<String, dynamic>>> createCommitment(
    String projectId, {
    required String weeklyPlanId,
    required String title,
    String? plannedEffort,
  }) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.projectCommitmentWrite,
      pathParams: {'projectId': projectId},
      body: {
        'weeklyPlanId': weeklyPlanId,
        'title': title,
        'plannedEffort': ?plannedEffort,
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

  // `AdvanceTaskParams` — endpoint mới Task 3 (`project.task.status.write`),
  // `taskId` là path param, `status` là body.
  Future<ApiResult<Map<String, dynamic>>> updateTaskStatus(
    String projectId, {
    required String taskId,
    required String status,
  }) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.projectTaskStatusWrite,
      pathParams: {'projectId': projectId, 'taskId': taskId},
      body: {'status': status},
      decode: (raw) => raw is Map<String, dynamic> ? raw : {},
    );
  }
}

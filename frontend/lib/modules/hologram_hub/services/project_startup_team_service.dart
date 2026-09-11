import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_endpoints.g.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import '../models/project_startup_team.dart';

class ProjectStartupTeamService {
  final MvpRequestClient _client;

  ProjectStartupTeamService({MvpRequestClient? client})
      : _client = client ?? MvpRequestClient();

  /// Lấy danh sách 9 thành viên startup team cho project.
  Future<ApiResult<List<ProjectStartupTeamMember>>> fetchTeam(String projectId) async {
    return _client.request<List<ProjectStartupTeamMember>>(
      MvpEndpoint.projectStartupTeamRead,
      pathParams: {'projectId': projectId},
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          final items = raw['items'] as List<dynamic>? ?? [];
          return items
              .map((e) => ProjectStartupTeamMember.fromJson(e as Map<String, dynamic>))
              .toList();
        }
        throw const FormatException('Invalid response format for startup team');
      },
    );
  }

  /// Kích hoạt một thành viên agent template (Founder/Admin).
  Future<ApiResult<ProjectStartupTeamMember>> activate({
    required String projectId,
    required String profileKey,
    required int expectedVersion,
    String? idempotencyKey,
  }) async {
    return _client.request<ProjectStartupTeamMember>(
      MvpEndpoint.projectStartupTeamActivate,
      pathParams: {
        'projectId': projectId,
        'profileKey': profileKey,
      },
      body: {
        'expectedVersion': expectedVersion,
        'idempotencyKey': ?idempotencyKey,
      },
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          return ProjectStartupTeamMember.fromJson(raw);
        }
        throw const FormatException('Invalid response format for activate agent');
      },
    );
  }

  /// Tạm dừng một thành viên agent (Founder/Admin).
  Future<ApiResult<ProjectStartupTeamMember>> pause({
    required String projectId,
    required String profileKey,
    required int expectedVersion,
    String? reason,
    String? idempotencyKey,
  }) async {
    return _client.request<ProjectStartupTeamMember>(
      MvpEndpoint.projectStartupTeamPause,
      pathParams: {
        'projectId': projectId,
        'profileKey': profileKey,
      },
      body: {
        'expectedVersion': expectedVersion,
        'reason': ?reason,
        'idempotencyKey': ?idempotencyKey,
      },
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          return ProjectStartupTeamMember.fromJson(raw);
        }
        throw const FormatException('Invalid response format for pause agent');
      },
    );
  }

  /// Alias for fetchTeam
  Future<ApiResult<List<ProjectStartupTeamMember>>> listTeam(String projectId) =>
      fetchTeam(projectId);

  /// Alias for activate
  Future<ApiResult<ProjectStartupTeamMember>> activateMember({
    required String projectId,
    required String profileKey,
    required int expectedVersion,
    String? idempotencyKey,
  }) =>
      activate(
        projectId: projectId,
        profileKey: profileKey,
        expectedVersion: expectedVersion,
        idempotencyKey: idempotencyKey,
      );

  /// Alias for pause
  Future<ApiResult<ProjectStartupTeamMember>> pauseMember({
    required String projectId,
    required String profileKey,
    required int expectedVersion,
    String? reason,
    String? idempotencyKey,
  }) =>
      pause(
        projectId: projectId,
        profileKey: profileKey,
        expectedVersion: expectedVersion,
        reason: reason,
        idempotencyKey: idempotencyKey,
      );
}

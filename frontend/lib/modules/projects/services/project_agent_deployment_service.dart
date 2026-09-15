import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_endpoints.g.dart';
import 'package:frontend/core/network/mvp_request_client.dart';

/// Project Agent Deployment — kết quả deploy Workspace Agent vào Project.
/// Project KHÔNG sở hữu Role; chỉ deploy Workspace Agent hiện hữu với scope
/// hẹp (data/budget/policy). Server resolve pin (spec/version/hash) — client
/// không gửi roleKey, spec hash hay Skill definition tự chọn.
class ProjectAgentDeployment {
  final String id;
  final String workspaceId;
  final String projectId;
  final String workspaceAgentId;
  final String? projectRoleDeploymentId;
  final String state;
  final List<dynamic> capabilityOverrides;
  final int version;

  const ProjectAgentDeployment({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    required this.workspaceAgentId,
    this.projectRoleDeploymentId,
    required this.state,
    required this.capabilityOverrides,
    required this.version,
  });

  factory ProjectAgentDeployment.fromJson(Map<String, dynamic> json) {
    String requiredId(String key) {
      final value = json[key];
      if (value is! String || value.isEmpty) {
        throw FormatException('Missing $key in project agent deployment');
      }
      return value;
    }

    final state = json['state'];
    const validStates = {'ACTIVE', 'INACTIVE', 'PAUSED', 'RETIRED'};
    if (state is! String || !validStates.contains(state)) {
      throw FormatException('Invalid state in project agent deployment');
    }
    final version = json['version'];
    if (version is! num || version.toInt() < 1) {
      throw FormatException('Invalid version in project agent deployment');
    }

    return ProjectAgentDeployment(
      id: requiredId('id'),
      workspaceId: requiredId('workspaceId'),
      projectId: requiredId('projectId'),
      workspaceAgentId: requiredId('workspaceAgentId'),
      projectRoleDeploymentId: json['projectRoleDeploymentId'] as String?,
      state: state,
      capabilityOverrides:
          (json['capabilityOverrides'] as List<dynamic>?) ?? const [],
      version: version.toInt(),
    );
  }
}

/// Lệnh Project DUY NHẤT cho Executive Board: deploy Workspace Agent hiện hữu
/// vào Project (2026-09-14). Không có Project Role bind/unbind — Role thuộc
/// Workspace, Project chỉ deploy Agent.
class ProjectAgentDeploymentService {
  final MvpRequestClient _client;

  ProjectAgentDeploymentService({MvpRequestClient? client})
      : _client = client ?? MvpRequestClient();

  Future<ApiResult<ProjectAgentDeployment>> deploy(
    String projectId, {
    required String workspaceAgentId,
    String? idempotencyKey,
  }) async {
    return _client.request<ProjectAgentDeployment>(
      MvpEndpoint.projectAgentDeploymentsCreate,
      pathParams: {'projectId': projectId},
      body: {
        'workspaceAgentId': workspaceAgentId,
        'idempotencyKey': ?idempotencyKey,
      },
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          return ProjectAgentDeployment.fromJson(raw);
        }
        throw const FormatException('Invalid response format for agent deployment');
      },
    );
  }
}

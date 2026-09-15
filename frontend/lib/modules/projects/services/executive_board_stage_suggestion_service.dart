import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_endpoints.g.dart';
import 'package:frontend/core/network/mvp_request_client.dart';

/// Kết quả gợi ý Executive Board theo lifecycle stage của Project (2026-09-14).
/// CHỈ gợi ý — hai hành động Founder là 2 endpoint khác nhau:
///   - bật/tắt office → Workspace (`activateRole` ở ExecutiveAdvisoryBoardService);
///   - deploy Workspace Agent → Project (`ProjectAgentDeploymentService.deploy`).
/// Không bao giờ tự kích hoạt office hay tự deploy agent ở đây.
class ExecutiveBoardStageSuggestion {
  final String stage;
  final List<String> workspaceOfficeToEnable;
  final List<String> projectAgentsToDeploy;
  final List<String> stageEligibleRoles;

  const ExecutiveBoardStageSuggestion({
    required this.stage,
    required this.workspaceOfficeToEnable,
    required this.projectAgentsToDeploy,
    required this.stageEligibleRoles,
  });

  factory ExecutiveBoardStageSuggestion.fromJson(Map<String, dynamic> json) {
    final stage = json['stage'];
    if (stage is! String || stage.isEmpty) {
      throw const FormatException('Missing stage in executive board suggestion');
    }

    List<String> readList(String key) {
      final raw = json[key];
      if (raw is! List) {
        throw FormatException('Missing $key in executive board suggestion');
      }
      if (raw.any((value) => value is! String || value.isEmpty)) {
        throw FormatException('Invalid $key in executive board suggestion');
      }
      return raw.cast<String>();
    }

    return ExecutiveBoardStageSuggestion(
      stage: stage,
      workspaceOfficeToEnable: readList('workspaceOfficeToEnable'),
      projectAgentsToDeploy: readList('projectAgentsToDeploy'),
      stageEligibleRoles: readList('stageEligibleRoles'),
    );
  }
}

/// Gợi ý kích hoạt Executive Board theo lifecycle stage của Project.
/// Dùng contract-generated endpoint (không gọi `ApiClient` thô).
class ExecutiveBoardStageSuggestionService {
  final MvpRequestClient _client;

  ExecutiveBoardStageSuggestionService({MvpRequestClient? client})
      : _client = client ?? MvpRequestClient();

  Future<ApiResult<ExecutiveBoardStageSuggestion>> getSuggestion(
    String projectId,
  ) async {
    return _client.request<ExecutiveBoardStageSuggestion>(
      MvpEndpoint.operationsExecutiveBoardStageSuggestion,
      pathParams: {'projectId': projectId},
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          return ExecutiveBoardStageSuggestion.fromJson(raw);
        }
        throw const FormatException('Invalid response format for stage suggestion');
      },
    );
  }
}

import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_endpoints.g.dart';
import 'package:frontend/core/network/mvp_request_client.dart';

/// Fact dự án founder đã xác nhận (review 2026-09-27, G-8). Agent chỉ đề xuất
/// (thẻ `memory_confirm` trong chat); chỉ founder bấm "Lưu" mới ghi.
class ProjectFact {
  final String id;
  final String content;

  const ProjectFact({required this.id, required this.content});

  factory ProjectFact.fromJson(Map<String, dynamic> j) =>
      ProjectFact(id: '${j['id']}', content: '${j['content'] ?? ''}');
}

class ProjectMemoryService {
  final MvpRequestClient _client;

  ProjectMemoryService({MvpRequestClient? client}) : _client = client ?? MvpRequestClient();

  Future<ApiResult<List<ProjectFact>>> list(String projectId) {
    return _client.request<List<ProjectFact>>(
      MvpEndpoint.agentProjectMemoryList,
      pathParams: {'projectId': projectId},
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          return ((raw['facts'] as List<dynamic>?) ?? const [])
              .map((e) => ProjectFact.fromJson(e as Map<String, dynamic>))
              .toList();
        }
        throw const FormatException('Invalid response format for project facts');
      },
    );
  }

  Future<ApiResult<ProjectFact>> create(
    String projectId,
    String content, {
    String? sourceMessageId,
  }) {
    return _client.request<ProjectFact>(
      MvpEndpoint.agentProjectMemoryCreate,
      pathParams: {'projectId': projectId},
      body: {'content': content, 'source_message_id': ?sourceMessageId},
      decode: (raw) {
        if (raw is Map<String, dynamic>) return ProjectFact.fromJson(raw);
        throw const FormatException('Invalid response format for project fact');
      },
    );
  }

  Future<ApiResult<bool>> retract(String projectId, String factId) {
    return _client.request<bool>(
      MvpEndpoint.agentProjectMemoryRetract,
      pathParams: {'projectId': projectId, 'factId': factId},
      decode: (raw) => raw is Map<String, dynamic> && raw['status'] == 'RETRACTED',
    );
  }
}

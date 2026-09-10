import 'package:http/http.dart' as http;
import '../../../core/network/api_result.dart';
import '../../../core/network/mvp_endpoints.g.dart';
import '../../../core/network/mvp_request_client.dart';
import '../models/project_knowledge.dart';

class ProjectKnowledgeService {
  final MvpRequestClient _client;

  ProjectKnowledgeService({MvpRequestClient? client, http.Client? httpClient})
      : _client = client ?? MvpRequestClient(httpClient: httpClient);

  Future<ApiResult<ProjectKnowledgeSearchResult>> search(
    String projectId, {
    required String query,
    int limit = 5,
  }) async {
    return _client.request<ProjectKnowledgeSearchResult>(
      MvpEndpoint.agentKnowledgeProjectSearch,
      pathParams: {'projectId': projectId},
      body: {
        'query': query,
        'limit': limit,
      },
      decode: (json) {
        final map = json is Map<String, dynamic> ? json : <String, dynamic>{};
        return ProjectKnowledgeSearchResult.fromJson(map);
      },
    );
  }
}

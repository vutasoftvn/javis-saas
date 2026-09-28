import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_endpoints.g.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import '../models/ai_initiative_portfolio.dart';

class AiInitiativePortfolioService {
  final MvpRequestClient _client;

  AiInitiativePortfolioService({MvpRequestClient? client})
      : _client = client ?? MvpRequestClient();

  Future<ApiResult<AiInitiativePortfolioResponse>> getPortfolio(String projectId) async {
    return _client.request<AiInitiativePortfolioResponse>(
      MvpEndpoint.aiInitiativePortfolioRead,
      pathParams: {'projectId': projectId},
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          final data = raw['data'] is Map<String, dynamic>
              ? raw['data'] as Map<String, dynamic>
              : raw;
          return AiInitiativePortfolioResponse.fromJson(data);
        }
        throw const FormatException('Invalid response format for AI initiative portfolio');
      },
    );
  }
}

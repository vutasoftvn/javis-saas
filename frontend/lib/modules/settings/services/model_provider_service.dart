import 'package:http/http.dart' as http;

import '../../../core/network/api_result.dart';
import '../../../core/network/mvp_endpoints.g.dart';
import '../../../core/network/mvp_request_client.dart';
import '../models/settings_models.dart';

/// Task 4 (plan 2026-09-07-local-first-model-routing) — client cho founder-
/// only model provider/policy settings (`/agent/settings/model-*`). Cùng
/// convention `SettingsMvpService` (dùng `MvpRequestClient` + generated
/// `MvpEndpoint`), khác domain (Agent Platform's own Postgres, `source_kind:
/// "agent_db"` — không phải COSA Control Plane).
///
/// KHÔNG BAO GIỜ truyền/nhận `apiKey` dưới dạng plaintext ra khỏi hàm
/// [createProvider] — tham số nhận vào rồi đưa thẳng vào body JSON của 1
/// request HTTPS duy nhất, không log, không giữ lại biến instance nào chứa
/// giá trị đó.
class ModelProviderService {
  final MvpRequestClient _client;

  ModelProviderService({MvpRequestClient? client, http.Client? httpClient})
      : _client = client ?? MvpRequestClient(httpClient: httpClient);

  Future<ApiResult<List<ModelProviderModel>>> listProviders() async {
    return _client.request<List<ModelProviderModel>>(
      MvpEndpoint.settingsModelProviderList,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => ModelProviderModel.fromJson(e))
            .toList();
      },
    );
  }

  /// Tạo (hoặc upsert) 1 provider profile. `apiKey` là optional (CLI/local
  /// endpoint không cần) — khi có, đi thẳng vào body của request này, KHÔNG
  /// bao giờ được server trả lại (xem `ModelProviderModel` — không có field
  /// đó).
  Future<ApiResult<ModelProviderModel>> createProvider({
    required String providerType,
    String? profileId,
    String? modelId,
    String? apiKey,
    String? baseUrl,
    List<String>? allowedModels,
    double? budgetUsdLimit,
    int? maxConcurrency,
  }) async {
    return _client.request<ModelProviderModel>(
      MvpEndpoint.settingsModelProviderCreate,
      body: {
        'provider_type': providerType,
        'profile_id': ?profileId,
        'model_id': ?modelId,
        'api_key': ?apiKey,
        'base_url': ?baseUrl,
        'allowed_models': ?allowedModels,
        'budget_usd_limit': ?budgetUsdLimit,
        'max_concurrency': ?maxConcurrency,
      },
      decode: (json) => ModelProviderModel.fromJson(json as Map<String, dynamic>),
    );
  }

  /// Health-check server-side cho 1 profile đã tạo. Caller (UI) KHÔNG được tự
  /// suy luận "usable" từ `credentialConfigured` — chỉ tin `ok` trả về từ
  /// chính call này, và chỉ SAU KHI call này thành công.
  Future<ApiResult<ModelProviderTestResultModel>> testConnection(String profileId) async {
    return _client.request<ModelProviderTestResultModel>(
      MvpEndpoint.settingsModelProviderTest,
      pathParams: {'profileId': profileId},
      decode: (json) => ModelProviderTestResultModel.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<ModelPolicyModel>> getPolicy(String agentProfile) async {
    return _client.request<ModelPolicyModel>(
      MvpEndpoint.settingsModelPolicyGet,
      pathParams: {'agentProfile': agentProfile},
      decode: (json) => ModelPolicyModel.fromJson(json as Map<String, dynamic>),
    );
  }

  /// `agentProfile` dùng sentinel `_workspace_default`
  /// (xem `apps/cosa/api/model_policy_routes.py::WORKSPACE_DEFAULT_SENTINEL`)
  /// để set default TOÀN WORKSPACE thay vì override 1 agent cụ thể.
  Future<ApiResult<ModelPolicyModel>> setPolicy(
    String agentProfile, {
    required String primaryProfileId,
    List<String> fallbackProfileIds = const [],
  }) async {
    return _client.request<ModelPolicyModel>(
      MvpEndpoint.settingsModelPolicySet,
      pathParams: {'agentProfile': agentProfile},
      body: {
        'primary_profile_id': primaryProfileId,
        'fallback_profile_ids': fallbackProfileIds,
      },
      decode: (json) => ModelPolicyModel.fromJson(json as Map<String, dynamic>),
    );
  }
}

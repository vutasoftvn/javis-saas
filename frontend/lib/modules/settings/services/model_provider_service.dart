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
      decode: (raw) => (raw as List? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(ModelProviderModel.fromJson)
          .toList(),
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
        'profile_id': ?_nonEmpty(profileId),
        'model_id': ?_nonEmpty(modelId),
        'api_key': ?_nonEmpty(apiKey),
        'base_url': ?_nonEmpty(baseUrl),
        'allowed_models': ?allowedModels,
        'budget_usd_limit': ?budgetUsdLimit,
        'max_concurrency': ?maxConcurrency,
      },
      decode: (raw) => ModelProviderModel.fromJson(_asMap(raw)),
    );
  }

  /// Health-check server-side cho 1 profile đã tạo. Caller (UI) KHÔNG được tự
  /// suy luận "usable" từ `credentialConfigured` — chỉ tin `ok` trả về từ
  /// chính call này, và chỉ SAU KHI call này thành công.
  Future<ApiResult<ModelProviderTestResultModel>> testConnection(String profileId) async {
    return _client.request<ModelProviderTestResultModel>(
      MvpEndpoint.settingsModelProviderTest,
      pathParams: {'profileId': profileId},
      decode: (raw) => ModelProviderTestResultModel.fromJson(_asMap(raw)),
    );
  }

  Future<ApiResult<ModelPolicyModel>> getPolicy(String agentProfile) async {
    return _client.request<ModelPolicyModel>(
      MvpEndpoint.settingsModelPolicyRead,
      pathParams: {'agentProfile': agentProfile},
      decode: (raw) => ModelPolicyModel.fromJson(_asMap(raw)),
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
      MvpEndpoint.settingsModelPolicyWrite,
      pathParams: {'agentProfile': agentProfile},
      body: {
        'primary_profile_id': primaryProfileId,
        'fallback_profile_ids': fallbackProfileIds,
      },
      decode: (raw) => ModelPolicyModel.fromJson(_asMap(raw)),
    );
  }

  static String? _nonEmpty(String? value) {
    final trimmed = value?.trim();
    return trimmed == null || trimmed.isEmpty ? null : trimmed;
  }

  static Map<String, dynamic> _asMap(Object? raw) {
    if (raw is Map<String, dynamic>) return raw;
    throw const FormatException('Expected JSON object for model settings response');
  }
}

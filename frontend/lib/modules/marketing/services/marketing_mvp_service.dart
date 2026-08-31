import 'package:http/http.dart' as http;

import '../../../core/network/api_result.dart';
import '../../../core/network/mvp_endpoints.g.dart';
import '../../../core/network/mvp_request_client.dart';
import '../models/marketing_mvp_models.dart';

class MarketingMvpService {
  final MvpRequestClient _client;

  MarketingMvpService({MvpRequestClient? client, http.Client? httpClient})
      : _client = client ?? MvpRequestClient(httpClient: httpClient);

  Future<ApiResult<MarketingContextModel>> getContext() async {
    return _client.request<MarketingContextModel>(
      MvpEndpoint.marketingContextGet,
      decode: (json) => MarketingContextModel.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<MarketingContextModel>> updateContext(Map<String, dynamic> data) async {
    return _client.request<MarketingContextModel>(
      MvpEndpoint.marketingContextUpdate,
      body: data,
      decode: (json) => MarketingContextModel.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<List<MarketingObjectiveModel>>> listObjectives() async {
    return _client.request<List<MarketingObjectiveModel>>(
      MvpEndpoint.marketingObjectiveList,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => MarketingObjectiveModel.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<List<MarketingCampaignModel>>> listCampaigns() async {
    return _client.request<List<MarketingCampaignModel>>(
      MvpEndpoint.marketingCampaignList,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => MarketingCampaignModel.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<List<CampaignAssetModel>>> listAssets({String? campaignId}) async {
    final query = <String, String>{};
    if (campaignId != null) {
      query['campaignId'] = campaignId;
    }
    return _client.request<List<CampaignAssetModel>>(
      MvpEndpoint.marketingAssetList,
      query: query.isNotEmpty ? query : null,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => CampaignAssetModel.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<List<MarketingExperimentModel>>> listExperiments() async {
    return _client.request<List<MarketingExperimentModel>>(
      MvpEndpoint.marketingExperimentList,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => MarketingExperimentModel.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<List<MarketingObservedMetricModel>>> getObservedMetrics({String? providerKey}) async {
    final query = <String, String>{};
    if (providerKey != null) {
      query['providerKey'] = providerKey;
    }
    return _client.request<List<MarketingObservedMetricModel>>(
      MvpEndpoint.marketingMetricObserved,
      query: query.isNotEmpty ? query : null,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => MarketingObservedMetricModel.fromJson(e))
            .toList();
      },
    );
  }
}

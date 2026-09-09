// Founder Trial R1 — legacy surface removed from the MVP contract. Every
// request here now returns MvpRequestClient.unavailable(); the retained
// class shell keeps callers compiling until the module is deleted.
// ignore_for_file: unused_field, unused_import, unused_element
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
    return MvpRequestClient.unavailable<MarketingContextModel>('marketingContextGet was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<MarketingContextModel>> updateContext(Map<String, dynamic> data) async {
    return MvpRequestClient.unavailable<MarketingContextModel>('marketingContextUpdate was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<List<MarketingObjectiveModel>>> listObjectives() async {
    return MvpRequestClient.unavailable<List<MarketingObjectiveModel>>('marketingObjectiveList was removed from the Founder Trial R1 contract');
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
    return MvpRequestClient.unavailable<List<CampaignAssetModel>>('marketingAssetList was removed from the Founder Trial R1 contract');
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
    return MvpRequestClient.unavailable<List<MarketingObservedMetricModel>>('marketingMetricObserved was removed from the Founder Trial R1 contract');
  }
}

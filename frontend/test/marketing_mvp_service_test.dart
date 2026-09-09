import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/marketing/models/marketing_mvp_models.dart';
import 'package:frontend/modules/marketing/services/marketing_mvp_service.dart';

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({
      'workspace_id': '1001',
    });
    await SecureStorageService.write('auth_token', 'test-token');
  });

  test('marketing 503 is unavailable, not an empty collection', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({'code': 'unavailable', 'message': 'Service temporarily unavailable'}),
        503,
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = MarketingMvpService(client: requestClient);

    final result = await service.listObjectives();
    expect(result, isA<ApiFailure<List<MarketingObjectiveModel>>>());
    expect((result as ApiFailure<List<MarketingObjectiveModel>>).failure.code, ApiFailureCode.unavailable);
  });



  test('list campaigns returns populated list with budget', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, contains('/commercial/marketing/campaigns'));

      return http.Response(
        jsonEncode({
          'data': [
            {
              'id': 'camp_1',
              'workspaceId': '1001',
              'name': 'Founder Led Launch',
              'funnelStage': 'discover',
              'budget': 5000000.0,
              'status': 'active',
              'createdAt': '2026-08-31T12:00:00.000Z',
              'updatedAt': '2026-08-31T12:00:00.000Z',
            }
          ],
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-08-31T12:00:00.000Z',
            'sources': [{'kind': 'company_db', 'ref': 'commercial.marketing'}],
          },
        }),
        200,
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = MarketingMvpService(client: requestClient);

    final result = await service.listCampaigns();
    expect(result, isA<ApiSuccess<List<MarketingCampaignModel>>>());
    final success = result as ApiSuccess<List<MarketingCampaignModel>>;
    expect(success.data.length, 1);
    expect(success.data.first.name, 'Founder Led Launch');
    expect(success.data.first.budget, 5000000.0);
  });

}

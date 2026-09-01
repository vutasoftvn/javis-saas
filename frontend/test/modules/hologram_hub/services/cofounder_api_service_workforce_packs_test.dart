import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/data/models/workforce_pack_model.dart';
import 'package:frontend/modules/hologram_hub/services/cofounder_api_service.dart';
import 'package:frontend/modules/workforce/services/workforce_mvp_service.dart';

// Fix-review (2026-09-01, Task 3) — `listWorkforcePacks` giờ trả
// `ApiResult<List<WorkforcePackModel>>` thay vì `List` trần, để phân biệt
// "tải thất bại" (ApiFailure) với "tải thành công nhưng workspace chưa gán
// agent nào" (ApiSuccess với data rỗng) — hai trạng thái này trước đây đều
// bị gộp chung thành `[]`.
void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({
      'auth_token': 'test-token',
      'workspace_id': 'ws_1001',
    });
  });

  test('listWorkforcePacks returns ApiFailure (not an empty list) when composition fetch fails', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(jsonEncode({'message': 'unavailable'}), 503);
    });
    final workforceMvpService = WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await CoFounderApiService.listWorkforcePacks(
      workforceMvpService: workforceMvpService,
    );

    expect(result, isA<ApiFailure<List<WorkforcePackModel>>>());
  });

  test('listWorkforcePacks returns ApiSuccess with real composition entries mapped to packs', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({
          'data': [
            {
              'functional_key': 'campaign_planner',
              'title': 'Campaign Planner',
              'description': 'Plans campaigns',
              'spec_id': 'spec_cp',
              'spec_version': 'v1',
              'definition_hash': 'hash_cp',
              'allowed_capability_prefixes': ['marketing.'],
              'assigned': true,
              'assignment_id': 'assign_1',
              'status': 'ACTIVE',
              'eligibility_reasons': [],
            },
          ],
          'meta': {
            'data_state': 'populated',
            'observed_at': '2026-08-31T12:00:00.000Z',
            'sources': [
              {'kind': 'agent_db', 'ref': 'agent.workforce_assignments'},
            ],
          },
        }),
        200,
      );
    });
    final workforceMvpService = WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await CoFounderApiService.listWorkforcePacks(
      workforceMvpService: workforceMvpService,
    );

    expect(result, isA<ApiSuccess<List<WorkforcePackModel>>>());
    final success = result as ApiSuccess<List<WorkforcePackModel>>;
    expect(success.data.single.key, 'campaign_planner');
    expect(success.data.single.isActive, isTrue);
  });

  test('listWorkforcePacks returns ApiSuccess with an empty list when workspace legitimately has no agents', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({
          'data': <dynamic>[],
          'meta': {
            'data_state': 'empty',
            'observed_at': '2026-08-31T12:00:00.000Z',
            'sources': [
              {'kind': 'agent_db', 'ref': 'agent.workforce_assignments'},
            ],
          },
        }),
        200,
      );
    });
    final workforceMvpService = WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await CoFounderApiService.listWorkforcePacks(
      workforceMvpService: workforceMvpService,
    );

    expect(result, isA<ApiSuccess<List<WorkforcePackModel>>>());
    expect((result as ApiSuccess<List<WorkforcePackModel>>).data, isEmpty);
  });

  test('toggleOptionalPack has no canonical route and always reports unavailable (false)', () async {
    final result = await CoFounderApiService.toggleOptionalPack(
      packKey: 'marketing',
      isActive: true,
    );
    expect(result, isFalse);
  });
}

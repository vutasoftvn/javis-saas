// Task 6 — chứng minh `ApprovalsService.list`/`decide` không bao giờ nuốt
// lỗi transport/parse thành `[]`/`null` giả tạo. Trước fix: `getApprovalsList`
// chỉ có nhánh `if (statusCode == 200)`, mọi mã khác (401/403/503/timeout/
// malformed) đều rơi xuống `return []` — y hệt "đã tải xong, không có gì".
import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/data/models/approval_model.dart';
import 'package:frontend/modules/approvals/services/approvals_service.dart';

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1001'});
    await SecureStorageService.write('auth_token', 'test-token');
  });

  ApprovalsService serviceWith(http.Client mockHttp) {
    return ApprovalsService(client: MvpRequestClient(httpClient: mockHttp));
  }

  group('list', () {
    test('maps HTTP 503 to ApiFailure instead of an empty approval list', () async {
      final mockHttp = MockClient((request) async {
        return http.Response(
          jsonEncode({'code': 'unavailable', 'message': 'Service temporarily unavailable'}),
          503,
        );
      });

      final result = await serviceWith(mockHttp).list();

      expect(result, isA<ApiFailure<List<ApprovalItemModel>>>());
      expect(
        (result as ApiFailure<List<ApprovalItemModel>>).failure.code,
        ApiFailureCode.unavailable,
      );
    });

    test('maps HTTP 401 to unauthenticated ApiFailure', () async {
      final mockHttp = MockClient((request) async {
        return http.Response(jsonEncode({'message': 'Missing token'}), 401);
      });

      final result = await serviceWith(mockHttp).list();

      expect(result, isA<ApiFailure<List<ApprovalItemModel>>>());
      expect(
        (result as ApiFailure<List<ApprovalItemModel>>).failure.code,
        ApiFailureCode.unauthenticated,
      );
    });

    test('maps HTTP 403 to forbidden ApiFailure', () async {
      final mockHttp = MockClient((request) async {
        return http.Response(jsonEncode({'message': 'Forbidden'}), 403);
      });

      final result = await serviceWith(mockHttp).list();

      expect(result, isA<ApiFailure<List<ApprovalItemModel>>>());
      expect(
        (result as ApiFailure<List<ApprovalItemModel>>).failure.code,
        ApiFailureCode.forbidden,
      );
    });

    test('maps a network timeout to ApiFailure', () async {
      final mockHttp = MockClient((request) async {
        throw TimeoutException('deadline exceeded');
      });

      final result = await serviceWith(mockHttp).list();

      expect(result, isA<ApiFailure<List<ApprovalItemModel>>>());
      expect(
        (result as ApiFailure<List<ApprovalItemModel>>).failure.code,
        ApiFailureCode.unavailable,
      );
    });

    test('maps a malformed success body to ApiFailure, not an empty list', () async {
      final mockHttp = MockClient((request) async {
        return http.Response('not json at all {{{', 200);
      });

      final result = await serviceWith(mockHttp).list();

      expect(result, isA<ApiFailure<List<ApprovalItemModel>>>());
      expect(
        (result as ApiFailure<List<ApprovalItemModel>>).failure.code,
        ApiFailureCode.malformedResponse,
      );
    });

    test('genuinely empty success returns ApiSuccess with empty dataState', () async {
      final mockHttp = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'data': [],
            'meta': {
              'dataState': 'empty',
              'observedAt': '2026-09-02T12:00:00.000Z',
              'sources': [
                {'kind': 'agent_db', 'ref': 'agent.approvals'},
              ],
            },
          }),
          200,
        );
      });

      final result = await serviceWith(mockHttp).list();

      expect(result, isA<ApiSuccess<List<ApprovalItemModel>>>());
      final success = result as ApiSuccess<List<ApprovalItemModel>>;
      expect(success.data, isEmpty);
      expect(success.meta.dataState, ApiDataState.empty);
    });

    test('genuinely populated success returns typed ApprovalItemModel list', () async {
      final mockHttp = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'data': [
              {
                'id': 'appr_1',
                'approval_id': 'appr_1',
                'action': 'send_email',
                'status': 'pending',
                'risk_level': 'high',
              },
            ],
            'meta': {
              'dataState': 'populated',
              'observedAt': '2026-09-02T12:00:00.000Z',
              'sources': [
                {'kind': 'agent_db', 'ref': 'agent.approvals'},
              ],
            },
          }),
          200,
        );
      });

      final result = await serviceWith(mockHttp).list();

      expect(result, isA<ApiSuccess<List<ApprovalItemModel>>>());
      final success = result as ApiSuccess<List<ApprovalItemModel>>;
      expect(success.data, hasLength(1));
      expect(success.data.first.id, 'appr_1');
      expect(success.data.first.status, ApprovalStatus.pending);
    });
  });

  group('decide', () {
    test('decision failure (409 conflict) maps to ApiFailure, not a silent false', () async {
      final mockHttp = MockClient((request) async {
        return http.Response(jsonEncode({'message': 'Already decided'}), 409);
      });

      final result = await serviceWith(mockHttp).decide('appr_1', approved: true);

      expect(result, isA<ApiFailure<ApprovalItemModel>>());
      expect(
        (result as ApiFailure<ApprovalItemModel>).failure.code,
        ApiFailureCode.conflict,
      );
    });

    test('decision success returns ApiSuccess', () async {
      final mockHttp = MockClient((request) async {
        expect(request.method, 'POST');
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['approved'], isTrue);
        return http.Response(
          jsonEncode({
            'data': {
              'approval_id': 'appr_1',
              'run_id': 'run_1',
              'status': 'approved',
              'reviewer': 'user_1',
              'reason': null,
              'decided_at': '2026-09-02T12:05:00.000Z',
            },
            'meta': {
              'dataState': 'populated',
              'observedAt': '2026-09-02T12:05:00.000Z',
              'sources': [
                {'kind': 'agent_db', 'ref': 'agent.approvals'},
              ],
            },
          }),
          200,
        );
      });

      final result = await serviceWith(mockHttp).decide('appr_1', approved: true);

      expect(result, isA<ApiSuccess<ApprovalItemModel>>());
    });
  });
}

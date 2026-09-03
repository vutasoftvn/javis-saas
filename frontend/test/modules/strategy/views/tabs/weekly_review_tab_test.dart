import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/strategy/services/strategy_mvp_client.dart';
import 'package:frontend/modules/strategy/services/twelve_wy_service.dart';
import 'package:frontend/modules/strategy/views/tabs/weekly_review_tab.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-1'});
    // MvpRequestClient yêu cầu cả token lẫn workspaceId trước khi gọi HTTP
    // thật (DefaultApiAuthResolver.tokenFor đọc SecureStorageService) — thiếu
    // token sẽ trả về ApiFailure(unauthenticated) trước khi request chạm
    // tới MockClient, giống pattern setUp() của strategy_mvp_service_test.dart.
    await SecureStorageService.write('auth_token', 'test-token');
  });

  testWidgets('shows plan focus, commitments, and saves review on submit', (
    tester,
  ) async {
    var updateCalled = false;

    // `WeeklyReviewTab()` mặc định dựng `TwelveWyService()` → `StrategyMvpClient()`
    // → `MvpRequestClient()` với `http.Client()` THẬT riêng — không đọc qua
    // `ApiClient.client`, nên override `ApiClient.client = MockClient(...)`
    // không có tác dụng ở đây. Phải tiêm mock HTTP trực tiếp qua
    // `MvpRequestClient(httpClient: ...)`, đúng pattern đã dùng trong
        // strategy_mvp_service_test.dart.
    // `MvpRequestClient._decodeResponse` bắt buộc envelope
    // `{"data": ..., "meta": {"dataState": ..., "observedAt": ...}}` —
    // trả raw JSON array/object (như plan mẫu ban đầu) sẽ bị coi là
    // malformedResponse.
    Map<String, dynamic> envelope(Object? data) => {
      'data': data,
      'meta': {
        'dataState': 'populated',
        'observedAt': DateTime.now().toIso8601String(),
      },
    };

    // `http.Response` mặc định encode body bằng latin1 khi thiếu header
    // `content-type; charset=utf-8` — vỡ với text tiếng Việt có dấu. Convention
    // đã dùng khắp `frontend/test/` (vd. `strategy_mvp_service_test.dart`).
    const utf8JsonHeaders = {'content-type': 'application/json; charset=utf-8'};

    final mockHttp = MockClient((request) async {
      if (request.method == 'GET' &&
          request.url.path == '/operations/twelve-week-plans') {
        return http.Response(
          jsonEncode(
            envelope([
              {
                'id': 'plan-1',
                'workspaceId': 'workspace-1',
                'cycleId': 'cycle-1',
                'weekNo': 1,
                'focus': 'Xác thực vấn đề',
                'createdAt': DateTime.now().toIso8601String(),
              },
            ]),
          ),
          200,
          headers: utf8JsonHeaders,
        );
      }
      if (request.method == 'GET' &&
          request.url.path == '/operations/twelve-week-commitments') {
        return http.Response(
          jsonEncode(
            envelope([
              {
                'id': 'commit-1',
                'workspaceId': 'workspace-1',
                'weeklyPlanId': 'plan-1',
                'title': 'Phỏng vấn 5 khách hàng',
                'status': 'done',
                'createdAt': DateTime.now().toIso8601String(),
              },
            ]),
          ),
          200,
          headers: utf8JsonHeaders,
        );
      }
      if (request.method == 'PATCH' &&
          request.url.path == '/operations/twelve-week-plans/plan-1') {
        updateCalled = true;
        return http.Response(
          jsonEncode(
            envelope({
              'id': 'plan-1',
              'workspaceId': 'workspace-1',
              'cycleId': 'cycle-1',
              'weekNo': 1,
              'focus': 'Xác thực vấn đề',
              'executionScore': 80,
              'createdAt': DateTime.now().toIso8601String(),
            }),
          ),
          200,
          headers: utf8JsonHeaders,
        );
      }
      return http.Response('not found', 404);
    });

    final service = TwelveWyService(
      client: StrategyMvpClient(client: MvpRequestClient(httpClient: mockHttp)),
    );

    await tester.pumpWidget(
      GetMaterialApp(home: Scaffold(body: WeeklyReviewTab(service: service))),
    );
    await tester.pumpAndSettle();

    expect(find.text('Xác thực vấn đề'), findsOneWidget);
    expect(find.text('Phỏng vấn 5 khách hàng'), findsOneWidget);

    await tester.enterText(
      find.byKey(const Key('execution_score_field')),
      '80',
    );
    await tester.tap(find.text('Lưu review'));
    await tester.pumpAndSettle();

    expect(updateCalled, isTrue);
  });
}

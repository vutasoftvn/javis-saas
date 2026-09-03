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

    // Save thành công giờ hiện thêm `AppToast.success` — để hết animation
    // GetX Snackbar chạy xong và timer tự-đóng (4-5s) trôi hết, tránh lỗi
    // "A Timer is still pending" khi widget tree bị dispose cuối test.
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    await tester.pumpAndSettle(const Duration(seconds: 5));
  });

  testWidgets(
    'shows error toast and keeps old value when backend rejects the save '
    '(Finding Important #1 — lỗi lưu review không được nuốt im lặng)',
    (tester) async {
      Map<String, dynamic> envelope(Object? data) => {
        'data': data,
        'meta': {
          'dataState': 'populated',
          'observedAt': DateTime.now().toIso8601String(),
        },
      };
      const utf8JsonHeaders = {
        'content-type': 'application/json; charset=utf-8',
      };

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
            jsonEncode(envelope(<Map<String, dynamic>>[])),
            200,
            headers: utf8JsonHeaders,
          );
        }
        if (request.method == 'PATCH' &&
            request.url.path == '/operations/twelve-week-plans/plan-1') {
          // "80" hợp lệ ở cả client lẫn range 0-100 nên request vẫn đi ra —
          // mô phỏng 1 lỗi backend KHÔNG bắt được ở client (vd. plan đã bị
          // khoá review, workspace hết quyền...) để verify lỗi server luôn
          // được hiển thị cho user, không phụ thuộc vào validate client.
          return http.Response(
            jsonEncode({'message': 'weekly plan is locked for review'}),
            409,
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

      await tester.enterText(
        find.byKey(const Key('execution_score_field')),
        '80',
      );
      await tester.tap(find.text('Lưu review'));
      await tester.pumpAndSettle();

      expect(
        find.text('weekly plan is locked for review'),
        findsOneWidget,
      );
      // Nút quay lại trạng thái sẵn sàng lưu lại, không kẹt ở "Đang lưu...".
      expect(find.text('Lưu review'), findsOneWidget);

      // Flush GetX Snackbar animation + timer tự-đóng để tránh lỗi "A Timer
      // is still pending" khi widget tree bị dispose cuối test (đúng pattern
      // `app_toast_test.dart`).
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pumpAndSettle(const Duration(seconds: 5));
    },
  );

  testWidgets(
    'blocks save and shows error toast when execution score is not a valid '
    'number (Finding Important #2 — input sai âm thầm không làm gì)',
    (tester) async {
      Map<String, dynamic> envelope(Object? data) => {
        'data': data,
        'meta': {
          'dataState': 'populated',
          'observedAt': DateTime.now().toIso8601String(),
        },
      };
      const utf8JsonHeaders = {
        'content-type': 'application/json; charset=utf-8',
      };

      var updateCalled = false;
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
            jsonEncode(envelope(<Map<String, dynamic>>[])),
            200,
            headers: utf8JsonHeaders,
          );
        }
        if (request.method == 'PATCH' &&
            request.url.path == '/operations/twelve-week-plans/plan-1') {
          updateCalled = true;
          return http.Response('not found', 404);
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

      // Gõ nhầm "9O" (chữ O) thay vì "90" — double.tryParse trả null.
      await tester.enterText(
        find.byKey(const Key('execution_score_field')),
        '9O',
      );
      await tester.tap(find.text('Lưu review'));
      await tester.pumpAndSettle();

      expect(updateCalled, isFalse);
      expect(find.text('Điểm thực thi phải là một số hợp lệ'), findsOneWidget);

      // Flush GetX Snackbar animation + timer tự-đóng để tránh lỗi "A Timer
      // is still pending" khi widget tree bị dispose cuối test.
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pumpAndSettle(const Duration(seconds: 5));
    },
  );
}

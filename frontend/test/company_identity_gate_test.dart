// frontend/test/company_identity_gate_test.dart
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/onboarding/services/company_identity_gate.dart';
import 'package:frontend/modules/onboarding/widgets/company_identity_modal.dart';

// Xem giải thích chi tiết trong company_identity_modal_test.dart: gọi
// testWidgets() (khác test() trần) khiến platform-channel này KHÔNG tự throw
// MissingPluginException, treo vĩnh viễn mọi call qua ApiClient nếu không
// mock — cần cho test "production path" dùng testWidgets bên dưới.
const MethodChannel _secureStorageChannel =
    MethodChannel('plugins.it_nomads.com/flutter_secure_storage');

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  SharedPreferences.setMockInitialValues({});
  Get.testMode = true;
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      .setMockMethodCallHandler(_secureStorageChannel, (MethodCall methodCall) async {
    if (methodCall.method == 'read') return null;
    if (methodCall.method == 'readAll') return <String, String>{};
    return null;
  });

  late http.Client originalClient;
  setUp(() => originalClient = ApiClient.client);
  tearDown(() => ApiClient.client = originalClient);

  test('calls showModal when the workspace is missing vision/mission/coreValues', () async {
    var fetchCount = 0;
    ApiClient.client = MockClient((request) async {
      fetchCount++;
      // Lần fetch đầu tiên trả về thiếu dữ liệu (kích hoạt showModal); lần
      // fetch thứ hai (sau khi loop re-check) trả về đủ dữ liệu để thoát loop
      // — mô phỏng dialog lưu thành công.
      if (fetchCount == 1) {
        return http.Response(
          '{"id":"ws_1","vision":null,"mission":null,"coreValues":null}',
          200,
        );
      }
      return http.Response(
        '{"id":"ws_1","vision":"V","mission":"M","coreValues":"C"}',
        200,
      );
    });

    var shown = false;
    await CompanyIdentityGate.checkAndPrompt(
      'ws_1',
      showModal: (workspaceId) async {
        shown = true;
        expect(workspaceId, 'ws_1');
      },
    );

    expect(shown, isTrue);
  });

  test('re-checks after show() and re-prompts if still incomplete', () async {
    var fetchCount = 0;
    ApiClient.client = MockClient((request) async {
      fetchCount++;
      if (fetchCount < 3) {
        return http.Response(
          '{"id":"ws_2","vision":null,"mission":null,"coreValues":null}',
          200,
        );
      }
      return http.Response(
        '{"id":"ws_2","vision":"V","mission":"M","coreValues":"C"}',
        200,
      );
    });

    var showCount = 0;
    await CompanyIdentityGate.checkAndPrompt(
      'ws_2',
      showModal: (workspaceId) async => showCount++,
    );

    expect(showCount, 2);
  });

  test('an in-flight call guards against a second concurrent call stacking a modal', () async {
    var fetchCount = 0;
    ApiClient.client = MockClient((request) async {
      fetchCount++;
      // Fetch đầu tiên thiếu dữ liệu (kích hoạt show()); fetch thứ hai (sau
      // khi show() của call đầu resolve) đã đủ dữ liệu để thoát loop, tránh
      // show() lặp vô hạn trong test.
      if (fetchCount == 1) {
        return http.Response(
          '{"id":"ws_3","vision":null,"mission":null,"coreValues":null}',
          200,
        );
      }
      return http.Response(
        '{"id":"ws_3","vision":"V","mission":"M","coreValues":"C"}',
        200,
      );
    });

    var showCount = 0;
    final completer = Completer<void>();
    final first = CompanyIdentityGate.checkAndPrompt(
      'ws_3',
      showModal: (workspaceId) async {
        showCount++;
        await completer.future;
      },
    );
    // Bắn call thứ hai trong lúc call đầu vẫn đang await bên trong show() —
    // guard _inFlight phải khiến nó return ngay, không show() lần nữa.
    final second = CompanyIdentityGate.checkAndPrompt(
      'ws_3',
      showModal: (workspaceId) async => showCount++,
    );
    await Future<void>.delayed(Duration.zero);
    completer.complete();
    await Future.wait([first, second]);

    expect(showCount, 1);
  });

  test('does not call showModal when the workspace already has all three fields', () async {
    ApiClient.client = MockClient((request) async {
      return http.Response('{"id":"ws_1","vision":"V","mission":"M","coreValues":"C"}', 200);
    });

    var shown = false;
    await CompanyIdentityGate.checkAndPrompt(
      'ws_1',
      showModal: (workspaceId) async => shown = true,
    );

    expect(shown, isFalse);
  });

  test('fails open (does not call showModal) when the fetch itself errors', () async {
    ApiClient.client = MockClient((request) async {
      return http.Response('server error', 500);
    });

    var shown = false;
    await CompanyIdentityGate.checkAndPrompt(
      'ws_1',
      showModal: (workspaceId) async => shown = true,
    );

    expect(shown, isFalse);
  });

  testWidgets(
    'production path: real Get.dialog renders CompanyIdentityModal without a Material-ancestor crash',
    (tester) async {
      var fetchCount = 0;
      ApiClient.client = MockClient((request) async {
        fetchCount++;
        // Lần fetch thứ hai (sau khi dialog bị đóng ở cuối test) trả về đủ
        // dữ liệu để loop trong checkAndPrompt thoát hẳn, tránh future chạy
        // nền vô hạn sau khi test kết thúc.
        if (fetchCount == 1) {
          return http.Response(
            '{"id":"ws_real","vision":null,"mission":null,"coreValues":null}',
            200,
          );
        }
        return http.Response(
          '{"id":"ws_real","vision":"V","mission":"M","coreValues":"C"}',
          200,
        );
      });

      await tester.pumpWidget(
        GetMaterialApp(home: const Scaffold(body: SizedBox.shrink())),
      );
      await tester.pumpAndSettle();

      // Không truyền showModal — dùng đúng đường dẫn production
      // (Get.dialog), nơi Finding 1 phát hiện thiếu Material ancestor.
      // Không await tới cùng vì Get.dialog chỉ resolve khi dialog bị
      // pop (barrierDismissible: false, không có nút đóng) — chỉ cần
      // kick off rồi pump để dialog build xong.
      unawaited(CompanyIdentityGate.checkAndPrompt('ws_real'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
      expect(find.byType(CompanyIdentityModal), findsOneWidget);

      // Dọn dẹp: đóng dialog để không leak state sang test khác.
      Get.back<void>();
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));
      await tester.pumpAndSettle();
    },
  );
}

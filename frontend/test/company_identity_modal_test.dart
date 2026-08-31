// frontend/test/company_identity_modal_test.dart
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/onboarding/widgets/company_identity_modal.dart';

// `SecureStorageService.read()` gọi `FlutterSecureStorage().read()` trước —
// một lệnh platform-channel thật. Trong `test()` trần, lệnh này ném
// `MissingPluginException` ngay (rơi xuống fallback SharedPreferences), NHƯNG
// trong `testWidgets()` nó KHÔNG throw — treo vĩnh viễn, khiến mọi call qua
// `ApiClient` (vốn gọi `SecureStorageService.read` để lấy auth header) hang.
// Mock method channel này để trả về null ngay, ép rơi xuống nhánh
// SharedPreferences như mong đợi trong test.
const MethodChannel _secureStorageChannel =
    MethodChannel('plugins.it_nomads.com/flutter_secure_storage');

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  SharedPreferences.setMockInitialValues({
    'workspace_id': 'ws_1',
  });
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      .setMockMethodCallHandler(_secureStorageChannel, (MethodCall methodCall) async {
    if (methodCall.method == 'read') return null;
    if (methodCall.method == 'readAll') return <String, String>{};
    return null;
  });

  late http.Client originalClient;
  setUp(() => originalClient = ApiClient.client);
  tearDown(() => ApiClient.client = originalClient);

  Future<void> pumpModal(WidgetTester tester) async {
    // Dialog() (thêm để cấp Material ancestor — xem Finding 1) có
    // insetPadding riêng cộng với Padding(24) hiện tại của nội dung, cần
    // viewport cao hơn mặc định 800x600 để nút "Lưu" không bị đẩy ra ngoài
    // vùng test surface (gây lỗi hit-test "outside the bounds").
    tester.view.physicalSize = const Size(800, 1200);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: CompanyIdentityModal(workspaceId: 'ws_1')),
      ),
    );
  }

  testWidgets('Save button is disabled until all three fields are filled', (tester) async {
    await pumpModal(tester);

    final saveBtn = find.widgetWithText(ElevatedButton, 'Lưu');
    expect(tester.widget<ElevatedButton>(saveBtn).onPressed, isNull);

    await tester.enterText(find.byKey(const Key('company_identity_vision_field')), 'Vision');
    await tester.enterText(find.byKey(const Key('company_identity_mission_field')), 'Mission');
    await tester.pump();
    expect(tester.widget<ElevatedButton>(saveBtn).onPressed, isNull);

    await tester.enterText(find.byKey(const Key('company_identity_values_field')), 'Values');
    await tester.pump();
    expect(tester.widget<ElevatedButton>(saveBtn).onPressed, isNotNull);
  });

  testWidgets('Save button taps and initiates save flow', (tester) async {
    // Mock the HTTP client to capture the save request
    ApiClient.client = MockClient((request) async {
      // Return success response for any PATCH request to company identity
      if (request.method == 'PATCH' && request.url.toString().contains('company-identity')) {
        return http.Response(
          '{"id":"ws_1","vision":"Vision text","mission":"Mission text","coreValues":"Values text"}',
          200,
        );
      }
      return http.Response('not found', 404);
    });

    await pumpModal(tester);
    await tester.enterText(find.byKey(const Key('company_identity_vision_field')), 'Vision text');
    await tester.enterText(find.byKey(const Key('company_identity_mission_field')), 'Mission text');
    await tester.enterText(find.byKey(const Key('company_identity_values_field')), 'Values text');
    await tester.pump();

    // Verify save button is enabled
    final saveBtn = find.widgetWithText(ElevatedButton, 'Lưu');
    expect(tester.widget<ElevatedButton>(saveBtn).onPressed, isNotNull);

    // Tap save button
    await tester.tap(saveBtn);
    // Pump to allow the async operation to start and show loading indicator
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    // Verify loading indicator appears (indicating save operation started)
    expect(find.byType(CircularProgressIndicator), findsWidgets);
  });

  testWidgets('modal has no dismiss affordance (blocking)', (tester) async {
    await pumpModal(tester);
    expect(find.byIcon(Icons.close), findsNothing);
    expect(find.byType(BackButton), findsNothing);
  });

  testWidgets('"Nhờ AI soạn" fills the three fields from a well-formed SSE reply', (tester) async {
    ApiClient.client = MockClient((request) async {
      final path = request.url.path;
      if (path == '/agent/conversations' && request.method == 'POST') {
        return http.Response(
          '{"id":"conv_1","workspace_id":"ws1","created_by_principal":"p1",'
          '"title":"Company Identity Draft","created_at":"2026-08-31T00:00:00Z",'
          '"updated_at":"2026-08-31T00:00:00Z"}',
          201,
        );
      }
      if (path == '/agent/conversations/conv_1/messages' && request.method == 'POST') {
        return http.Response('{"run_id":"run_1","status":"accepted"}', 202);
      }
      if (path == '/agent/runs/run_1/events') {
        return http.Response(
          'event: message.delta\n'
          'data: {"payload":{"delta":"VISION: Tro thanh so 1.\\nMISSION: Trao quyen cho founder.\\nVALUES: Minh bach, Toc do."}}\n\n'
          'event: run.completed\n'
          'data: {"payload":{"output":null}}\n\n',
          200,
          headers: {'content-type': 'text/event-stream'},
        );
      }
      return http.Response('not found', 404);
    });

    await pumpModal(tester);
    await tester.tap(find.widgetWithText(OutlinedButton, 'Nhờ AI soạn'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.text('Tro thanh so 1.'), findsOneWidget);
    expect(find.text('Trao quyen cho founder.'), findsOneWidget);
    expect(find.text('Minh bach, Toc do.'), findsOneWidget);
  });

  Future<void> mockAiSse(String delta) async {
    ApiClient.client = MockClient((request) async {
      final path = request.url.path;
      if (path == '/agent/conversations' && request.method == 'POST') {
        return http.Response(
          '{"id":"conv_1","workspace_id":"ws1","created_by_principal":"p1",'
          '"title":"Company Identity Draft","created_at":"2026-08-31T00:00:00Z",'
          '"updated_at":"2026-08-31T00:00:00Z"}',
          201,
        );
      }
      if (path == '/agent/conversations/conv_1/messages' && request.method == 'POST') {
        return http.Response('{"run_id":"run_1","status":"accepted"}', 202);
      }
      if (path == '/agent/runs/run_1/events') {
        return http.Response(
          'event: message.delta\n'
          'data: {"payload":{"delta":${jsonEncode(delta)}}}\n\n'
          'event: run.completed\n'
          'data: {"payload":{"output":null}}\n\n',
          200,
          headers: {'content-type': 'text/event-stream'},
        );
      }
      return http.Response('not found', 404);
    });
  }

  testWidgets(
    '"Nhờ AI soạn" with a fully malformed reply does not pollute Vision and shows an error instead',
    (tester) async {
      await mockAiSse('Cau tra loi tu do khong dung dinh dang.');

      await pumpModal(tester);
      await tester.tap(find.widgetWithText(OutlinedButton, 'Nhờ AI soạn'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      // Không field nào bị ghi đè bằng text thô/marker lỗi.
      final visionField = tester.widget<TextField>(
        find.byKey(const Key('company_identity_vision_field')),
      );
      final missionField = tester.widget<TextField>(
        find.byKey(const Key('company_identity_mission_field')),
      );
      final valuesField = tester.widget<TextField>(
        find.byKey(const Key('company_identity_values_field')),
      );
      expect(visionField.controller!.text, isEmpty);
      expect(missionField.controller!.text, isEmpty);
      expect(valuesField.controller!.text, isEmpty);
      expect(
        find.textContaining('AI trả lời chưa đủ định dạng'),
        findsOneWidget,
      );
    },
  );

  testWidgets(
    '"Nhờ AI soạn" with a partial reply fills what parsed and leaves the rest untouched',
    (tester) async {
      await mockAiSse('VISION: Tro thanh so 1.\nMISSION: Trao quyen cho founder.');

      await pumpModal(tester);
      await tester.tap(find.widgetWithText(OutlinedButton, 'Nhờ AI soạn'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(find.text('Tro thanh so 1.'), findsOneWidget);
      expect(find.text('Trao quyen cho founder.'), findsOneWidget);
      final valuesField = tester.widget<TextField>(
        find.byKey(const Key('company_identity_values_field')),
      );
      expect(valuesField.controller!.text, isEmpty);
      expect(
        find.textContaining('AI trả lời chưa đủ định dạng'),
        findsOneWidget,
      );
    },
  );
}

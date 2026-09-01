import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/vault/controllers/vault_controller.dart';
import 'package:frontend/modules/vault/views/vault_view.dart';

/// Task 5 (Truthful MVP Hardening) — Vault chưa có storage/indexing/retrieval
/// thật ở backend, nên UI phải công khai trạng thái "chưa khả dụng" và tuyệt
/// đối không gọi bất kỳ route `/vault/*` legacy nào (những route đó giờ đã bị
/// containment ở apps/cosa/api/vault_routes.py, trả 501).
void main() {
  late http.Client realClient;
  final recordedRequests = <http.BaseRequest>[];

  setUp(() {
    realClient = ApiClient.client;
    recordedRequests.clear();
    ApiClient.client = MockClient((request) async {
      recordedRequests.add(request);
      return http.Response('{}', 200);
    });
  });

  tearDown(() {
    ApiClient.client = realClient;
    Get.delete<VaultController>(force: true);
  });

  testWidgets(
    'Vault screen explains unavailable capability without requesting legacy /vault routes',
    (tester) async {
      await tester.pumpWidget(const MaterialApp(home: VaultView()));
      await tester.pumpAndSettle();

      expect(find.text('Vault chưa khả dụng'), findsOneWidget);
      expect(find.textContaining('chưa khả dụng'), findsWidgets);
      expect(
        recordedRequests.where((r) => r.url.path.startsWith('/vault/')),
        isEmpty,
      );
    },
  );

  testWidgets('Vault screen has no edit, save, promote or retrieval affordance', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: VaultView()));
    await tester.pumpAndSettle();

    expect(find.text('Chỉnh sửa'), findsNothing);
    expect(find.text('Lưu'), findsNothing);
    expect(find.textContaining('Phê duyệt'), findsNothing);
    expect(find.byIcon(Icons.edit_rounded), findsNothing);
    expect(find.byIcon(Icons.save_rounded), findsNothing);
  });
}

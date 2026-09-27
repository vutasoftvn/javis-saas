import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:frontend/core/network/api_auth_resolver.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/services/project_memory_service.dart';
import 'package:frontend/modules/hologram_hub/widgets/chat_panel_content.dart';

class _Auth implements ApiAuthResolver {
  @override
  Future<String?> tokenFor(ApiPlane plane) async => 'tok';

  @override
  Future<String?> workspaceId() async => 'ws_1';
}

/// Review 2026-09-27 G-8 — fact dự án founder xác nhận.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late List<http.Request> sent;
  late ProjectMemoryService service;

  setUp(() {
    Get.testMode = true;
    Get.reset();
    sent = [];
    http.Response ok(Object body, [int status = 200]) => http.Response.bytes(
          utf8.encode(jsonEncode(body)),
          status,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
    final mock = MockClient((req) async {
      sent.add(req);
      if (req.method == 'POST') {
        final body = jsonDecode(req.body) as Map<String, dynamic>;
        return ok({'id': 'f1', 'content': body['content']}, 201);
      }
      if (req.method == 'DELETE') {
        return ok({'id': 'f1', 'status': 'RETRACTED'});
      }
      return ok({
        'facts': [
          {'id': 'f1', 'content': 'Runway 6 tháng'},
        ],
      });
    });
    service = ProjectMemoryService(client: MvpRequestClient(httpClient: mock, authResolver: _Auth()));
  });

  tearDown(Get.reset);

  test('list/create/retract hit the contract routes', () async {
    final listed = await service.list('p1');
    expect((listed as ApiSuccess<List<ProjectFact>>).data.single.content, 'Runway 6 tháng');
    expect(sent.last.url.path, '/agent/projects/p1/memory/facts');

    final created = await service.create('p1', 'Ưu tiên B2B', sourceMessageId: 'm1');
    expect((created as ApiSuccess<ProjectFact>).data.content, 'Ưu tiên B2B');
    expect(jsonDecode(sent.last.body), {'content': 'Ưu tiên B2B', 'source_message_id': 'm1'});

    final retracted = await service.retract('p1', 'f1');
    expect((retracted as ApiSuccess<bool>).data, isTrue);
    expect(sent.last.method, 'DELETE');
    expect(sent.last.url.path, '/agent/projects/p1/memory/facts/f1');
  });

  test('memoryConfirmFact parses only memory_confirm cards', () {
    expect(memoryConfirmFact('{"kind":"memory_confirm","fact":"A"}'), 'A');
    expect(memoryConfirmFact('{"kind":"goal_confirm","normalized_goal":"A"}'), isNull);
    expect(memoryConfirmFact('xin chào'), isNull);
  });

  testWidgets('memory_confirm card saves through the controller only on click', (tester) async {
    final controller = Get.put(FounderCommandCenterController(projectMemoryService: service));
    controller.activeProjectId.value = 'p1';
    controller.chatMessages.add({
      'role': 'assistant',
      'content': '{"kind":"memory_confirm","fact":"Khách hàng mục tiêu là SME"}',
    });
    await tester.pumpWidget(
      GetMaterialApp(home: Scaffold(body: ChatPanelContent(controller: controller, onClose: () {}))),
    );
    await tester.pump();

    expect(find.text('Lưu điều này vào trí nhớ dự án?'), findsOneWidget);
    expect(find.textContaining('"kind"'), findsNothing);
    expect(sent.where((r) => r.method == 'POST'), isEmpty);

    await tester.tap(find.text('Lưu'));
    await tester.pumpAndSettle();

    final posts = sent.where((r) => r.method == 'POST').toList();
    expect(posts, hasLength(1));
    expect(jsonDecode(posts.single.body)['content'], 'Khách hàng mục tiêu là SME');
    expect(find.text('Đã lưu'), findsOneWidget);
  });
}

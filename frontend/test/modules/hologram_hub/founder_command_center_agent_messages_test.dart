import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/models/project_activity_models.dart';
import 'package:frontend/modules/hologram_hub/services/project_activity_service.dart';

/// WGA G9 — message agent chèn vào conversation (plan_progress, goal_confirm,
/// kết quả lập kế hoạch) tới chat đang mở qua Project Activity SSE.
class _FakeActivityService extends ProjectActivityService {
  final controller = StreamController<ProjectActivityEvent>();
  String? streamedProject;

  @override
  Stream<ProjectActivityEvent> stream(String projectId, {int? afterSequence}) {
    streamedProject = projectId;
    return controller.stream;
  }
}

ProjectActivityEvent _event(String kind, int seq) => ProjectActivityEvent(
      eventId: 'ev$seq',
      workspaceId: 'ws_1',
      projectId: 'proj-1',
      projectSequence: seq,
      kind: kind,
      sourceType: 'message',
      sourceId: 'm$seq',
    );

http.Response _ok(Object body) => http.Response(
      jsonEncode(body),
      200,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

Map<String, dynamic> _msg(String id, String content, {String? runId}) => {
      'id': id,
      'conversation_id': 'conv_1',
      'role': 'assistant',
      'content': content,
      'run_id': runId,
    };

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client original;
  late List<Map<String, dynamic>> serverMessages;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});
    Get.testMode = true;
    Get.reset();
    original = ApiClient.client;
    serverMessages = [];
    ApiClient.client = MockClient((req) async {
      if (req.method == 'GET' && req.url.path == '/agent/sessions/conv_1') {
        return _ok({
          'id': 'conv_1',
          'workspace_id': 'ws_1',
          'title': 't',
          'status': 'idle',
          'messages': serverMessages,
        });
      }
      if (req.method == 'POST' &&
          req.url.path == '/operations/strategy/projects/proj-1/weekly-goal') {
        return _ok({'weeklyPlanId': 'wp-1', 'focus': 'x', 'decompositionRequested': true});
      }
      return http.Response('{}', 404);
    });
  });
  tearDown(() {
    ApiClient.client = original;
    Get.reset();
  });

  test('syncAgentChatMessages adds only agent-inserted messages, once', () async {
    serverMessages = [
      _msg('m1', 'Trả lời thường của chat', runId: 'run_abc'),
      _msg('m2', '{"kind":"plan_progress","plan_id":"pl1","done":["A"]}',
          runId: 'wga_progress_pl1'),
      _msg('m3', 'Đã lập kế hoạch triển khai từ mục tiêu tuần.', runId: 'wga_decomp_1'),
      _msg('m4', '{"kind":"goal_confirm","normalized_goal":"G"}', runId: 'run_abc'),
    ];
    final c = FounderCommandCenterController(projectActivityService: _FakeActivityService());
    c.seedConversationIdForTest('conv_1');

    await c.syncAgentChatMessages();
    await c.syncAgentChatMessages();

    expect(c.chatMessages.map((m) => m['content']).toList(), [
      '{"kind":"plan_progress","plan_id":"pl1","done":["A"]}',
      'Đã lập kế hoạch triển khai từ mục tiêu tuần.',
      '{"kind":"goal_confirm","normalized_goal":"G"}',
    ]);
  });

  test('agent.chat_message activity event pushes the new message into the open chat',
      () async {
    final activity = _FakeActivityService();
    final c = FounderCommandCenterController(projectActivityService: activity);
    c.activeProjectId.value = 'proj-1';
    c.seedConversationIdForTest('conv_1');

    // Chat mở kế hoạch từ chat -> bắt đầu nghe Project Activity của Project.
    await c.requestDecomposition('Mục tiêu', origin: 'chat');
    expect(activity.streamedProject, 'proj-1');

    serverMessages = [
      _msg('m9', '{"kind":"plan_progress","plan_id":"pl1","done":["A"]}',
          runId: 'wga_progress_pl1'),
    ];
    activity.controller.add(_event('run.completed', 1)); // không liên quan -> bỏ qua
    activity.controller.add(_event('agent.chat_message', 2));
    await Future<void>.delayed(const Duration(milliseconds: 50));

    expect(c.chatMessages.single['content'], contains('plan_progress'));
    c.startNewChat();
    expect(activity.controller.hasListener, isFalse);
  });
}

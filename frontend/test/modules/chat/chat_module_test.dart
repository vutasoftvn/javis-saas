import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/chat/models/chat_models.dart';
import 'package:frontend/modules/chat/models/data_access_declaration.dart';
import 'package:frontend/modules/chat/services/agent_chat_service.dart';
import 'package:frontend/modules/chat/controllers/chat_controller.dart';
import 'package:frontend/modules/chat/views/chat_view.dart';

import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({
      'workspace_id': 'ws-1',
    });
    Get.reset();
  });

  tearDown(() async {
    // `ChatController.onInit()` gọi `loadConversations()` mà KHÔNG await. Nếu test
    // kết thúc trước khi future đó settle, lời gọi `getConversations()` treo lại sẽ
    // chạy SAU khi tearDown khôi phục `ApiClient.client = realClient` (→ HTTP 400) và
    // nổ ở test chạy kế tiếp dưới dạng "This test failed after it had already
    // completed" — đây chính là nguồn flaky khi chạy full-suite / random order.
    // Dispose controller (Get.reset → onClose) rồi xả hết microtask/timer đang treo
    // TRƯỚC khi trả lại client thật, để future treo hoàn tất trên mockClient.
    Get.reset();
    await Future<void>.delayed(Duration.zero);
    ApiClient.client = realClient;
    ApiClient.clearRuntimeContext();
  });

  group('Chat Models Test', () {
    test('ChatConversation JSON serialization and deserialization', () {
      final json = {
        'id': 'conv-123',
        'workspace_id': 'ws-1',
        'created_by_principal': 'user:1',
        'title': 'Test Chat',
        'active_agent_profile': 'founder_assistant',
        'created_at': '2026-08-22T12:00:00Z',
        'updated_at': '2026-08-22T12:05:00Z',
        'messages': [
          {
            'id': 'msg-1',
            'conversation_id': 'conv-123',
            'role': 'user',
            'content': 'Hello Agent',
            'created_at': '2026-08-22T12:00:00Z',
            'attachments': [
              {
                'id': 'att-1',
                'object_ref': 's3://bucket/file.pdf',
                'media_type': 'application/pdf',
                'file_name': 'file.pdf',
                'size': 2048,
              }
            ],
          }
        ],
      };

      final conv = ChatConversation.fromJson(json);
      expect(conv.id, 'conv-123');
      expect(conv.title, 'Test Chat');
      expect(conv.activeAgentProfile, 'founder_assistant');
      expect(conv.isArchived, isFalse);
      expect(conv.messages.length, 1);
      expect(conv.messages[0].content, 'Hello Agent');
      expect(conv.messages[0].attachments.length, 1);
      expect(conv.messages[0].attachments[0].fileName, 'file.pdf');
    });

    test('ChatApproval JSON model', () {
      final json = {
        'id': 'appr-999',
        'run_id': 'run-1',
        'action': 'transfer_funds',
        'subject': '500 USD',
        'requester': 'finance_agent',
        'status': 'PENDING',
      };

      final appr = ChatApproval.fromJson(json);
      expect(appr.id, 'appr-999');
      expect(appr.action, 'transfer_funds');
      expect(appr.status, 'PENDING');
    });
  });

  group('AgentChatService Test', () {
    test('getConversations does NOT send X-Company-Id header', () async {
      final mockClient = MockClient((request) async {
        // Verify that X-Company-Id header is NOT present
        expect(request.headers.containsKey('X-Company-Id'), isFalse);
        if (request.url.path.contains('/agent/conversations')) {
          return http.Response(
            jsonEncode({
              'items': [
                {
                  'id': 'conv-1',
                  'workspace_id': 'ws-1',
                  'created_by_principal': 'user:1',
                  'title': 'Strategy Session',
                  'created_at': '2026-08-22T12:00:00Z',
                  'updated_at': '2026-08-22T12:00:00Z',
                }
              ],
              'total': 1,
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        return http.Response('Not Found', 404);
      });

      ApiClient.client = mockClient;
      final service = AgentChatService();
      final list = await service.getConversations();
      expect(list.length, 1);
      expect(list[0].id, 'conv-1');
      expect(list[0].title, 'Strategy Session');
    });

    test('sendMessage posts to conversation messages endpoint', () async {
      final mockClient = MockClient((request) async {
        if (request.url.path.contains('/agent/conversations/conv-1/messages')) {
          final body = jsonDecode(request.body);
          expect(body['content'], 'Hello test');
          expect(body['data_access']['categories'], ['NON_PERSONAL']);
          return http.Response(
            jsonEncode({
              'run_id': 'run-100',
              'conversation_id': 'conv-1',
              'status': 'RUNNING',
              'message_id': 'msg-user-1',
            }),
            202,
            headers: {'content-type': 'application/json'},
          );
        }
        return http.Response('Not Found', 404);
      });

      ApiClient.client = mockClient;
      final service = AgentChatService();
      final res = await service.sendMessage(
        'conv-1',
        projectId: 'proj-1',
        content: 'Hello test',
        dataAccess: const DataAccessDeclaration(
          categories: {DataAccessCategory.nonPersonal},
        ),
      );
      expect(res, isNotNull);
      expect(res!['run_id'], 'run-100');
    });

    test('sendMessage serializes explicit data access', () async {
      Map<String, dynamic>? sentJson;
      final mockClient = MockClient((request) async {
        sentJson = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response(
          jsonEncode({
            'run_id': 'run-101',
            'conversation_id': 'conv_1',
            'status': 'RUNNING',
            'message_id': 'msg-user-2',
          }),
          202,
          headers: {'content-type': 'application/json'},
        );
      });

      ApiClient.client = mockClient;
      final service = AgentChatService();
      const declaration = DataAccessDeclaration(
        categories: {DataAccessCategory.businessConfidential},
      );
      await service.sendMessage(
        'conv_1',
        projectId: 'proj-1',
        content: 'Kế hoạch quý',
        dataAccess: declaration,
      );
      expect(sentJson, isNotNull);
      expect(sentJson!['data_access']['categories'], ['BUSINESS_CONFIDENTIAL']);
      expect(sentJson!['project_id'], 'proj-1');
    });

    test('decideApproval posts decision', () async {
      final mockClient = MockClient((request) async {
        if (request.url.path.contains('/agent/approvals/appr-1/decision')) {
          final body = jsonDecode(request.body);
          expect(body['approved'], true);
          return http.Response(
            jsonEncode({
              'approval_id': 'appr-1',
              'status': 'APPROVED',
              'reviewer': 'user:1',
              'decided_at': '2026-08-22T12:00:00Z',
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        return http.Response('Not Found', 404);
      });

      ApiClient.client = mockClient;
      final service = AgentChatService();
      final ok = await service.decideApproval('appr-1', approved: true);
      expect(ok, isTrue);
    });
  });

  group('ChatController & View Test', () {
    testWidgets('ChatView renders header, conversation list and composer', (tester) async {
      final mockClient = MockClient((request) async {
        if (request.url.path == '/agent/conversations') {
          return http.Response(
            jsonEncode({
              'items': [
                {
                  'id': 'conv-1',
                  'workspace_id': 'ws-1',
                  'created_by_principal': 'user:1',
                  'title': 'Test Conversation',
                  'active_agent_profile': 'founder_assistant',
                  'created_at': '2026-08-22T12:00:00Z',
                  'updated_at': '2026-08-22T12:00:00Z',
                  'messages': [],
                }
              ],
              'total': 1,
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (request.url.path.contains('/agent/conversations/conv-1')) {
          return http.Response(
            jsonEncode({
              'id': 'conv-1',
              'company_id': 'comp-1',
              'workspace_id': 'ws-1',
              'created_by_principal': 'user:1',
              'title': 'Test Conversation',
              'active_agent_profile': 'founder_assistant',
              'created_at': '2026-08-22T12:00:00Z',
              'updated_at': '2026-08-22T12:00:00Z',
              'messages': [
                {
                  'id': 'msg-1',
                  'conversation_id': 'conv-1',
                  'role': 'user',
                  'content': 'Welcome to AgentOS',
                  'created_at': '2026-08-22T12:00:00Z',
                }
              ],
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        return http.Response('{}', 200);
      });

      ApiClient.client = mockClient;
      final service = AgentChatService();
      final controller = ChatController(service: service);
      Get.put<ChatController>(controller);

      await tester.pumpWidget(
        const GetMaterialApp(
          home: ChatView(),
        ),
      );
      await tester.pump(const Duration(milliseconds: 100));
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.text('AgentOS Chat'), findsOneWidget);
      expect(find.text('New Chat'), findsOneWidget);
      expect(find.byType(TextField), findsOneWidget);
    });

    testWidgets('personal classification requires a subject reference', (tester) async {
      final mockClient = MockClient((request) async {
        if (request.url.path == '/agent/conversations') {
          return http.Response(
            jsonEncode({'items': [], 'total': 0}),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        return http.Response('{}', 200);
      });

      ApiClient.client = mockClient;
      final service = AgentChatService();
      final controller = ChatController(service: service);
      Get.put<ChatController>(controller);

      // Composer now stacks classification chips + subject field + a
      // blocked-reason line above the message row; give the test surface
      // enough height so this extra content doesn't trip an unrelated
      // RenderFlex overflow in the (fixed-size) test viewport.
      await tester.binding.setSurfaceSize(const Size(800, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        const GetMaterialApp(
          home: ChatView(),
        ),
      );
      await tester.pump(const Duration(milliseconds: 100));
      await tester.pump(const Duration(milliseconds: 100));

      // Select PERSONAL, leave subject blank, then tap Send.
      await tester.tap(find.text('Personal'));
      await tester.pump();

      expect(find.textContaining('subject'), findsOneWidget);

      // Type into the MESSAGE field explicitly (by Key, not `.first`) so
      // the assertion below cannot be confused with the early-return for
      // empty content — content is non-empty here, only the subject
      // reference is missing.
      await tester.enterText(
        find.byKey(const Key('chat_message_field')),
        'Hello',
      );
      expect(controller.textController.text, 'Hello');
      // The subject-reference field (rendered because PERSONAL is
      // selected) must remain untouched.
      expect(controller.dataAccess.value.subjectReference, isNull);

      // The Send icon button is disabled (onPressed: null) while invalid,
      // so tapping it fires nothing — call the controller directly (same
      // codepath `onSubmitted` on the message field uses) to exercise the
      // classification gate itself.
      await controller.sendMessage();
      await tester.pump();

      // Send is blocked specifically due to the missing subject reference
      // (not the unrelated empty-content early return): message content
      // is non-empty, classification is invalid, and the surfaced reason
      // names the subject reference requirement.
      expect(controller.canSendMessage, isFalse);
      expect(controller.messages, isEmpty);
      expect(controller.sendBlockedReason.value, contains('subject'));
    });

    testWidgets('failed send shows retry action; tapping it resends the same content once', (tester) async {
      var sendAttempts = 0;
      String? lastSentContent;

      final mockClient = MockClient((request) async {
        if (request.url.path == '/agent/conversations') {
          return http.Response(
            jsonEncode({
              'items': [
                {
                  'id': 'conv-1',
                  'workspace_id': 'ws-1',
                  'created_by_principal': 'user:1',
                  'title': 'Test Conversation',
                  'active_agent_profile': 'founder_assistant',
                  'created_at': '2026-08-22T12:00:00Z',
                  'updated_at': '2026-08-22T12:00:00Z',
                  'messages': [],
                }
              ],
              'total': 1,
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (request.url.path == '/agent/conversations/conv-1' || request.url.path.contains('/agent/conversations/conv-1')) {
          if (request.method == 'POST' && request.url.path.endsWith('/messages')) {
            sendAttempts += 1;
            final body = jsonDecode(request.body) as Map<String, dynamic>;
            lastSentContent = body['content'] as String?;
            // Fail every attempt (mirrors AgentChatApiException(503) từ backend
            // — profile locale Control Plane tạm không sẵn sàng) để kiểm tra
            // retry KHÔNG auto-resubmit thành công ngầm mà chỉ gọi lại đúng 1 lần
            // mỗi lần user bấm.
            return http.Response(
              jsonEncode({'detail': 'Profile locale unavailable'}),
              503,
              headers: {'content-type': 'application/json'},
            );
          }
          return http.Response(
            jsonEncode({
              'id': 'conv-1',
              'company_id': 'comp-1',
              'workspace_id': 'ws-1',
              'created_by_principal': 'user:1',
              'title': 'Test Conversation',
              'active_agent_profile': 'founder_assistant',
              'created_at': '2026-08-22T12:00:00Z',
              'updated_at': '2026-08-22T12:00:00Z',
              'messages': [],
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        return http.Response('{}', 200);
      });

      ApiClient.client = mockClient;
      final service = AgentChatService();
      final controller = ChatController(service: service);
      Get.put<ChatController>(controller);
      // Task 2 — sendMessage() giờ bắt buộc có Project đang hoạt động.
      controller.activeProjectId.value = 'proj-1';

      await tester.binding.setSurfaceSize(const Size(800, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        const GetMaterialApp(
          home: ChatView(),
        ),
      );
      await tester.pump(const Duration(milliseconds: 100));
      await tester.pump(const Duration(milliseconds: 100));

      // Chọn 1 category để vượt qua data-access gate, rồi gõ nội dung và gửi.
      await tester.tap(find.text('Non-personal'));
      await tester.pump();

      await tester.enterText(find.byKey(const Key('chat_message_field')), 'Please retry this message');
      await controller.sendMessage();
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      // Optimistic message đã bị rollback, spinner tắt, và retry copy hiển thị.
      expect(sendAttempts, 1);
      expect(controller.messages, isEmpty);
      expect(controller.isStreaming.value, isFalse);
      expect(find.byType(CircularProgressIndicator), findsNothing);
      expect(controller.sendBlockedReason.value, isNotEmpty);
      expect(find.text(controller.sendBlockedReason.value), findsOneWidget);
      expect(find.byKey(const Key('chat_retry_button')), findsOneWidget);
      // Text đã gõ được giữ lại trong ô nhập, không bị mất khi gửi thất bại.
      expect(controller.textController.text, 'Please retry this message');

      // Bấm Retry: phải gọi lại sendMessage() đúng 1 lần nữa với cùng nội dung
      // — không auto-resubmit lặp lại nhiều lần.
      await tester.tap(find.byKey(const Key('chat_retry_button')));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(sendAttempts, 2);
      expect(lastSentContent, 'Please retry this message');
    });
  });

  group('ChatController attachment guard', () {
    test('sendMessage rolls back optimistic state when the API rejects the request', () async {
      final mockClient = MockClient((request) async {
        if (request.url.path == '/agent/conversations/conv-1/messages') {
          return http.Response(
            jsonEncode({'detail': 'Profile locale unavailable'}),
            503,
            headers: {'content-type': 'application/json'},
          );
        }
        return http.Response(jsonEncode({'items': [], 'total': 0}), 200);
      });

      ApiClient.client = mockClient;
      final controller = ChatController(service: AgentChatService());
      controller.activeConversation.value = ChatConversation(
        id: 'conv-1',
        workspaceId: 'ws-1',
        createdByPrincipal: 'user:1',
        title: 'Retryable chat',
        createdAt: DateTime.utc(2026),
        updatedAt: DateTime.utc(2026),
      );
      controller.textController.text = 'Please retry this message';
      controller.toggleDataAccessCategory(DataAccessCategory.nonPersonal);
      controller.activeProjectId.value = 'proj-1';

      await controller.sendMessage();

      expect(controller.messages, isEmpty);
      expect(controller.isStreaming.value, isFalse);
      expect(controller.runStatus.value, 'failed');
      expect(controller.textController.text, 'Please retry this message');
      expect(controller.sendBlockedReason.value, isNotEmpty);
    });

    test('sendMessage blocks attachments even with non-empty text content', () async {
      var serviceCalled = false;
      final mockClient = MockClient((request) async {
        serviceCalled = true;
        return http.Response('{}', 200);
      });

      ApiClient.client = mockClient;
      final service = AgentChatService();
      final controller = ChatController(service: service);
      Get.put<ChatController>(controller);

      // Give the composer valid text and a valid classification so the
      // ONLY thing that could block the send is the attachment guard.
      controller.textController.text = 'Hello with attachment';
      controller.toggleDataAccessCategory(DataAccessCategory.nonPersonal);
      expect(controller.canSendMessage, isTrue);

      await controller.sendMessage(
        attachments: [
          ChatAttachment(
            id: 'att-1',
            objectRef: 's3://bucket/file.pdf',
            mediaType: 'application/pdf',
            fileName: 'file.pdf',
            size: 1024,
          ),
        ],
      );

      expect(serviceCalled, isFalse);
      expect(controller.messages, isEmpty);
      expect(controller.sendBlockedReason.value, contains('Attachments'));
    });

    test('sendMessage blocks dispatch when no project is selected (Task 2)', () async {
      var serviceCalled = false;
      final mockClient = MockClient((request) async {
        serviceCalled = true;
        return http.Response('{}', 200);
      });

      ApiClient.client = mockClient;
      final service = AgentChatService();
      final controller = ChatController(service: service);
      Get.put<ChatController>(controller);

      // Valid text + valid classification, but NO active project — the
      // generic chat transport must refuse to dispatch createConversation/
      // sendMessage without one, per Task 2 (Project-scoped Founder Hub).
      controller.textController.text = 'Hello without project';
      controller.toggleDataAccessCategory(DataAccessCategory.nonPersonal);
      expect(controller.canSendMessage, isTrue);
      expect(controller.activeProjectId.value, isNull);

      await controller.sendMessage();

      expect(serviceCalled, isFalse);
      expect(controller.messages, isEmpty);
      expect(controller.sendBlockedReason.value, contains('project'));
    });
  });
}

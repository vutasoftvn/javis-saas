import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:frontend/modules/chat/models/chat_models.dart';
import 'package:frontend/modules/chat/models/data_access_declaration.dart';
import 'package:frontend/modules/chat/services/agent_chat_service.dart';
import 'package:frontend/modules/chat/controllers/chat_controller.dart';
import 'package:frontend/modules/chat/views/chat_view.dart';

import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({
      'auth_token': 'test_jwt_token',
      'workspace_id': 'ws-1',
    });
    Get.reset();
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

      final service = AgentChatService(client: mockClient);
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

      final service = AgentChatService(client: mockClient);
      final res = await service.sendMessage(
        'conv-1',
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

      final service = AgentChatService(client: mockClient);
      const declaration = DataAccessDeclaration(
        categories: {DataAccessCategory.businessConfidential},
      );
      await service.sendMessage(
        'conv_1',
        content: 'Kế hoạch quý',
        dataAccess: declaration,
      );
      expect(sentJson, isNotNull);
      expect(sentJson!['data_access']['categories'], ['BUSINESS_CONFIDENTIAL']);
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

      final service = AgentChatService(client: mockClient);
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

      final service = AgentChatService(client: mockClient);
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

      final service = AgentChatService(client: mockClient);
      final controller = ChatController(service: service);
      Get.put<ChatController>(controller);

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

      await tester.enterText(find.byType(TextField).first, 'Hello');
      await tester.tap(find.byIcon(Icons.send));
      await tester.pump();

      // Send is blocked: no run started, no message appended for lack of
      // a valid classification.
      expect(controller.messages, isEmpty);
    });
  });
}

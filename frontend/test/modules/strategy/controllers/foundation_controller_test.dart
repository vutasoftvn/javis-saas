import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/strategy/controllers/foundation_controller.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-1'});
    // Get.testMode chặn snackbar/dialog thật sự cố tìm overlay context (không có trong unit test).
    Get.testMode = true;
  });

  tearDown(() {
    Get.closeAllSnackbars();
    ApiClient.client = realClient;
    Get.reset();
  });

  group('FoundationController', () {
    group('Initialization', () {
      test('initializes with correct observable states', () {
        TestWidgetsFlutterBinding.ensureInitialized();
        final controller = FoundationController();
        expect(controller.isLoading.value, false);
        expect(controller.isSaving.value, false);
        expect(controller.isGeneratingAi.value, false);
        expect(controller.errorMessage.value, isNull);
        expect(controller.canvases, isEmpty);
        expect(controller.selectedCanvas.value, isNull);
        expect(controller.currentRevision.value, isNull);
        expect(controller.visionController.text, '');
        expect(controller.missionController.text, '');
        expect(controller.valueTitleControllers, hasLength(3));
      });

      test('canApprove returns true for admin role', () {
        final controller = FoundationController();
        controller.role.value = 'admin';
        expect(controller.canApprove, isTrue);
      });

      test('canApprove returns true for owner role', () {
        final controller = FoundationController();
        controller.role.value = 'owner';
        expect(controller.canApprove, isTrue);
      });

      test('canApprove returns false for other roles', () {
        final controller = FoundationController();
        controller.role.value = 'member';
        expect(controller.canApprove, isFalse);
      });

      test('canEdit returns true for draft status', () {
        final controller = FoundationController();
        controller.currentRevision.value = {'status': 'draft'};
        expect(controller.canEdit, isTrue);
      });

      test('canEdit returns true for changes_requested status', () {
        final controller = FoundationController();
        controller.currentRevision.value = {'status': 'changes_requested'};
        expect(controller.canEdit, isTrue);
      });

      test('canEdit returns false for approved status', () {
        final controller = FoundationController();
        controller.currentRevision.value = {'status': 'approved'};
        expect(controller.canEdit, isFalse);
      });

      test('canEdit returns true when no revision', () {
        final controller = FoundationController();
        controller.currentRevision.value = null;
        expect(controller.canEdit, isTrue);
      });
    });

    group('loadCanvases', () {
      test('loads canvases', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path == '/strategy/canvases') {
            // decodeList dùng key 'canvases', không phải 'items'.
            return http.Response(
              jsonEncode({
                'canvases': [
                  {'id': 'canvas-1', 'name': 'Canvas 1'},
                ]
              }),
              200,
            );
          }
          // Accept all other requests (selectCanvas gọi tiếp sau khi có canvas đầu tiên)
          return http.Response('{}', 200);
        });

        final controller = FoundationController();
        await controller.loadCanvases();

        expect(controller.canvases, hasLength(1));
        expect(controller.isLoading.value, false);
      });

      test('handles error gracefully', () async {
        ApiClient.client = MockClient((request) async {
          return http.Response('error', 500);
        });

        final controller = FoundationController();
        await controller.loadCanvases();

        expect(controller.canvases, isEmpty);
        expect(controller.isLoading.value, false);
      });
    });

    group('deleteCanvas', () {
      testWidgets('deletes canvas and clears current selection', (tester) async {
        // deleteCanvas() luôn gọi Get.snackbar khi thành công, cần overlay thật từ GetMaterialApp.
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          if (request.url.path == '/strategy/canvases/canvas-1' && request.method == 'DELETE') {
            return http.Response('{}', 200);
          }
          if (request.url.path == '/strategy/canvases') {
            return http.Response(jsonEncode({'canvases': []}), 200);
          }
          return http.Response('{}', 200);
        });

        final controller = FoundationController();
        controller.selectedCanvas.value = {'id': 'canvas-1'};
        controller.currentRevision.value = {'id': 'rev-1'};

        await controller.deleteCanvas('canvas-1');
        await tester.pump(const Duration(seconds: 4));

        expect(controller.selectedCanvas.value, isNull);
        expect(controller.currentRevision.value, isNull);
        expect(controller.isSaving.value, false);
      });

      testWidgets('shows error for invalid canvas ID', (tester) async {
        // deleteCanvas(null) cũng gọi Get.snackbar (nhánh báo lỗi ID không hợp lệ).
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        final controller = FoundationController();
        await controller.deleteCanvas(null);
        await tester.pump(const Duration(seconds: 4));

        // deleteCanvas trả về sớm trước khi set isSaving — chỉ xác nhận không crash
        // và state không bị thay đổi ngoài ý muốn.
        expect(controller.isSaving.value, false);
        expect(controller.selectedCanvas.value, isNull);
      });
    });

    group('selectCanvas', () {
      test('selects canvas', () async {
        ApiClient.client = MockClient((request) async {
          // Accept all canvas requests
          return http.Response(
            jsonEncode({
              'canvas': {'id': 'canvas-1', 'name': 'Canvas 1'},
              'foundation': {'vision': 'Test vision', 'mission': 'Test mission', 'values': []},
              'active_revision': {'id': 'rev-1'},
              'revisions': []
            }),
            200,
          );
        });

        final controller = FoundationController();
        await controller.selectCanvas('canvas-1');

        expect(controller.selectedCanvas.value, isNotNull);
      });
    });

    group('saveFoundation', () {
      test('saves foundation with vision, mission and values', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path.contains('foundation:save') && request.method == 'POST') {
            final body = jsonDecode(request.body);
            expect(body['vision'], 'Vision');
            expect(body['mission'], 'Mission');
            expect(body['values'], hasLength(3));
            return http.Response(jsonEncode({}), 200);
          }
          if (request.url.path.contains('revisions/rev-1')) {
            return http.Response(
              jsonEncode({
                'id': 'rev-1',
                'foundation': {
                  'vision': 'Vision',
                  'mission': 'Mission',
                  'values': []
                }
              }),
              200,
            );
          }
          return http.Response('{}', 200);
        });

        final controller = FoundationController();
        controller.currentRevision.value = {'id': 'rev-1'};
        controller.visionController.text = 'Vision';
        controller.missionController.text = 'Mission';

        await controller.saveFoundation();

        expect(controller.isSaving.value, false);
      });
    });

    group('submitReview', () {
      test('submits foundation for review', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path.contains('review:submit') && request.method == 'POST') {
            return http.Response(
              jsonEncode({'id': 'rev-1', 'status': 'in_review'}),
              200,
            );
          }
          if (request.url.path.contains('revisions/rev-1')) {
            return http.Response(
              jsonEncode({
                'id': 'rev-1',
                'status': 'in_review',
                'foundation': {'vision': '', 'mission': '', 'values': []}
              }),
              200,
            );
          }
          if (request.url.path.contains('canvas-detail')) {
            return http.Response(
              jsonEncode({
                'canvas': {'id': 'canvas-1'},
                'revisions': []
              }),
              200,
            );
          }
          return http.Response('{}', 200);
        });

        final controller = FoundationController();
        controller.currentRevision.value = {'id': 'rev-1'};
        controller.selectedCanvas.value = {'id': 'canvas-1'};

        await controller.submitReview();

        expect(controller.isSaving.value, false);
      });
    });

    group('approveRevision', () {
      test('approves foundation revision', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path.contains('approve') && request.method == 'POST') {
            return http.Response(
              jsonEncode({'id': 'rev-1', 'status': 'approved'}),
              200,
            );
          }
          if (request.url.path.contains('revisions/rev-1')) {
            return http.Response(
              jsonEncode({
                'id': 'rev-1',
                'status': 'approved',
                'foundation': {'vision': '', 'mission': '', 'values': []}
              }),
              200,
            );
          }
          if (request.url.path.contains('canvas-detail')) {
            return http.Response(
              jsonEncode({
                'canvas': {'id': 'canvas-1'},
                'revisions': []
              }),
              200,
            );
          }
          return http.Response('{}', 200);
        });

        final controller = FoundationController();
        controller.currentRevision.value = {'id': 'rev-1'};
        controller.selectedCanvas.value = {'id': 'canvas-1'};

        await controller.approveRevision();

        expect(controller.isSaving.value, false);
      });
    });

    group('requestChanges', () {
      test('requests changes on revision', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path.contains('request-changes') && request.method == 'POST') {
            final body = jsonDecode(request.body);
            expect(body['reason'], 'Need improvements');
            return http.Response(
              jsonEncode({'id': 'rev-1', 'status': 'changes_requested'}),
              200,
            );
          }
          if (request.url.path.contains('revisions/rev-1')) {
            return http.Response(
              jsonEncode({
                'id': 'rev-1',
                'status': 'changes_requested',
                'foundation': {'vision': '', 'mission': '', 'values': []}
              }),
              200,
            );
          }
          return http.Response('{}', 200);
        });

        final controller = FoundationController();
        controller.currentRevision.value = {'id': 'rev-1'};

        await controller.requestChanges('Need improvements');

        expect(controller.isSaving.value, false);
      });
    });
  });
}

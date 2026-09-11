import 'dart:async';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/network/realtime_service.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:frontend/modules/profile/controllers/profile_controller.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() async {
    Get.reset();
    Get.testMode = true;
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({});
    await SecureStorageService.write('auth_token', 'test-token');
    await SecureStorageService.write('local_session_token', 'test-local-token');
    await SecureStorageService.write('workspace_id', 'ws-test-123');
  });

  tearDown(() {
    ApiClient.client = realClient;
    RealtimeService.disconnect();
    ApiClient.clearRuntimeContext();
  });

  group('RealtimeService Lifecycle & Disconnect Tests', () {
    test('Project-switch discards events from previous project', () async {
      final service = RealtimeService();
      final receivedEvents = <Map<String, dynamic>>[];

      ApiClient.client = MockClient.streaming((request, bodyStream) async {
        final controller = StreamController<List<int>>();
        // Simulate SSE stream with project_id in event data
        controller.add('event: test\n'.codeUnits);
        controller.add('id: 1\n'.codeUnits);
        controller.add('data: {"project_id":"proj_a","message":"data from A"}\n'.codeUnits);
        controller.add('\n'.codeUnits);
        controller.close();
        return http.StreamedResponse(controller.stream, 200);
      });

      // Add listener to capture events
      service.addListener((eventType, data) {
        receivedEvents.add(data);
      });

      // Connect and set active project A
      await service.connectForWorkspace('ws-test-123');
      service.setActiveProject('proj_a');
      await Future<void>.delayed(const Duration(milliseconds: 100));

      // Should receive event from proj_a
      expect(receivedEvents.length, 1);
      expect(receivedEvents[0]['message'], 'data from A');

      // Switch to project B and trigger disconnect/reconnect
      service.setActiveProject('proj_b');

      // Clear received events for next test
      receivedEvents.clear();

      // Mock new SSE stream with proj_a event arriving late
      ApiClient.client = MockClient.streaming((request, bodyStream) async {
        final controller = StreamController<List<int>>();
        controller.add('event: test\n'.codeUnits);
        controller.add('id: 2\n'.codeUnits);
        controller.add('data: {"project_id":"proj_a","message":"late data from A"}\n'.codeUnits);
        controller.add('\n'.codeUnits);
        controller.close();
        return http.StreamedResponse(controller.stream, 200);
      });

      // Reconnect (simulating reconnect after project switch)
      await service.reconnectForTest();
      await Future<void>.delayed(const Duration(milliseconds: 100));

      // Should NOT receive event from proj_a since active is now proj_b
      expect(receivedEvents.length, 0);
    });

    test('disconnect cancels stream and prevents reconnection', () async {
      final service = RealtimeService();
      bool streamOpened = false;

      ApiClient.client = MockClient.streaming((request, bodyStream) async {
        streamOpened = true;
        final controller = StreamController<List<int>>();
        return http.StreamedResponse(controller.stream, 200);
      });

      await service.connect();
      expect(service.isConnected, isTrue);
      expect(streamOpened, isTrue);

      RealtimeService.disconnect();
      expect(service.isConnected, isFalse);
    });

    test('AuthService.logout() calls RealtimeService.disconnect()', () async {
      final service = RealtimeService();
      ApiClient.client = MockClient.streaming((request, bodyStream) async {
        final controller = StreamController<List<int>>();
        return http.StreamedResponse(controller.stream, 200);
      });

      await service.connect();
      expect(service.isConnected, isTrue);

      final authService = AuthService();
      await authService.logout();

      expect(service.isConnected, isFalse);
      expect(await SecureStorageService.read('auth_token'), isNull);
    });

    test('ProfileController.logout() triggers disconnect and navigation', () async {
      final service = RealtimeService();
      ApiClient.client = MockClient.streaming((request, bodyStream) async {
        final controller = StreamController<List<int>>();
        return http.StreamedResponse(controller.stream, 200);
      });

      await service.connect();
      expect(service.isConnected, isTrue);

      final profileController = ProfileController();
      await profileController.logout();

      expect(service.isConnected, isFalse);
    });
  });
}

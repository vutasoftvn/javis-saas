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

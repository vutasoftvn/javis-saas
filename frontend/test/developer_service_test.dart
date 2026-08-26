import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/settings/services/developer_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-1'});
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  group('getDevices', () {
    test('returns the devices list on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/devices');
        return http.Response(
          jsonEncode({
            'devices': [
              {'id': 'dev-1'},
            ],
          }),
          200,
        );
      });

      final devices = await DeveloperService().getDevices();

      expect(devices, hasLength(1));
    });
  });

  group('enrollDevice', () {
    test('posts the enroll payload and returns the created device on 201', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/devices/enroll');
        return http.Response(jsonEncode({'id': 'dev-2'}), 201);
      });

      final device = await DeveloperService().enrollDevice({'name': 'my-mac'});

      expect(device?['id'], 'dev-2');
    });
  });

  group('getJobs', () {
    test('appends the status filter when provided', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.queryParameters['status'], 'running');
        return http.Response(jsonEncode({'jobs': []}), 200);
      });

      await DeveloperService().getJobs(status: 'running');
    });
  });

  group('createJob', () {
    test('posts the job payload and returns the created job on 201', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/devices/jobs');
        return http.Response(jsonEncode({'id': 'job-1'}), 201);
      });

      final job = await DeveloperService().createJob({'title': 'Fix bug'});

      expect(job?['id'], 'job-1');
    });

    test('returns null when workspace_id is missing', () async {
      SharedPreferences.setMockInitialValues({});
      ApiClient.client = MockClient((request) async {
        fail('should not call the API without a workspace_id');
      });

      final job = await DeveloperService().createJob({'title': 'Fix bug'});

      expect(job, isNull);
    });
  });
}

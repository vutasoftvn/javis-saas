import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/strategy/services/founder_service.dart';
import 'package:frontend/modules/strategy/services/strategy_service_base.dart';
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

  group('FounderService', () {
    group('Founder Profile', () {
      test('getFounderProfile returns profile data on success', () async {
        ApiClient.client = MockClient((request) async {
          expect(request.url.path, '/strategy/founder-profile');
          expect(request.url.queryParameters['workspace_id'], 'workspace-1');
          return http.Response(
            jsonEncode({
              'id': 'founder-1',
              'weekly_capacity_hours': 40,
              'max_active_strategic_projects': 3,
            }),
            200,
          );
        });

        final result = await FounderService().getFounderProfile();
        expect(result, isA<Map<String, dynamic>>());
        expect(result['id'], 'founder-1');
        expect(result['weekly_capacity_hours'], 40);
      });

      test('getFounderProfile throws StrategyApiException on error', () async {
        ApiClient.client = MockClient((request) async {
          return http.Response(
            jsonEncode({'detail': 'Founder profile not found'}),
            404,
          );
        });

        expect(
          () => FounderService().getFounderProfile(),
          throwsA(isA<StrategyApiException>()),
        );
      });

      test('updateFounderProfile sends optional parameters', () async {
        ApiClient.client = MockClient((request) async {
          expect(request.method, 'PUT');
          expect(request.url.path, '/strategy/founder-profile');
          final body = jsonDecode(request.body);
          expect(body['weekly_capacity_hours'], 50);
          expect(body['max_active_strategic_projects'], 5);
          return http.Response(
            jsonEncode({
              'id': 'founder-1',
              'weekly_capacity_hours': 50,
              'max_active_strategic_projects': 5,
            }),
            200,
          );
        });

        final result = await FounderService().updateFounderProfile(
          weeklyCapacityHours: 50,
          maxActiveStrategicProjects: 5,
        );
        expect(result['weekly_capacity_hours'], 50);
        expect(result['max_active_strategic_projects'], 5);
      });

      test('updateFounderProfile sends only provided parameters', () async {
        ApiClient.client = MockClient((request) async {
          final body = jsonDecode(request.body);
          expect(body.containsKey('weekly_capacity_hours'), isTrue);
          expect(body['weekly_capacity_hours'], 30);
          return http.Response(
            jsonEncode({'id': 'founder-1', 'weekly_capacity_hours': 30}),
            200,
          );
        });

        await FounderService().updateFounderProfile(weeklyCapacityHours: 30);
      });
    });

    group('CEO Next Actions', () {
      test('getCeoNextActions returns list of actions on success', () async {
        ApiClient.client = MockClient((request) async {
          expect(request.url.path, '/strategy/ceo/next-actions');
          expect(request.url.queryParameters['workspace_id'], 'workspace-1');
          expect(request.url.queryParameters['limit'], '5');
          return http.Response(
            jsonEncode({
              'next_actions': [
                {'id': 'action-1', 'title': 'Action 1'},
                {'id': 'action-2', 'title': 'Action 2'},
              ]
            }),
            200,
          );
        });

        final result = await FounderService().getCeoNextActions();
        expect(result.items, hasLength(2));
        expect(result.items.first['id'], 'action-1');
        expect(result.isFailure, isFalse);
      });

      test('getCeoNextActions respects limit parameter', () async {
        ApiClient.client = MockClient((request) async {
          expect(request.url.queryParameters['limit'], '10');
          return http.Response(jsonEncode({'next_actions': []}), 200);
        });

        await FounderService().getCeoNextActions(limit: 10);
      });

      test('getCeoNextActions returns failure on network error', () async {
        ApiClient.client = MockClient((_) async {
          throw const SocketException('offline');
        });

        final result = await FounderService().getCeoNextActions();
        expect(result.items, isEmpty);
        expect(result.isFailure, isTrue);
      });

      test('evaluateCeoNextActions posts evaluation request', () async {
        ApiClient.client = MockClient((request) async {
          expect(request.method, 'POST');
          expect(request.url.path, '/strategy/ceo/next-actions/evaluate');
          final body = jsonDecode(request.body);
          expect(body['project_id'], 'project-1');
          expect(body['portfolio_id'], 'portfolio-1');
          return http.Response(
            jsonEncode({
              'rankings': [
                {'rank': 1, 'score': 0.9},
              ]
            }),
            200,
          );
        });

        final result = await FounderService().evaluateCeoNextActions(
          projectId: 'project-1',
          portfolioId: 'portfolio-1',
        );
        expect(result.items, hasLength(1));
      });

      test('updateNextActionStatus updates action status', () async {
        ApiClient.client = MockClient((request) async {
          expect(request.method, 'PUT');
          expect(request.url.path, '/strategy/ceo/next-actions/action-1/status');
          final body = jsonDecode(request.body);
          expect(body['status'], 'done');
          return http.Response(
            jsonEncode({'id': 'action-1', 'status': 'done'}),
            200,
          );
        });

        final result = await FounderService().updateNextActionStatus('action-1', 'done');
        expect(result['status'], 'done');
      });
    });

    group('Model Runs & Profiles', () {
      test('getModelRunsAudit returns audit list', () async {
        ApiClient.client = MockClient((request) async {
          expect(request.url.path, '/strategy/model-runs/audit');
          expect(request.url.queryParameters['limit'], '20');
          return http.Response(
            jsonEncode({
              'audits': [
                {'id': 'audit-1', 'model': 'GPT-4'},
              ]
            }),
            200,
          );
        });

        final result = await FounderService().getModelRunsAudit();
        expect(result.items, hasLength(1));
        expect(result.items.first['id'], 'audit-1');
      });

      test('getModelRunsAudit respects limit parameter', () async {
        ApiClient.client = MockClient((request) async {
          expect(request.url.queryParameters['limit'], '50');
          return http.Response(jsonEncode({'audits': []}), 200);
        });

        await FounderService().getModelRunsAudit(limit: 50);
      });

      test('getModelProfiles returns profile list', () async {
        ApiClient.client = MockClient((request) async {
          expect(request.url.path, '/strategy/model-profiles');
          return http.Response(
            jsonEncode({
              'profiles': [
                {
                  'id': 'profile-1',
                  'display_name': 'GPT-4',
                  'temperature': 0.7,
                  'is_active': true,
                }
              ]
            }),
            200,
          );
        });

        final result = await FounderService().getModelProfiles();
        expect(result.items, hasLength(1));
        expect(result.items.first['display_name'], 'GPT-4');
      });

      test('updateModelProfile sends update', () async {
        ApiClient.client = MockClient((request) async {
          expect(request.method, 'PUT');
          expect(request.url.path, '/strategy/model-profiles/profile-1');
          final body = jsonDecode(request.body);
          expect(body['display_name'], 'GPT-4 Updated');
          expect(body['temperature'], 0.9);
          expect(body['is_active'], false);
          return http.Response(
            jsonEncode({
              'id': 'profile-1',
              'display_name': 'GPT-4 Updated',
              'temperature': 0.9,
              'is_active': false,
            }),
            200,
          );
        });

        final result = await FounderService().updateModelProfile(
          'profile-1',
          displayName: 'GPT-4 Updated',
          temperature: 0.9,
          isActive: false,
        );
        expect(result['display_name'], 'GPT-4 Updated');
        expect(result['temperature'], 0.9);
      });
    });
  });
}

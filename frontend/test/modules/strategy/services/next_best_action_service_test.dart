import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/strategy/services/next_best_action_service.dart';
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

  group('NextBestActionService - Action Context', () {
    test('getActionContext returns context data on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/operations/strategy/action-context');
        return http.Response(
          jsonEncode({
            'context': {
              'currentPhase': 'discovery',
              'focusArea': 'market_validation',
            },
          }),
          200,
        );
      });

      final result = await NextBestActionService().getActionContext();

      expect(result, isNotNull);
      expect(result!['currentPhase'], 'discovery');
      expect(result['focusArea'], 'market_validation');
    });

    test('getActionContext returns null when context is not a map', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'context': 'not a map',
          }),
          200,
        );
      });

      final result = await NextBestActionService().getActionContext();

      expect(result, isNull);
    });

    test('getActionContext returns null on error response', () async {
      ApiClient.client = MockClient((request) async => http.Response('server error', 500));

      final result = await NextBestActionService().getActionContext();

      expect(result, isNull);
    });

    test('getActionContext returns null on non-2xx status', () async {
      ApiClient.client = MockClient((request) async => http.Response('error', 500));

      final result = await NextBestActionService().getActionContext();

      expect(result, isNull);
    });

    test('getActionContext returns null when workspace_id is missing', () async {
      SharedPreferences.setMockInitialValues({});

      final result = await NextBestActionService().getActionContext();

      expect(result, isNull);
    });
  });

  group('NextBestActionService - Action Proposals', () {
    test('getActionProposals returns proposals list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/operations/strategy/action-proposals');
        return http.Response(
          jsonEncode({
            'proposals': [
              {'id': 'prop-1', 'title': 'Validate MVP with users', 'priority': 'high'},
            ],
          }),
          200,
        );
      });

      final result = await NextBestActionService().getActionProposals();

      expect(result, hasLength(1));
      expect(result.first['title'], 'Validate MVP with users');
    });

    test('getActionProposals filters by status when provided', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/operations/strategy/action-proposals');
        expect(request.url.queryParameters['status'], 'pending');
        return http.Response(
          jsonEncode({
            'proposals': [
              {'id': 'prop-1', 'status': 'pending'},
            ],
          }),
          200,
        );
      });

      final result = await NextBestActionService().getActionProposals(status: 'pending');

      expect(result, hasLength(1));
    });

    test('getActionProposals returns empty list when proposals key is missing', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(jsonEncode({}), 200);
      });

      final result = await NextBestActionService().getActionProposals();

      expect(result, isEmpty);
    });

    test('getActionProposals returns empty list when proposals is not a list', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({'proposals': 'not a list'}),
          200,
        );
      });

      final result = await NextBestActionService().getActionProposals();

      expect(result, isEmpty);
    });

    test('getActionProposals returns empty list on non-2xx status', () async {
      ApiClient.client = MockClient((request) async => http.Response('error', 500));

      final result = await NextBestActionService().getActionProposals();

      expect(result, isEmpty);
    });

    test('getActionProposals returns empty list when workspace_id missing', () async {
      SharedPreferences.setMockInitialValues({});

      final result = await NextBestActionService().getActionProposals();

      expect(result, isEmpty);
    });

    test('createActionProposal posts payload and returns created proposal', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/operations/strategy/action-proposals');
        final body = jsonDecode(request.body);
        expect(body['title'], 'New action');
        return http.Response(
          jsonEncode({'id': 'prop-2', 'title': 'New action', 'status': 'draft'}),
          201,
        );
      });

      final result = await NextBestActionService().createActionProposal({
        'title': 'New action',
      });

      expect(result, isNotNull);
      expect(result!['id'], 'prop-2');
      expect(result['title'], 'New action');
    });

    test('createActionProposal returns null on error', () async {
      ApiClient.client = MockClient((request) async => http.Response('server error', 500));

      final result = await NextBestActionService().createActionProposal({
        'title': 'New action',
      });

      expect(result, isNull);
    });

    test('createActionProposal returns null when response is not a map', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(jsonEncode('not a map'), 200);
      });

      final result = await NextBestActionService().createActionProposal({
        'title': 'New action',
      });

      expect(result, isNull);
    });

    test('acceptActionProposal posts accept action', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/operations/strategy/action-proposals/prop-1/accept');
        return http.Response(
          jsonEncode({'id': 'prop-1', 'status': 'accepted'}),
          200,
        );
      });

      final result = await NextBestActionService().acceptActionProposal('prop-1');

      expect(result, isNotNull);
      expect(result!['status'], 'accepted');
    });

    test('acceptActionProposal returns null on error', () async {
      ApiClient.client = MockClient((request) async => http.Response('error', 400));

      final result = await NextBestActionService().acceptActionProposal('prop-1');

      expect(result, isNull);
    });
  });

  group('NextBestActionService - Weekly Reviews', () {
    test('getWeeklyReviews returns reviews list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/operations/strategy/weekly-reviews');
        return http.Response(
          jsonEncode({
            'reviews': [
              {'id': 'review-1', 'week': 1, 'score': 8.5},
            ],
          }),
          200,
        );
      });

      final result = await NextBestActionService().getWeeklyReviews();

      expect(result, hasLength(1));
      expect(result.first['week'], 1);
      expect(result.first['score'], 8.5);
    });

    test('getWeeklyReviews returns empty list when reviews key missing', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(jsonEncode({}), 200);
      });

      final result = await NextBestActionService().getWeeklyReviews();

      expect(result, isEmpty);
    });

    test('getWeeklyReviews returns empty list when reviews is not a list', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({'reviews': 'not a list'}),
          200,
        );
      });

      final result = await NextBestActionService().getWeeklyReviews();

      expect(result, isEmpty);
    });

    test('getWeeklyReviews returns empty list on non-2xx status', () async {
      ApiClient.client = MockClient((request) async => http.Response('error', 500));

      final result = await NextBestActionService().getWeeklyReviews();

      expect(result, isEmpty);
    });

    test('getWeeklyReviews returns empty list when workspace_id missing', () async {
      SharedPreferences.setMockInitialValues({});

      final result = await NextBestActionService().getWeeklyReviews();

      expect(result, isEmpty);
    });

    test('createWeeklyReview posts review payload', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/operations/strategy/weekly-reviews');
        final body = jsonDecode(request.body);
        expect(body['week'], 1);
        expect(body['execution_score'], 8.0);
        return http.Response(
          jsonEncode({'id': 'review-1', 'week': 1}),
          201,
        );
      });

      final result = await NextBestActionService().createWeeklyReview({
        'week': 1,
        'execution_score': 8.0,
      });

      expect(result, isNotNull);
      expect(result!['id'], 'review-1');
    });

    test('createWeeklyReview returns null on error', () async {
      ApiClient.client = MockClient((request) async => http.Response('error', 500));

      final result = await NextBestActionService().createWeeklyReview({
        'week': 1,
      });

      expect(result, isNull);
    });

    test('createWeeklyReview returns null when response is not a map', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(jsonEncode('not a map'), 200);
      });

      final result = await NextBestActionService().createWeeklyReview({
        'week': 1,
      });

      expect(result, isNull);
    });

    test('completeWeeklyReview posts completion action', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/operations/strategy/weekly-reviews/review-1/complete');
        return http.Response(
          jsonEncode({'id': 'review-1', 'status': 'completed'}),
          200,
        );
      });

      final result = await NextBestActionService().completeWeeklyReview('review-1');

      expect(result, isNotNull);
      expect(result!['status'], 'completed');
    });

    test('completeWeeklyReview returns null on error', () async {
      ApiClient.client = MockClient((request) async => http.Response('error', 400));

      final result = await NextBestActionService().completeWeeklyReview('review-1');

      expect(result, isNull);
    });
  });
}

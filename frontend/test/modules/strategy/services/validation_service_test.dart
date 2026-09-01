import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/strategy/services/validation_service.dart';
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

  group('ValidationService - Session Management', () {
    test('startSession makes POST request to start endpoint', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/projects/123/validation/session/start');
        final body = jsonDecode(request.body);
        expect(body['initial_topic'], 'CUSTOMER');
        expect(body['interview_mode'], isTrue);
        return http.Response('', 400);
      });

      final session = await ValidationService.startSession(123);
      expect(session, isNull);
    });

    test('startSession allows custom initial topic', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body['initial_topic'], 'PROBLEM');
        return http.Response('', 400);
      });

      await ValidationService.startSession(456, initialTopic: 'PROBLEM');
    });

    test('getSession makes GET request', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/projects/789/validation/session');
        return http.Response('', 400);
      });

      final session = await ValidationService.getSession(789);
      expect(session, isNull);
    });
  });

  group('ValidationService - Chat', () {
    test('sendValidationChat posts message with optional currentTopic', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/projects/123/validation/chat');
        final body = jsonDecode(request.body);
        expect(body['message'], 'Tell me about your customers');
        expect(body['current_topic'], 'CUSTOMER');
        return http.Response('', 400);
      });

      await ValidationService.sendValidationChat(
        123,
        'Tell me about your customers',
        currentTopic: 'CUSTOMER',
      );
    });

    test('sendValidationChat works without currentTopic', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body['message'], 'Hello');
        expect(body.containsKey('current_topic'), isFalse);
        return http.Response('', 400);
      });

      await ValidationService.sendValidationChat(123, 'Hello');
    });
  });

  group('ValidationService - Claims', () {
    test('getClaims makes GET request to claims endpoint', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/projects/123/validation/claims');
        return http.Response('[]', 200);
      });

      final claims = await ValidationService.getClaims(123);
      expect(claims, isA<List>());
    });

    test('getClaims returns empty list on error', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('error', 500);
      });

      final claims = await ValidationService.getClaims(123);
      expect(claims, isEmpty);
    });

    test('confirmClaim posts to confirm endpoint with confidence', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/projects/123/validation/claims/1/confirm');
        final body = jsonDecode(request.body);
        expect(body['confidence'], 0.9);
        return http.Response('', 400);
      });

      await ValidationService.confirmClaim(123, 1, confidence: 0.9);
    });

    test('confirmClaim uses default confidence of 1.0', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body['confidence'], 1.0);
        return http.Response('', 400);
      });

      await ValidationService.confirmClaim(123, 1);
    });

    test('editClaim posts new value with reason', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/projects/123/validation/claims/1/edit');
        final body = jsonDecode(request.body);
        expect(body['reason'], 'Custom reason');
        return http.Response('', 400);
      });

      await ValidationService.editClaim(123, 1, 'Value', reason: 'Custom reason');
    });

    test('editClaim wraps scalar newValue in raw field', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body['new_value'], {'raw': 'string value'});
        return http.Response('', 400);
      });

      await ValidationService.editClaim(123, 1, 'string value');
    });

    test('editClaim sends Map newValue directly', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body['new_value'], {'key': 'value'});
        return http.Response('', 400);
      });

      await ValidationService.editClaim(123, 1, {'key': 'value'});
    });
  });

  group('ValidationService - Hypotheses & Experiments', () {
    test('getHypotheses makes GET request', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/projects/123/validation/hypotheses');
        return http.Response('[]', 200);
      });

      final hypotheses = await ValidationService.getHypotheses(123);
      expect(hypotheses, isA<List>());
    });

    test('getExperiments makes GET request', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/projects/123/validation/experiments');
        return http.Response('[]', 200);
      });

      final experiments = await ValidationService.getExperiments(123);
      expect(experiments, isA<List>());
    });

    test('getEvidence makes GET request', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/projects/123/validation/evidence');
        return http.Response('[]', 200);
      });

      final evidence = await ValidationService.getEvidence(123);
      expect(evidence, isA<List>());
    });

    test('generateHypothesis posts to generate-hypothesis endpoint', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/projects/123/validation/assumptions/5/generate-hypothesis');
        return http.Response('[]', 200);
      });

      await ValidationService.generateHypothesis(123, 5);
    });

    test('recommendExperiment posts to recommend-experiment endpoint', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/projects/123/validation/hypotheses/1/recommend-experiment');
        return http.Response('[]', 200);
      });

      await ValidationService.recommendExperiment(123, 1);
    });
  });

  group('ValidationService - Customer Interactions', () {
    test('getContacts makes GET request', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/projects/123/validation/contacts');
        return http.Response('[]', 200);
      });

      final contacts = await ValidationService.getContacts(123);
      expect(contacts, isA<List>());
    });

    test('getContacts returns empty list on error', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('error', 500);
      });

      final contacts = await ValidationService.getContacts(123);
      expect(contacts, isEmpty);
    });

    test('getInterviews makes GET request', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/projects/123/validation/interviews');
        return http.Response('[]', 200);
      });

      final interviews = await ValidationService.getInterviews(123);
      expect(interviews, isA<List>());
    });

    test('getQuotes makes GET request', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/projects/123/validation/quotes');
        return http.Response('[]', 200);
      });

      final quotes = await ValidationService.getQuotes(123);
      expect(quotes, isA<List>());
    });
  });

  group('ValidationService - Problem Discovery', () {
    test('getProblemScorecard makes GET request', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/projects/123/validation/problem-scorecard');
        return http.Response('', 400);
      });

      final scorecard = await ValidationService.getProblemScorecard(123);
      expect(scorecard, isNull);
    });

    test('updateProblemScorecard posts all score fields', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/projects/123/validation/problem-scorecard');
        final body = jsonDecode(request.body);
        expect(body['frequency_score'], 8);
        expect(body['severity_score'], 9);
        expect(body['alternatives_score'], 7);
        expect(body['wtp_score'], 8);
        expect(body['market_potential_score'], 9);
        expect(body['notes'], 'Good market');
        return http.Response('', 400);
      });

      await ValidationService.updateProblemScorecard(
        123,
        frequencyScore: 8,
        severityScore: 9,
        alternativesScore: 7,
        wtpScore: 8,
        marketPotentialScore: 9,
        notes: 'Good market',
      );
    });

    test('getRoleCoverage makes GET request', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/projects/123/validation/role-coverage');
        return http.Response('', 400);
      });

      await ValidationService.getRoleCoverage(123);
    });

    test('getSolutionBiasRisk makes GET request', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/projects/123/validation/solution-bias');
        return http.Response('', 400);
      });

      await ValidationService.getSolutionBiasRisk(123);
    });
  });

  group('ValidationService - Analysis & Reviews', () {
    test('getStateVector makes GET request', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/projects/123/validation/state-vector');
        return http.Response('', 400);
      });

      await ValidationService.getStateVector(123);
    });

    test('getRiskMatrix makes GET request', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/projects/123/validation/risk-matrix');
        return http.Response('', 400);
      });

      await ValidationService.getRiskMatrix(123);
    });

    test('getRiskiestAssumptions uses custom limit parameter', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/projects/123/validation/assumptions/riskiest');
        expect(request.url.queryParameters['limit'], '10');
        return http.Response('[]', 200);
      });

      await ValidationService.getRiskiestAssumptions(123, limit: 10);
    });

    test('performAiReview posts to review endpoint', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/projects/123/validation/hypotheses/1/review/ai');
        return http.Response('', 400);
      });

      await ValidationService.performAiReview(123, 1);
    });

    test('getLatestReview makes GET request', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/projects/123/validation/reviews/latest');
        return http.Response('', 200);
      });

      await ValidationService.getLatestReview(123);
    });
  });

  group('ValidationService - Next Best Action', () {
    test('getNextBestAction makes GET request', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/projects/123/validation/next-best-action');
        return http.Response('', 400);
      });

      await ValidationService.getNextBestAction(123);
    });
  });

  group('ValidationService - Error Handling', () {
    test('methods handle malformed JSON gracefully', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('not json', 200);
      });

      final session = await ValidationService.startSession(123);
      expect(session, isNull);

      final claims = await ValidationService.getClaims(123);
      expect(claims, isEmpty);
    });

    test('methods handle empty response bodies', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('', 200);
      });

      final review = await ValidationService.getLatestReview(123);
      expect(review, isNull);

      final scorecard = await ValidationService.getProblemScorecard(123);
      expect(scorecard, isNull);
    });
  });
}

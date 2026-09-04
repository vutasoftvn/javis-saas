import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/skills/services/skill_registry_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({
      'workspace_id': 'ws-1',
    });
  });

  tearDown(() {
    ApiClient.client = http.Client();
  });

  group('ApiClient Endpoint Normalization for Skill Registry', () {
    test('normalizes /skills to /agent/skills and resolves to agentOsBaseUrl (:8000)', () {
      final uri1 = ApiClient.resolveUri('/skills');
      expect(uri1.path, '/agent/skills');
      expect(uri1.port, 8000);

      final uri2 = ApiClient.resolveUri('/skills/sync-built-in');
      expect(uri2.path, '/agent/skills/sync-built-in');
      expect(uri2.port, 8000);

      final uri3 = ApiClient.resolveUri('/agent/skills/marketing-positioning/promote');
      expect(uri3.path, '/agent/skills/marketing-positioning/promote');
      expect(uri3.port, 8000);
    });
  });

  group('SkillRegistryService Lifecycle & Methods', () {
    test('syncBuiltInSkills calls POST /agent/skills/sync-built-in', () async {
      String? capturedPath;
      String? capturedMethod;

      ApiClient.client = MockClient((request) async {
        capturedPath = request.url.path;
        capturedMethod = request.method;
        return http.Response(
          jsonEncode({
            'synced_count': 1,
            'skills': [
              {
                'skill_id': 'marketing.positioning',
                'version': '1.1.0',
                'definition_hash': 'hash-123',
                'published': true,
              }
            ]
          }),
          200,
        );
      });

      final service = SkillRegistryService();
      final result = await service.syncBuiltInSkills();
      expect(capturedPath, '/agent/skills/sync-built-in');
      expect(capturedMethod, 'POST');
      expect(result.length, 1);
      expect(result[0]['skill_id'], 'marketing.positioning');
    });

    test('listSkills sends domain and status query params', () async {
      String? capturedPath;
      Map<String, String>? capturedQuery;

      ApiClient.client = MockClient((request) async {
        capturedPath = request.url.path;
        capturedQuery = request.url.queryParameters;
        return http.Response(
          jsonEncode([
            {
              'id': 'marketing.positioning',
              'version': '1.1.0',
              'status': 'PUBLISHED',
              'domain': 'marketing',
              'definition_hash': 'hash-123',
            }
          ]),
          200,
        );
      });

      final service = SkillRegistryService();
      final result = await service.listSkills(domain: 'marketing', status: 'PUBLISHED');
      expect(capturedPath, '/agent/skills');
      expect(capturedQuery?['domain'], 'marketing');
      expect(capturedQuery?['status'], 'PUBLISHED');
      expect(result.length, 1);
    });

    test('createCandidate sends required candidate payload', () async {
      Map<String, dynamic>? capturedBody;

      ApiClient.client = MockClient((request) async {
        capturedBody = jsonDecode(request.body);
        return http.Response(
          jsonEncode({
            'candidate_id': 'cand-1',
            'skill_id': 'custom-drafter',
            'status': 'CANDIDATE',
          }),
          201,
        );
      });

      final service = SkillRegistryService();
      final result = await service.createCandidate(
        name: 'Custom Drafter',
        domain: 'marketing',
        instructions: 'Write SOP.',
        toolPermissions: ['web.search'],
      );

      expect(capturedBody?['name'], 'Custom Drafter');
      expect(capturedBody?['domain'], 'marketing');
      expect(result['status'], 'CANDIDATE');
    });

    test('promoteSkill sends approvedBy and approvalReason', () async {
      Map<String, dynamic>? capturedBody;
      String? capturedPath;

      ApiClient.client = MockClient((request) async {
        capturedPath = request.url.path;
        capturedBody = jsonDecode(request.body);
        return http.Response(
          jsonEncode({
            'skill_id': 'custom-drafter',
            'status': 'PUBLISHED',
            'approved_by': 'founder_admin',
            'approval_reason': 'Passed all benchmark evals',
          }),
          200,
        );
      });

      final service = SkillRegistryService();
      final result = await service.promoteSkill(
        skillId: 'custom-drafter',
        approvedBy: 'founder_admin',
        approvalReason: 'Passed all benchmark evals',
      );

      expect(capturedPath, '/agent/skills/custom-drafter/promote');
      expect(capturedBody?['approved_by'], 'founder_admin');
      expect(capturedBody?['approval_reason'], 'Passed all benchmark evals');
      expect(result['status'], 'PUBLISHED');
    });

    test('deprecateSkill and recordFeedback call respective endpoints', () async {
      String? capturedPath;

      ApiClient.client = MockClient((request) async {
        capturedPath = request.url.path;
        return http.Response(jsonEncode({'status': 'ok'}), 200);
      });

      final service = SkillRegistryService();
      await service.deprecateSkill('custom-drafter', reason: 'Outdated');
      expect(capturedPath, '/agent/skills/custom-drafter/deprecate');

      await service.recordFeedback(skillId: 'custom-drafter', success: true, rating: 5);
      expect(capturedPath, '/agent/skills/custom-drafter/feedback');
    });
  });

  group('SkillRegistryService Error Mapping', () {
    test('throws SkillAuthException on 401/403', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'Unauthorized'}), 401);
      });

      final service = SkillRegistryService();
      expect(() => service.listSkills(), throwsA(isA<SkillAuthException>()));
    });

    test('throws SkillNotFoundException on 404', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'Skill not found'}), 404);
      });

      final service = SkillRegistryService();
      expect(() => service.getSkill('unknown-skill'), throwsA(isA<SkillNotFoundException>()));
    });

    test('throws SkillConflictException on 409', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'Hash conflict'}), 409);
      });

      final service = SkillRegistryService();
      expect(() => service.syncBuiltInSkills(), throwsA(isA<SkillConflictException>()));
    });

    test('throws SkillValidationException on 422', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'Missing approved_by'}), 422);
      });

      final service = SkillRegistryService();
      expect(
        () => service.promoteSkill(skillId: 'draft', approvedBy: '', approvalReason: ''),
        throwsA(isA<SkillValidationException>()),
      );
    });
  });
}

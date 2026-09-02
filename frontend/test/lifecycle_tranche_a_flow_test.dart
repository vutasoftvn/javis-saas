import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/models/stage_model.dart';
import 'package:frontend/modules/skills/services/skill_registry_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({
      'workspace_id': 'ws-tranche-a',
    });
  });

  tearDown(() {
    ApiClient.client = http.Client();
  });

  group('COSA Lifecycle Tranche A Operating Model Flow Test', () {
    test('verifies canonical P0–P6 stage definitions in Flutter ProjectStage', () {
      expect(ProjectStage.values.length, 7);
      expect(ProjectStage.p0Discovery.wireValue, 'P0_DISCOVERY');
      expect(ProjectStage.p1ProblemValidation.wireValue, 'P1_PROBLEM_VALIDATION');
      expect(ProjectStage.p2SolutionValidation.wireValue, 'P2_SOLUTION_VALIDATION');
      expect(ProjectStage.p3BuildValidate.wireValue, 'P3_BUILD_VALIDATE');
      expect(ProjectStage.p4GoToMarket.wireValue, 'P4_GO_TO_MARKET');
      expect(ProjectStage.p5OperateGrowth.wireValue, 'P5_OPERATE_GROWTH');
      expect(ProjectStage.p6ScaleGovern.wireValue, 'P6_SCALE_GOVERN');

      // Canonical serialization & deserialization
      expect(ProjectStage.fromString('P0_DISCOVERY'), ProjectStage.p0Discovery);
      expect(ProjectStage.fromString('P2_SOLUTION_VALIDATION'), ProjectStage.p2SolutionValidation);
      expect(ProjectStage.fromString('UNKNOWN_STAGE'), ProjectStage.p1ProblemValidation);
    });

    test('verifies SkillRegistryService correctly parses Tranche A governance fields', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode([
            {
              'id': 'lifecycle.context-resolver',
              'version': '1.0.0',
              'status': 'PUBLISHED',
              'domain': 'lifecycle',
              'definition_hash': 'd2cd448f9012ae55f12d20b40315b79f517136fc8b55577f651dd4e36d2bcb98',
              'project_stages': ['P0_DISCOVERY', 'P1_PROBLEM_VALIDATION'],
              'autonomy_ceiling': 'L0_OBSERVE',
              'side_effect_class': 'R',
              'min_source_refs': 0,
              'eval_suite': 'evals/lifecycle/context-resolver.yaml',
            }
          ]),
          200,
        );
      });

      final service = SkillRegistryService();
      final skills = await service.listSkills();

      expect(skills.length, 1);
      final skill = skills.first;
      expect(skill['id'], 'lifecycle.context-resolver');
      expect(skill['project_stages'], contains('P0_DISCOVERY'));
      expect(skill['autonomy_ceiling'], 'L0_OBSERVE');
      expect(skill['side_effect_class'], 'R');
      expect(skill['min_source_refs'], 0);
    });
  });
}

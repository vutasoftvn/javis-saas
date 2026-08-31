// frontend/test/workspace_company_identity_model_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/workspace_company_identity_model.dart';

void main() {
  group('WorkspaceCompanyIdentity', () {
    test('fromJson parses vision/mission/coreValues from camelCase keys', () {
      final model = WorkspaceCompanyIdentity.fromJson({
        'id': 'ws_1',
        'vision': 'Vision text',
        'mission': 'Mission text',
        'coreValues': 'Values text',
      });

      expect(model.workspaceId, 'ws_1');
      expect(model.vision, 'Vision text');
      expect(model.mission, 'Mission text');
      expect(model.coreValues, 'Values text');
    });

    test('isComplete is true only when all three fields are non-empty', () {
      const complete = WorkspaceCompanyIdentity(
        workspaceId: 'ws_1',
        vision: 'v',
        mission: 'm',
        coreValues: 'c',
      );
      expect(complete.isComplete, isTrue);

      const missingMission = WorkspaceCompanyIdentity(
        workspaceId: 'ws_1',
        vision: 'v',
        mission: '   ',
        coreValues: 'c',
      );
      expect(missingMission.isComplete, isFalse);

      const nullFields = WorkspaceCompanyIdentity(workspaceId: 'ws_1');
      expect(nullFields.isComplete, isFalse);
    });
  });
}

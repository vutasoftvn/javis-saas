import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/onboarding/services/company_identity_draft_parser.dart';

void main() {
  group('parseCompanyIdentityDraft', () {
    test('parses well-formed VISION/MISSION/VALUES sections', () {
      const text = 'VISION: Tro thanh so 1.\n\n'
          'MISSION: Trao quyen cho founder.\n\n'
          'VALUES: Minh bach, Toc do.';

      final draft = parseCompanyIdentityDraft(text);

      expect(draft.vision, 'Tro thanh so 1.');
      expect(draft.mission, 'Trao quyen cho founder.');
      expect(draft.coreValues, 'Minh bach, Toc do.');
    });

    test('is case-insensitive on the section labels', () {
      const text = 'vision: A\nMission: B\nValues: C';
      final draft = parseCompanyIdentityDraft(text);
      expect(draft.vision, 'A');
      expect(draft.mission, 'B');
      expect(draft.coreValues, 'C');
    });

    test('returns null fields when labels are missing (malformed reply)', () {
      const text = 'Day la mot cau tra loi tu do khong theo dinh dang.';
      final draft = parseCompanyIdentityDraft(text);
      expect(draft.vision, isNull);
      expect(draft.mission, isNull);
      expect(draft.coreValues, isNull);
    });
  });
}

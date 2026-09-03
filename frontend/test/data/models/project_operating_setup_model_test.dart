import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/project_operating_setup_model.dart';

void main() {
  test('fromJson đọc roundStartDate', () {
    final s = ProjectOperatingSetup.fromJson({
      'projectId': 'p1',
      'workspaceId': 'w1',
      'status': 'ACTIVE',
      'roundStartDate': '2026-09-08T00:00:00.000Z',
    });
    expect(s.roundStartDate, DateTime.utc(2026, 9, 8));
  });

  test('fromJson roundStartDate null -> null', () {
    final s = ProjectOperatingSetup.fromJson({
      'projectId': 'p1',
      'workspaceId': 'w1',
      'status': 'IN_PROGRESS',
    });
    expect(s.roundStartDate, isNull);
  });

  test('draft.toJson phát roundStartDate ISO khi có', () {
    final d = ProjectOperatingSetupDraft(
      roundStartDate: DateTime.utc(2026, 9, 8),
      firstWeekActions: const [],
    );
    expect(d.toJson()['roundStartDate'], '2026-09-08T00:00:00.000Z');
  });

  test('draft.toJson bỏ roundStartDate khi null', () {
    final d = ProjectOperatingSetupDraft(firstWeekActions: const []);
    expect(d.toJson().containsKey('roundStartDate'), isFalse);
  });
}

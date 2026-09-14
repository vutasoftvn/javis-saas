import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/lifecycle/lifecycle_service.dart';

void main() {
  test('workspace lifecycle path uses /identity/workspaces/:id/lifecycle', () {
    expect(
      LifecycleService.pathFor(LifecycleEntityType.workspace, 'ws1'),
      '/identity/workspaces/ws1/lifecycle',
    );
  });

  test('project lifecycle path uses /operations/projects/:id/lifecycle', () {
    expect(
      LifecycleService.pathFor(LifecycleEntityType.project, 'p1'),
      '/operations/projects/p1/lifecycle',
    );
  });
}

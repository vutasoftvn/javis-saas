import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/strategy/controllers/project_orchestration_controller.dart';
import 'package:frontend/modules/strategy/views/project_kickoff_view.dart';
import 'package:frontend/modules/strategy/views/project_stage_workspace_view.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.reset();
  });

  testWidgets('ProjectKickoffView shows the AI-proposed draft stages before any are confirmed', (WidgetTester tester) async {
    final controller = Get.put(ProjectOrchestrationController());
    controller.roadmapDraft.value = {
      'stages': [
        {'title': 'Validate demand', 'hypothesis': 'SMEs will pre-commit before build'},
        {'title': 'Build MVP', 'hypothesis': 'A thin slice converts pilots'},
      ],
    };

    await tester.pumpWidget(
      const GetMaterialApp(home: ProjectKickoffView(projectId: '100')),
    );

    expect(find.text('Validate demand'), findsOneWidget);
    expect(find.text('Build MVP'), findsOneWidget);
    expect(find.text('Xác nhận Roadmap'), findsOneWidget);
    // No stage has been confirmed/activated yet.
    expect(find.text('Kích hoạt'), findsNothing);
  });

  testWidgets('legal/regulated review requirement is visible before activation', (WidgetTester tester) async {
    final controller = Get.put(ProjectOrchestrationController());
    controller.serviceAssessments.assignAll([
      {
        'id': 'a1',
        'disposition': 'REQUIRED',
        'reason': 'Regulated compliance checklist needed',
        'risk_level': 'REGULATED',
        'execution_mode': 'MANUAL',
        'professional_review_required': true,
        'status': 'DRAFT',
      },
      {
        'id': 'a2',
        'disposition': 'OPTIONAL',
        'reason': 'Nice-to-have GTM support',
        'risk_level': 'LOW',
        'execution_mode': 'AI_ASSISTED',
        'professional_review_required': false,
        'status': 'DRAFT',
      },
    ]);

    await tester.pumpWidget(
      const GetMaterialApp(
        home: ProjectStageWorkspaceView(projectId: '100', stageId: 's1'),
      ),
    );

    expect(find.text('Cần chuyên gia phê duyệt'), findsOneWidget);
  });
}

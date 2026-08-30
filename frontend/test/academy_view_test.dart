import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/academy/models/academy_models.dart';
import 'package:frontend/modules/academy/views/widgets/academy_widgets.dart';

void main() {
  group('Academy Widget Tests — Boundary Isolation (Task 5)', () {
    testWidgets('SyntheticDisclaimerBanner renders always-visible disclaimer', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SyntheticDisclaimerBanner(
              disclaimer:
                  'Kết quả mô phỏng học tập – KHÔNG phải evidence thực.',
            ),
          ),
        ),
      );

      expect(find.text('Học tập / Mô phỏng'), findsOneWidget);
      expect(find.textContaining('KHÔNG phải evidence thực'), findsOneWidget);

      // Banner cannot be dismissed — no close button or dismiss action
      expect(find.byIcon(Icons.close), findsNothing);
    });

    testWidgets('SimulationWorkspace renders result with mandatory disclaimer and no pass-stage button', (tester) async {
      final result = AcademySimulationResult(
        attemptId: 'sim_abc123',
        artifactRef: 'academy-artifact://p0_discovery_v1/sim_abc123',
        synthetic: true,
        disclaimer: 'Đây là kết quả mô phỏng học tập, không phải evidence sản xuất.',
        scenarioVersion: '1.0.0',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: SimulationWorkspace(result: result),
            ),
          ),
        ),
      );

      // Disclaimer must always be visible
      expect(find.textContaining('Học tập / Mô phỏng'), findsOneWidget);
      expect(find.textContaining('không phải evidence'), findsOneWidget);

      // Simulation result shows attempt ID
      expect(find.textContaining('sim_abc123'), findsOneWidget);

      // Must NOT show "pass stage", "apply evidence", or lifecycle action buttons
      expect(find.textContaining('Chuyển giai đoạn'), findsNothing);
      expect(find.textContaining('Tạo evidence'), findsNothing);
      expect(find.textContaining('Áp dụng vào dự án'), findsNothing);
    });

    testWidgets('LessonProgressCard shows completed state without lifecycle reference', (tester) async {
      final lesson = AcademyLesson(
        id: 'lesson-p0-01',
        moduleId: 'module-001',
        title: 'Phỏng vấn khám phá vấn đề',
        order: 1,
        practiceType: 'simulation',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: LessonProgressCard(
              lesson: lesson,
              isCompleted: true,
              onTap: () {},
            ),
          ),
        ),
      );

      expect(find.text('Phỏng vấn khám phá vấn đề'), findsOneWidget);
      expect(find.byIcon(Icons.check_circle_rounded), findsOneWidget);

      // No lifecycle stage labels visible
      expect(find.textContaining('P0_DISCOVERY'), findsNothing);
      expect(find.textContaining('Gate'), findsNothing);
    });

    testWidgets('AcademySimulationResult.isValidAcademyArtifact returns true for academy:// refs', (tester) async {
      const result = AcademySimulationResult(
        attemptId: 'sim_001',
        artifactRef: 'academy-artifact://p0/sim_001',
        synthetic: true,
        disclaimer: 'Synthetic',
        scenarioVersion: '1.0.0',
      );

      expect(result.isValidAcademyArtifact, isTrue);
    });

    testWidgets('AcademyTemplateExportResult.isTemplateDraft is true for academy_template_draft kind', (tester) async {
      const exportResult = AcademyTemplateExportResult(
        id: 'tmpl_001',
        kind: 'academy_template_draft',
        academySourceRef: 'academy-artifact://p0/sim_001',
        disclaimer: 'Not evidence',
        body: {},
      );

      expect(exportResult.isTemplateDraft, isTrue);
    });
  });
}

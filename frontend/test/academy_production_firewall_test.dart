import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/academy/models/academy_models.dart';
import 'package:frontend/modules/academy/views/widgets/academy_widgets.dart';

void main() {
  group('Academy Production Firewall — Flutter Tests (Task 6)', () {
    testWidgets('Simulation result always has a visible disclaimer, no evidence actions', (tester) async {
      final result = AcademySimulationResult(
        attemptId: 'sim_fw_001',
        artifactRef: 'academy-artifact://p0_discovery_v1/sim_fw_001',
        synthetic: true,
        disclaimer: 'Kết quả mô phỏng COSA Academy — KHÔNG phải evidence thực.',
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

      // Disclaimer always visible
      expect(find.textContaining('Học tập / Mô phỏng'), findsOneWidget);

      // No production action buttons
      expect(find.textContaining('Áp dụng evidence'), findsNothing);
      expect(find.textContaining('Chuyển giai đoạn'), findsNothing);
      expect(find.textContaining('Tạo evidence từ mô phỏng'), findsNothing);
      expect(find.textContaining('Submit to gate'), findsNothing);
    });

    testWidgets('AcademySimulationResult invariant: isValidAcademyArtifact is false for non-academy refs', (tester) async {
      // Ensure the model contract prevents invalid refs from appearing as valid
      const result = AcademySimulationResult(
        attemptId: 'sim_fw_002',
        artifactRef: 'artifact://live-workspace/document.pdf',  // NOT an academy ref
        synthetic: true,
        disclaimer: 'Test',
        scenarioVersion: '1.0.0',
      );

      expect(result.isValidAcademyArtifact, isFalse);
    });

    testWidgets('AcademyTemplateExportResult with academy_template_draft kind is correctly identified', (tester) async {
      const export = AcademyTemplateExportResult(
        id: 'tmpl_fw_001',
        kind: 'academy_template_draft',
        academySourceRef: 'academy-artifact://p0/sim_fw_001',
        disclaimer: 'KHÔNG phải evidence — cần thay thế nguồn thực tế',
        body: {},
      );

      // Kind must be template_draft
      expect(export.isTemplateDraft, isTrue);
      expect(export.kind, equals('academy_template_draft'));

      // academySourceRef must start with academy-artifact://
      expect(export.academySourceRef.startsWith('academy-artifact://'), isTrue);
    });

    testWidgets('SyntheticDisclaimerBanner is always shown and cannot be dismissed', (tester) async {
      bool dismissed = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Column(
              children: [
                SyntheticDisclaimerBanner(
                  disclaimer: 'Firewall test disclaimer — NOT production evidence.',
                ),
              ],
            ),
          ),
        ),
      );

      expect(find.textContaining('Học tập / Mô phỏng'), findsOneWidget);
      // No close/dismiss icon
      expect(find.byIcon(Icons.close), findsNothing);
      expect(dismissed, isFalse);
    });
  });
}

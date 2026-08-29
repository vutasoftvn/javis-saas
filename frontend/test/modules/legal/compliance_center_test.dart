import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/data/models/ai_compliance_models.dart';
import 'package:frontend/modules/legal/controllers/ai_compliance_controller.dart';
import 'package:frontend/modules/legal/services/ai_compliance_service.dart';
import 'package:frontend/modules/legal/views/widgets/compliance_center_panel.dart';

class MockAiComplianceService extends AiComplianceService {
  @override
  Future<AiComplianceCenterData?> getComplianceCenter() async {
    return const AiComplianceCenterData(
      deployments: [
        AiComplianceDeployment(
          id: 'dep_test_1',
          status: 'APPROVED_FOR_USE',
          ownerName: 'Founder Test',
          assessmentExpiresAt: '2026-12-31',
          providerStatus: 'ACTIVE',
        ),
      ],
      recentIncidents: [
        AiIncidentSummary(
          id: 'inc_1',
          severity: 'HIGH',
          status: 'OPEN',
          summary: 'Model drift detected',
          createdAt: '2026-08-30',
        ),
      ],
      activeCount: 1,
      incidentCount: 1,
    );
  }
}

void main() {
  setUp(() {
    Get.reset();
  });

  testWidgets('renders compliance center panel with deployments and incidents', (tester) async {
    Get.put(AiComplianceController(service: MockAiComplianceService()));

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: ComplianceCenterPanel(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Trung tâm Tuân thủ AI (AI Compliance Center)'), findsOneWidget);
    expect(find.text('dep_test_1'), findsOneWidget);
    expect(find.text('APPROVED_FOR_USE'), findsOneWidget);
    expect(find.text('Model drift detected'), findsOneWidget);
  });
}

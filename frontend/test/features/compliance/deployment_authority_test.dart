import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/data/models/ai_compliance_models.dart';
import 'package:frontend/modules/legal/controllers/ai_compliance_controller.dart';
import 'package:frontend/modules/legal/services/ai_compliance_service.dart';
import 'package:frontend/modules/legal/views/widgets/compliance_center_panel.dart';

class MockAuthorityComplianceService extends AiComplianceService {
  @override
  Future<AiComplianceCenterData?> getComplianceCenter() async {
    return const AiComplianceCenterData(
      deployments: [
        AiComplianceDeployment(
          id: 'dep_auth_draft',
          status: 'ASSESSED',
          ownerName: 'Tech Lead',
          currentAssessmentId: 'assess_123',
          assessmentExpiresAt: '2027-01-01',
          providerStatus: 'ACTIVE',
          createdByMemberId: '1001',
          accountableMemberId: '1002',
          policyVersion: 2,
        ),
        AiComplianceDeployment(
          id: 'dep_auth_approved',
          status: 'APPROVED_FOR_USE',
          ownerName: 'Tech Lead',
          currentAssessmentId: 'assess_456',
          assessmentExpiresAt: '2027-01-01',
          providerStatus: 'ACTIVE',
          createdByMemberId: '1001',
          accountableMemberId: '1002',
          reviewerMemberId: '1003',
          approvedByMemberId: '9999',
          policyVersion: 2,
          approvedVersion: 1,
        ),
      ],
      recentIncidents: [],
      activeCount: 1,
      incidentCount: 0,
    );
  }
}

void main() {
  setUp(() {
    Get.reset();
  });

  testWidgets('displays workforce authority fields and approval action in compliance center', (tester) async {
    Get.put(AiComplianceController(service: MockAuthorityComplianceService()));

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: ComplianceCenterPanel(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Verify draft deployment displays creator and accountable member
    expect(find.text('dep_auth_draft'), findsOneWidget);
    expect(find.text('Người tạo: Member 1001'), findsNWidgets(2));
    expect(find.text('Chịu trách nhiệm: Member 1002'), findsNWidgets(2));
    expect(find.text('Phê duyệt thẩm quyền'), findsOneWidget);

    // Verify approved deployment displays approved by and version
    expect(find.text('dep_auth_approved'), findsOneWidget);
    expect(find.text('Đã duyệt bởi: Member 9999 (v1)'), findsOneWidget);
  });
}

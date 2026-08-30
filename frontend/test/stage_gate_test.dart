import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/stage_gate_model.dart';
import 'package:frontend/data/models/stage_model.dart';
import 'package:frontend/modules/hologram_hub/widgets/stage_gate/premature_alert_banner.dart';
import 'package:frontend/modules/hologram_hub/widgets/stage_gate/stage_gate_audit_modal.dart';

void main() {
  group('COSA Stage Gate Models Test', () {
    test('AuditStatus enum parsing', () {
      expect(AuditStatus.fromString('APPROVED'), AuditStatus.approved);
      expect(AuditStatus.fromString('CONDITIONALLY_APPROVED'), AuditStatus.conditionallyApproved);
      expect(AuditStatus.fromString('REJECTED'), AuditStatus.rejected);
      expect(AuditStatus.approved.labelVi, contains('Approved'));
    });

    test('AlertSeverity enum parsing', () {
      expect(AlertSeverity.fromString('CRITICAL'), AlertSeverity.critical);
      expect(AlertSeverity.fromString('WARNING'), AlertSeverity.warning);
      expect(AlertSeverity.fromString('INFO'), AlertSeverity.info);
    });

    test('StageGateAuditModel deserialization from JSON', () {
      final json = {
        'id': 999,
        'workspace_id': 1001,
        'project_id': 2001,
        'from_stage': 'P1_PROBLEM_VALIDATION',
        'to_stage': 'P2_SOLUTION_VALIDATION',
        'readiness_score': 0.85,
        'audit_status': 'APPROVED',
        'passed_criteria': [
          {
            'id': 'P1_PROBLEM_EVIDENCE',
            'title': 'Xác thực nỗi đau khách hàng',
            'description': 'Đã có 2 giả định nỗi đau đạt chuẩn',
            'is_met': true,
          }
        ],
        'missing_criteria': [],
        'detected_risks': [],
        'audited_by_agent': 'Stage Gate Auditor Agent',
        'recommendation_note': 'Đủ điều kiện chuyển giai đoạn',
        'created_at': '2026-08-18T10:00:00Z',
      };

      final model = StageGateAuditModel.fromJson(json);
      expect(model.id, 999);
      expect(model.fromStage, 'P1_PROBLEM_VALIDATION');
      expect(model.toStage, 'P2_SOLUTION_VALIDATION');
      expect(model.readinessScore, 0.85);
      expect(model.auditStatus, AuditStatus.approved);
      expect(model.passedCriteria.length, 1);
      expect(model.passedCriteria.first.isMet, true);
    });
  });

  group('COSA Stage Gate Widgets Test', () {
    testWidgets('PrematureAlertBanner renders warning title and message', (WidgetTester tester) async {
      final alert = PrematureAlertModel(
        id: 1,
        workspaceId: 1001,
        projectId: 2001,
        currentStage: 'P1_PROBLEM_VALIDATION',
        ruleCode: 'NO_PAID_ADS_IN_EARLY_STAGE',
        severity: AlertSeverity.critical,
        title: 'Rủi ro Đốt Tiền Quảng Cáo Sớm',
        message: 'Không nên chạy quảng cáo trước khi đạt Problem/Solution Fit.',
        isDismissed: false,
        createdAt: DateTime.now(),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: PrematureAlertBanner(
              alerts: [alert],
              onDismiss: (_) {},
            ),
          ),
        ),
      );

      expect(find.text('Rủi ro Đốt Tiền Quảng Cáo Sớm'), findsOneWidget);
      expect(find.text('CRITICAL'), findsOneWidget);
      expect(find.textContaining('Không nên chạy quảng cáo'), findsOneWidget);
    });

    testWidgets('StageGateAuditModal renders Readiness Score % and Passed Criteria', (WidgetTester tester) async {
      final audit = StageGateAuditModel(
        id: 999,
        workspaceId: 1001,
        projectId: 2001,
        fromStage: 'P1_PROBLEM_VALIDATION',
        toStage: 'P2_SOLUTION_VALIDATION',
        readinessScore: 0.80,
        auditStatus: AuditStatus.approved,
        passedCriteria: [
          StageGateCriteriaModel(
            id: 'P1_EVIDENCE',
            title: 'Bằng chứng thực tế E2+',
            description: 'Đã tích lũy đủ bằng chứng',
            isMet: true,
          ),
        ],
        missingCriteria: [],
        detectedRisks: [],
        auditedByAgent: 'Stage Gate Auditor Agent',
        recommendationNote: 'Dự án đủ điều kiện nâng cấp.',
        createdAt: DateTime.now(),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: StageGateAuditModal(
              projectId: 2001,
              currentStage: ProjectStage.p1ProblemValidation,
              audit: audit,
              onRunAudit: () {},
              onApplyTransition: (_) {},
            ),
          ),
        ),
      );

      expect(find.text('80%'), findsOneWidget);
      expect(find.text('Đủ Điều Kiện Nâng Cấp (Approved)'), findsOneWidget);
      expect(find.text('Nâng Cấp Stage'), findsOneWidget);
    });
  });
}

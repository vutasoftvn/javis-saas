import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/ai_compliance_models.dart';

void main() {
  group('AiComplianceModels', () {
    test('AiComplianceDeployment.fromJson parses canonical server fields without inventing data', () {
      final json = {
        'id': 'dep-100',
        'systemVersionId': 'sys-ver-1',
        'status': 'APPROVED_FOR_USE',
        'ownerName': 'Founder 123',
        'currentAssessmentId': 'assess-50',
        'assessmentExpiresAt': '2027-01-01T00:00:00Z',
        'providerStatus': 'APPROVED',
        'mode': 'ADVISORY_ONLY',
        'allowedCapabilities': ['model.input', 'retrieval.read'],
      };

      final dep = AiComplianceDeployment.fromJson(json);
      expect(dep.id, 'dep-100');
      expect(dep.systemVersionId, 'sys-ver-1');
      expect(dep.status, 'APPROVED_FOR_USE');
      expect(dep.ownerName, 'Founder 123');
      expect(dep.currentAssessmentId, 'assess-50');
      expect(dep.assessmentExpiresAt, '2027-01-01T00:00:00Z');
      expect(dep.providerStatus, 'APPROVED');
      expect(dep.mode, 'ADVISORY_ONLY');
      expect(dep.allowedCapabilities, ['model.input', 'retrieval.read']);
    });

    test('AiIncidentSummary.fromJson parses canonical server fields', () {
      final json = {
        'id': 'inc-99',
        'deploymentId': 'dep-100',
        'severity': 'CRITICAL',
        'status': 'RESOLVED',
        'summary': 'PII leakage in tool response',
        'createdAt': '2026-08-30T10:00:00Z',
      };

      final inc = AiIncidentSummary.fromJson(json);
      expect(inc.id, 'inc-99');
      expect(inc.deploymentId, 'dep-100');
      expect(inc.severity, 'CRITICAL');
      expect(inc.status, 'RESOLVED');
      expect(inc.summary, 'PII leakage in tool response');
      expect(inc.createdAt, '2026-08-30T10:00:00Z');
    });

    test('AiComplianceCenterData.fromJson maps canonical arrays directly', () {
      final json = {
        'workspaceId': 'ws-123',
        'activeCount': 2,
        'incidentCount': 1,
        'deployments': [
          {
            'id': 'dep-1',
            'systemVersionId': 'v1',
            'status': 'APPROVED_FOR_USE',
            'ownerName': 'Founder 1',
            'currentAssessmentId': 'a1',
            'assessmentExpiresAt': '2027-01-01T00:00:00Z',
            'providerStatus': 'APPROVED',
            'mode': 'ADVISORY_ONLY',
            'allowedCapabilities': <String>[],
          },
          {
            'id': 'dep-2',
            'systemVersionId': 'v2',
            'status': 'APPROVED_FOR_USE',
            'ownerName': 'Founder 1',
            'currentAssessmentId': 'a2',
            'assessmentExpiresAt': '2027-01-01T00:00:00Z',
            'providerStatus': 'APPROVED',
            'mode': 'ADVISORY_ONLY',
            'allowedCapabilities': <String>[],
          },
        ],
        'incidents': [
          {
            'id': 'inc-1',
            'deploymentId': 'dep-1',
            'severity': 'LOW',
            'status': 'OPEN',
            'summary': 'Minor audit note',
            'createdAt': '2026-08-30T00:00:00Z',
          }
        ],
      };

      final data = AiComplianceCenterData.fromJson(json);
      expect(data.activeCount, 2);
      expect(data.incidentCount, 1);
      expect(data.deployments.length, 2);
      expect(data.recentIncidents.length, 1);
      expect(data.recentIncidents.first.id, 'inc-1');
    });
  });
}

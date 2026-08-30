import '../../../core/network/workspace_scoped_service.dart';
import '../../../data/models/ai_compliance_models.dart';

class AiComplianceService extends WorkspaceService {
  Future<AiComplianceCenterData?> getComplianceCenter() async {
    final wId = await stringWorkspaceId();
    if (wId == null || wId.isEmpty) return null;
    final data = await getJson('/finance-legal/ai-compliance/center');
    if (data is Map) {
      return AiComplianceCenterData.fromJson(Map<String, dynamic>.from(data));
    }
    return null;
  }

  Future<bool> suspendDeployment(String deploymentId, {required String rationale}) async {
    final res = await postJson('/finance-legal/ai-compliance/deployments/$deploymentId/suspend', {
      'rationale': rationale,
    });
    return res != null;
  }

  Future<bool> resumeDeployment(String deploymentId, {required String rationale}) async {
    final res = await postJson('/finance-legal/ai-compliance/deployments/$deploymentId/resume', {
      'rationale': rationale,
    });
    return res != null;
  }

  Future<bool> approveDeployment(
    String deploymentId, {
    required String assessmentId,
    required String rationale,
    required String expiresAt,
  }) async {
    final res = await postJson('/finance-legal/ai-compliance/deployments/$deploymentId/approve', {
      'assessmentId': assessmentId,
      'rationale': rationale,
      'expiresAt': expiresAt,
    });
    return res != null;
  }

  Future<bool> reportIncident({
    required String deploymentId,
    required String severity,
    required String summary,
    String incidentType = 'COMPLIANCE_BREACH',
  }) async {
    final res = await postJson('/finance-legal/ai-compliance/incidents', {
      'deploymentId': deploymentId,
      'severity': severity,
      'incidentType': incidentType,
      'summary': summary,
    });
    return res != null;
  }
}

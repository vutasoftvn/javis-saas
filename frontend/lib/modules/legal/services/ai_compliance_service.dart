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

  Future<bool> suspendDeployment(String deploymentId, {required String reason}) async {
    final res = await postJson('/finance-legal/ai-deployments/$deploymentId/suspend', {
      'reason': reason,
    });
    return res != null;
  }

  Future<bool> resumeDeployment(String deploymentId, {required String reason}) async {
    final res = await postJson('/finance-legal/ai-deployments/$deploymentId/resume', {
      'reason': reason,
    });
    return res != null;
  }

  Future<bool> approveDeployment(String deploymentId, {required String rationale}) async {
    final res = await postJson('/finance-legal/ai-deployments/$deploymentId/approve', {
      'rationale': rationale,
    });
    return res != null;
  }

  Future<bool> reportIncident({
    required String deploymentId,
    required String severity,
    required String summary,
  }) async {
    final res = await postJson('/finance-legal/ai-incidents', {
      'deploymentId': deploymentId,
      'severity': severity,
      'summary': summary,
    });
    return res != null;
  }
}

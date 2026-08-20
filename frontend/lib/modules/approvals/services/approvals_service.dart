import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:get/get.dart';
import 'package:frontend/core/controllers/company_scope_controller.dart';
import '../../../data/models/approval_model.dart';

class ApprovalsService {
  Future<String?> _getWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('workspace_id');
  }

  String _appendScopeParams(String url) {
    if (Get.isRegistered<CompanyScopeController>()) {
      final scope = Get.find<CompanyScopeController>();
      final hasQuery = url.contains('?');
      var prefix = hasQuery ? '&' : '?';
      
      if (scope.operatingUnitId.value != null) {
        url += '${prefix}operating_unit_id=${scope.operatingUnitId.value}';
        prefix = '&';
      }
      if (scope.offeringId.value != null) {
        url += '${prefix}offering_id=${scope.offeringId.value}';
        prefix = '&';
      }
      if (scope.initiativeId.value != null) {
        url += '${prefix}initiative_id=${scope.initiativeId.value}';
      }
    }
    return url;
  }

  /// Lấy danh sách các phiếu chờ duyệt dạng typed `List<ApprovalItemModel>`
  Future<List<ApprovalItemModel>> getApprovalsList({String? requiredRole, String? status}) async {
    final raw = await getApprovals(requiredRole: requiredRole, status: status);
    return raw.map((item) {
      if (item is Map<String, dynamic>) {
        return ApprovalItemModel.fromJson(item);
      }
      return ApprovalItemModel.fromJson(Map<String, dynamic>.from(item as Map));
    }).toList();
  }

  /// Lấy danh sách thô từ Agent Platform Control Plane
  Future<List<dynamic>> getApprovals({String? requiredRole, String? status}) async {
    final List<String> queryParts = [];
    if (requiredRole != null) queryParts.add('required_role=$requiredRole');
    if (status != null) queryParts.add('status=$status');
    final roleQuery = queryParts.isNotEmpty ? '?${queryParts.join('&')}' : '';

    final response = await ApiClient.get(_appendScopeParams('/workforce/approvals$roleQuery'));
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data is List ? data : (data['approvals'] ?? []);
    }

    // Fallback workflow approvals
    final workspaceId = await _getWorkspaceId();
    if (workspaceId != null) {
      final statusParam = status != null ? '&status=$status' : '';
      final fbResp = await ApiClient.get(_appendScopeParams('/workflows/approvals?workspace_id=$workspaceId$statusParam'));
      if (fbResp.statusCode == 200) {
        final data = jsonDecode(fbResp.body) as Map<String, dynamic>;
        return data['approvals'] ?? [];
      }
    }
    return [];
  }

  /// Chấp thuận phiếu duyệt (Approve)
  Future<bool> approve(dynamic approvalId, {String? comment}) async {
    final response = await ApiClient.post(
      '/workforce/approvals/$approvalId/approve',
      body: {'comment': comment},
    );
    if (response.statusCode == 200) return true;

    // Fallback workflow step
    final workspaceId = await _getWorkspaceId();
    if (workspaceId != null) {
      final fb = await ApiClient.post('/workflows/steps/$approvalId/approve?workspace_id=$workspaceId');
      return fb.statusCode == 200;
    }
    return false;
  }

  /// Từ chối phiếu duyệt (Reject)
  Future<bool> reject(dynamic approvalId, {String? reason}) async {
    final response = await ApiClient.post(
      '/workforce/approvals/$approvalId/reject',
      body: {'comment': reason ?? 'Rejected by founder'},
    );
    if (response.statusCode == 200) return true;

    // Fallback workflow step
    final workspaceId = await _getWorkspaceId();
    if (workspaceId != null) {
      final fb = await ApiClient.post('/workflows/steps/$approvalId/reject?workspace_id=$workspaceId');
      return fb.statusCode == 200;
    }
    return false;
  }

  /// Yêu cầu làm lại kèm phản hồi hướng dẫn (Request Revision)
  Future<bool> requestRevision(dynamic approvalId, {required String feedback}) async {
    final response = await ApiClient.post(
      '/workforce/approvals/$approvalId/request-revision',
      body: {'comment': feedback},
    );
    return response.statusCode == 200;
  }

  // Legacy step compatibility
  Future<bool> approveStep(String stepId) => approve(stepId);
  Future<bool> rejectStep(String stepId) => reject(stepId);
}

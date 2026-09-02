import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_endpoints.g.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/network/workspace_scoped_service.dart';
import '../../../data/models/approval_model.dart';

class ApprovalsService extends WorkspaceService {
  ApprovalsService({MvpRequestClient? client, http.Client? httpClient})
      : _client = client ?? MvpRequestClient(httpClient: httpClient);

  // Task 6 — `list`/`decide` là interface truthful-state mới, đi qua
  // `MvpRequestClient` + endpoint canonical `/agent/workforce/approvals`
  // (xem `FounderCommandCenterController`, fix-review 2026-09-02 I-1):
  // `/agent/approvals` cũ (dùng bởi các phương thức legacy bên dưới) là stub
  // KHÔNG được mount trong `apps/cosa/api/app.py`, luôn trả 404 — tiếp tục
  // gọi nó rồi "sửa" cách hiển thị lỗi sẽ chỉ khiến Approvals tab hiện trạng
  // thái lỗi vĩnh viễn dù backend thật vẫn hoạt động tốt.
  final MvpRequestClient _client;

  List<Map<String, dynamic>> _asMapList(Object? json) {
    if (json is List) {
      return json.whereType<Map<String, dynamic>>().toList();
    }
    if (json is Map<String, dynamic>) {
      final items = json['items'] ?? json['approvals'];
      if (items is List) {
        return items.whereType<Map<String, dynamic>>().toList();
      }
    }
    return const [];
  }

  /// Lấy danh sách approval typed, trả `ApiResult` thật — 401/403/5xx/timeout/
  /// malformed body đều thành `ApiFailure`, KHÔNG BAO GIỜ âm thầm co về `[]`
  /// (đúng bug mà lát dọc Task 6 này sửa).
  Future<ApiResult<List<ApprovalItemModel>>> list({String? status}) {
    return _client.request<List<ApprovalItemModel>>(
      MvpEndpoint.workforceApprovalList,
      query: status != null ? {'status': status} : null,
      decode: (json) => _asMapList(json).map(ApprovalItemModel.fromJson).toList(),
    );
  }

  /// Quyết định approve/reject qua endpoint canonical, trả `ApiResult` —
  /// caller (controller) chỉ được coi là thành công khi nhận `ApiSuccess`
  /// thật, không suy diễn từ absence-of-exception.
  Future<ApiResult<ApprovalItemModel>> decide(
    String approvalId, {
    required bool approved,
    String? reason,
  }) {
    return _client.request<ApprovalItemModel>(
      MvpEndpoint.workforceApprovalDecision,
      pathParams: {'approvalId': approvalId},
      body: {
        'approved': approved,
        'reason': ?reason,
      },
      decode: (json) => ApprovalItemModel.fromJson(json as Map<String, dynamic>),
    );
  }

  /// Lấy danh sách các phiếu chờ duyệt dạng typed `List<ApprovalItemModel>` từ AgentOS
  Future<List<ApprovalItemModel>> getApprovalsList({String? requiredRole, String? status}) async {
    try {
      final response = await ApiClient.get('/agent/approvals');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final items = data is List ? data : (data['items'] ?? data['approvals'] ?? []);
        return (items as List).map((item) {
          if (item is Map<String, dynamic>) {
            return ApprovalItemModel.fromJson(item);
          }
          return ApprovalItemModel.fromJson(Map<String, dynamic>.from(item as Map));
        }).toList();
      }
    } catch (e) {
      debugPrint('[ApprovalsService] getApprovalsList error: $e');
    }
    return [];
  }

  /// Alias getApprovals giữ tương thích
  Future<List<dynamic>> getApprovals({String? requiredRole, String? status}) async {
    final list = await getApprovalsList(requiredRole: requiredRole, status: status);
    return list.map((e) => e.toJson()).toList();
  }

  /// Chấp thuận phiếu duyệt (Approve) qua AgentOS Decision API
  Future<bool> approve(dynamic approvalId, {String? comment}) async {
    try {
      final response = await ApiClient.post(
        '/agent/approvals/$approvalId/decision',
        body: {'approved': true, 'reason': comment ?? 'Approved by founder'},
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('[ApprovalsService] approve error: $e');
      return false;
    }
  }

  /// Từ chối phiếu duyệt (Reject) qua AgentOS Decision API
  Future<bool> reject(dynamic approvalId, {String? reason}) async {
    try {
      final response = await ApiClient.post(
        '/agent/approvals/$approvalId/decision',
        body: {'approved': false, 'reason': reason ?? 'Rejected by founder'},
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('[ApprovalsService] reject error: $e');
      return false;
    }
  }

  /// Yêu cầu làm lại kèm phản hồi hướng dẫn (Request Revision)
  Future<bool> requestRevision(dynamic approvalId, {required String feedback}) async {
    return reject(approvalId, reason: 'Revision requested: $feedback');
  }

  // Legacy step compatibility
  Future<bool> approveStep(String stepId) => approve(stepId);
  Future<bool> rejectStep(String stepId) => reject(stepId);
}

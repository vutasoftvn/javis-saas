import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/network/api_client.dart';

class ConnectorsService {
  Future<String?> _getWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('workspace_id');
  }

  Future<List<dynamic>> getConnectors() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];

    final response = await ApiClient.get('/connectors/?workspace_id=$workspaceId');
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return data['connectors'] ?? [];
    }
    return [];
  }

  Future<Map<String, dynamic>?> createConnector(String name, Map<String, dynamic> config) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return null;

    final response = await ApiClient.post(
      '/connectors/?workspace_id=$workspaceId',
      body: {
        'name': name,
        'config_jsonb': config,
      },
    );
    
    if (response.statusCode == 201) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  Future<bool> deleteConnector(String id) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return false;

    final response = await ApiClient.delete(
      '/connectors/$id?workspace_id=$workspaceId',
    );
    
    return response.statusCode == 200;
  }

  // --- Google Workspace OAuth2 ---

  /// Trạng thái thật của kết nối Gmail.
  ///
  /// `connected` chỉ true khi workspace có refresh token dùng được. Bản ghi kiểu cũ (chỉ
  /// có email người dùng gõ tay) trả về `needs_reconnect` để UI nói đúng việc phải làm
  /// thay vì khoe "Đã kết nối" rồi chat không đọc nổi thư nào.
  Future<Map<String, dynamic>?> getGoogleStatus() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return null;

    final response = await ApiClient.get(
      '/connectors/google/status?workspace_id=$workspaceId',
    );
    if (response.statusCode != 200) return null;
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  /// Trả về URL màn hình đồng ý của Google để mở bằng trình duyệt ngoài.
  Future<String?> startGoogleOAuth({String? loginHint}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return null;

    final hint = (loginHint != null && loginHint.isNotEmpty)
        ? '&login_hint=${Uri.encodeQueryComponent(loginHint)}'
        : '';
    final response = await ApiClient.post(
      '/connectors/google/oauth/start?workspace_id=$workspaceId$hint',
      body: {},
    );
    if (response.statusCode != 200) {
      final detail = jsonDecode(response.body)['detail'];
      throw Exception(detail ?? 'Không mở được đăng nhập Google');
    }
    return jsonDecode(response.body)['authorize_url'] as String?;
  }

  // --- Thư AI soạn, chờ người duyệt ---

  Future<List<dynamic>> getEmailApprovals({String? sessionId}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];

    final scope = sessionId != null ? '&session_id=$sessionId' : '';
    final response = await ApiClient.get(
      '/connectors/email-approvals?workspace_id=$workspaceId$scope',
    );
    if (response.statusCode != 200) return [];
    return jsonDecode(response.body)['approvals'] ?? [];
  }

  Future<String?> decideEmailApproval(String approvalId, {required bool approve}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return 'Chưa xác định được workspace';

    final action = approve ? 'approve' : 'reject';
    final response = await ApiClient.post(
      '/connectors/email-approvals/$approvalId/$action?workspace_id=$workspaceId',
      body: {},
    );
    if (response.statusCode == 200) return null;
    try {
      return jsonDecode(response.body)['detail'] as String?;
    } catch (_) {
      return 'Thao tác thất bại';
    }
  }

  // --- Zalo Agent MCP QR Flow ---

  Future<Map<String, dynamic>?> startZaloQr() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return null;

    final response = await ApiClient.post(
      '/connectors/zalo/sessions',
      body: {
        'workspace_id': workspaceId,
      },
    );

    if (response.statusCode == 202) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  Future<Map<String, dynamic>?> getZaloQrStatus(String sid) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return null;
    final response = await ApiClient.get('/connectors/zalo/sessions/$sid?workspace_id=$workspaceId');
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  Future<bool> cancelZaloQr(String sid) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return false;
    final response = await ApiClient.post('/connectors/zalo/sessions/$sid/cancel?workspace_id=$workspaceId', body: {});
    return response.statusCode == 200;
  }
}

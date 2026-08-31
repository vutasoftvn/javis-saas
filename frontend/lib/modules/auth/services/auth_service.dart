import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/realtime_service.dart';
import '../../../core/services/secure_storage_service.dart';

class WorkspaceSummary {
  final String workspaceId;
  final String? name;
  final String roleId;
  final String status;

  /// M5 §6 — hiển thị trên workspace picker khi platform trả kèm (nullable khi
  /// endpoint chưa cung cấp).
  final String? runtimeMode; // LOCAL_ONLY | REMOTE_ACCESS | CLOUD_CONTINUITY
  final String? presenceStatus; // ONLINE | OFFLINE | DEGRADED
  final DateTime? lastHeartbeatAt;

  const WorkspaceSummary({
    required this.workspaceId,
    required this.name,
    required this.roleId,
    required this.status,
    this.runtimeMode,
    this.presenceStatus,
    this.lastHeartbeatAt,
  });

  factory WorkspaceSummary.fromJson(Map<String, dynamic> json) {
    final hb =
        (json['lastHeartbeatAt'] ?? json['last_heartbeat_at']) as String?;
    return WorkspaceSummary(
      workspaceId: json['workspaceId'].toString(),
      name: json['name'] as String?,
      roleId: json['role'] as String? ?? 'member',
      status: json['status'] as String? ?? 'active',
      runtimeMode: (json['runtimeMode'] ?? json['runtime_mode']) as String?,
      presenceStatus:
          (json['presenceStatus'] ??
                  json['presence_status'] ??
                  json['presence'])
              as String?,
      lastHeartbeatAt: (hb != null && hb.isNotEmpty)
          ? DateTime.tryParse(hb)?.toUtc()
          : null,
    );
  }
}

class AuthResult {
  final bool success;
  final String? errorMessage;
  final String? token;
  final String? companyId;
  final List<WorkspaceSummary>? workspaces;
  final Map<String, dynamic>? user;
  final List<Map<String, dynamic>>? rawWorkspaces;

  const AuthResult({
    required this.success,
    this.errorMessage,
    this.token,
    this.companyId,
    this.workspaces,
    this.user,
    this.rawWorkspaces,
  });
}

/// control_plane (Central) la nguon su that cho danh tinh - dang ky/dang
/// nhap BAT BUOC online tren control_plane truoc, sau do sync xuong backend
/// local (javis) de lay 1 local JWT dung cho moi API local khac. Local
/// KHONG con dang ky/dang nhap doc lap bang email+password nua.
class AuthService {
  static String? _cachedToken;

  static bool get isAuthenticated =>
      _cachedToken != null && _cachedToken!.isNotEmpty;

  static Future<void> init() async {
    await SecureStorageService.migrateFromSharedPreferences();
    // M1 §1 — ưu tiên local session token; fallback token chung cũ.
    _cachedToken =
        await SecureStorageService.read('local_session_token') ??
        await SecureStorageService.read('auth_token');
  }

  static void setCachedToken(String? token) {
    _cachedToken = token;
  }

  /// Xac thuc token dang cache voi server. Tra ve true (con hop le), false
  /// (chac chan het han/khong hop le - 401) hoac null (khong xac dinh duoc,
  /// vd loi mang/server) - phan biet 3 trang thai nay de main() khong dang
  /// xuat oan khi chi la mat mang, nhung van chan duoc token het han vao
  /// thang hub truoc khi kip xac thuc (xem HubAuthMixin.ensureAuthenticated).
  static Future<bool?> validateCachedToken() async {
    if (!isAuthenticated) return false;
    try {
      final response = await ApiClient.get('/auth/me');
      if (response.statusCode == 200) return true;
      if (response.statusCode == 401) return false;
      return null;
    } catch (e) {
      debugPrint('validateCachedToken error: $e');
      return null;
    }
  }

  // ── Buoc 1: xac thuc voi control_plane (bat buoc online) ──────────────────

  /// Dang nhap tren control_plane bang email/phone + password. Token tra ve
  /// la platform_access_token TAM THOI - chua phai auth_token cua app, phai
  /// di qua syncFromPlatform() (sau khi da chon company neu can) moi co
  /// local JWT thuc su dung cho cac API local khac.
  Future<AuthResult> loginPlatform(String identifier, String password) async {
    try {
      final response = await ApiClient.post(
        '/platform/auth/sessions',
        requiresAuth: false,
        body: {'username': identifier, 'password': password},
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final token = data['access_token'] as String?;
        if (token == null) {
          return const AuthResult(
            success: false,
            errorMessage: 'Phản hồi không hợp lệ từ máy chủ',
          );
        }
        final userData = data['user'] as Map<String, dynamic>?;
        final rawWs = (data['workspaces'] as List<dynamic>?)
            ?.map((e) => e as Map<String, dynamic>)
            .toList();
        return AuthResult(
          success: true,
          token: token,
          user: userData,
          rawWorkspaces: rawWs,
        );
      } else if (response.statusCode == 401) {
        return const AuthResult(
          success: false,
          errorMessage: 'Email/Số điện thoại hoặc mật khẩu không chính xác',
        );
      }
      return AuthResult(
        success: false,
        errorMessage:
            'Đăng nhập không thành công (mã lỗi ${response.statusCode})',
      );
    } catch (e) {
      debugPrint('loginPlatform error: $e');
      return const AuthResult(
        success: false,
        errorMessage: 'Lỗi kết nối đến máy chủ. Vui lòng kiểm tra lại mạng.',
      );
    }
  }

  /// Đăng ký trên control_plane bằng email + password + workspaceName (hoặc companyName).
  Future<AuthResult> registerPlatform({
    required String email,
    required String password,
    required String displayName,
    String? workspaceName,
    String? companyName,
    String? joinCompanyId,
  }) async {
    try {
      final wsName = workspaceName ?? companyName;
      final response = await ApiClient.post(
        '/platform/auth/register',
        requiresAuth: false,
        body: {
          'email': email,
          'password': password,
          'full_name': displayName,
          'workspace_name': ?wsName,
          'company_name': ?companyName,
          if (joinCompanyId != null)
            'join_company_id': int.tryParse(joinCompanyId) ?? joinCompanyId,
        },
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final token = data['access_token'] as String?;
        final wsId =
            (data['platform_workspace_id'] ?? data['company_id']) as String?;
        if (token == null) {
          return const AuthResult(
            success: false,
            errorMessage: 'Phản hồi không hợp lệ từ máy chủ',
          );
        }
        final userData = data['user'] as Map<String, dynamic>?;
        final rawWs = (data['workspaces'] as List<dynamic>?)
            ?.map((e) => e as Map<String, dynamic>)
            .toList();
        return AuthResult(
          success: true,
          token: token,
          companyId: wsId,
          user: userData,
          rawWorkspaces: rawWs,
        );
      } else if (response.statusCode == 409) {
        return const AuthResult(
          success: false,
          errorMessage: 'Email này đã được đăng ký',
        );
      } else if (response.statusCode == 404) {
        return const AuthResult(
          success: false,
          errorMessage: 'Workspace không tồn tại',
        );
      } else if (response.statusCode == 422) {
        try {
          final data = jsonDecode(response.body);
          final detail = data['detail'];
          if (detail is List && detail.isNotEmpty) {
            final msg = detail[0]['msg'] ?? 'Dữ liệu không hợp lệ';
            return AuthResult(success: false, errorMessage: msg.toString());
          }
        } catch (_) {}
        return const AuthResult(
          success: false,
          errorMessage: 'Dữ liệu đăng ký không hợp lệ',
        );
      }
      return AuthResult(
        success: false,
        errorMessage:
            'Đăng ký không thành công (mã lỗi ${response.statusCode})',
      );
    } catch (e) {
      debugPrint('registerPlatform error: $e');
      return const AuthResult(
        success: false,
        errorMessage: 'Lỗi kết nối đến máy chủ. Vui lòng kiểm tra lại mạng.',
      );
    }
  }

  /// Tao company moi tren control_plane cho platform user hien tai.
  Future<AuthResult> createCompany({
    required String platformToken,
    required String companyName,
  }) async {
    try {
      final url = ApiClient.resolveUri('/platform/auth/companies/create');
      final response = await ApiClient.client.post(
        url,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $platformToken',
        },
        body: jsonEncode({'name': companyName}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final companyId = data['company_id']?.toString();
        final wsObj = data['workspace'] as Map<String, dynamic>?;
        return AuthResult(
          success: true,
          token: platformToken,
          companyId: companyId,
          rawWorkspaces: wsObj != null ? [wsObj] : null,
        );
      } else if (response.statusCode == 422) {
        return const AuthResult(
          success: false,
          errorMessage: 'Tên công ty không hợp lệ',
        );
      }
      return AuthResult(
        success: false,
        errorMessage:
            'Tạo công ty không thành công (mã lỗi ${response.statusCode})',
      );
    } catch (e) {
      debugPrint('createCompany error: $e');
      return const AuthResult(
        success: false,
        errorMessage: 'Lỗi kết nối đến máy chủ. Vui lòng kiểm tra lại mạng.',
      );
    }
  }

  /// Tham gia company co san tren control_plane bang ma company.
  Future<AuthResult> joinCompany({
    required String platformToken,
    required String companyId,
  }) async {
    try {
      final parsedId = int.tryParse(companyId);
      if (parsedId == null) {
        return const AuthResult(
          success: false,
          errorMessage: 'Mã công ty không hợp lệ (phải là số)',
        );
      }
      final url = ApiClient.resolveUri('/platform/auth/companies/join');
      final response = await ApiClient.client.post(
        url,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $platformToken',
        },
        body: jsonEncode({'company_id': parsedId}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final resCompanyId = data['company_id']?.toString();
        final wsObj = data['workspace'] as Map<String, dynamic>?;
        return AuthResult(
          success: true,
          token: platformToken,
          companyId: resCompanyId,
          rawWorkspaces: wsObj != null ? [wsObj] : null,
        );
      } else if (response.statusCode == 404) {
        return const AuthResult(
          success: false,
          errorMessage: 'Công ty muốn tham gia không tồn tại',
        );
      }
      return AuthResult(
        success: false,
        errorMessage:
            'Tham gia công ty không thành công (mã lỗi ${response.statusCode})',
      );
    } catch (e) {
      debugPrint('joinCompany error: $e');
      return const AuthResult(
        success: false,
        errorMessage: 'Lỗi kết nối đến máy chủ. Vui lòng kiểm tra lại mạng.',
      );
    }
  }

  // ── Buoc 2: dong bo platform token + company da chon xuong local ──────────

  /// Goi sau khi da co platformToken (tu loginPlatform/registerPlatform).
  /// Backend local se tao/dong bo core.users + tất cả workspaces tuong ung
  /// roi phat local JWT. Tra ve access_token va danh sach workspace thuc te.
  Future<AuthResult> syncFromPlatform({required String platformToken}) async {
    try {
      // M1 §1 — lưu platform token dưới key riêng: dùng cho control-plane /
      // AgentOS platform path. Không trộn với local session token.
      await SecureStorageService.write('platform_access_token', platformToken);

      // M2 §29 (P0) — KHÔNG gửi `user`/`workspaces` lên server: client không
      // còn quyền tự khai báo workspace/role của chính mình, backend luôn lấy
      // và xác thực membership từ Control Plane (xem sync.service.ts).
      final response = await ApiClient.post(
        '/identity/sync-from-platform',
        requiresAuth: false,
        body: {'platform_access_token': platformToken},
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        // Backend trả cả `local_session_token` (M1 §1) lẫn alias `access_token`.
        final token =
            (data['local_session_token'] ?? data['access_token']) as String?;
        if (token == null) {
          return const AuthResult(
            success: false,
            errorMessage: 'Phản hồi không hợp lệ từ máy chủ',
          );
        }

        // Parse workspaces from backend response
        List<WorkspaceSummary> workspacesList = [];
        final workspacesData = data['workspaces'] as List<dynamic>?;
        if (workspacesData != null) {
          workspacesList = workspacesData
              .map((w) => WorkspaceSummary.fromJson(w as Map<String, dynamic>))
              .toList();
        }

        // Ghi local session token dưới key mới + key cũ (tương thích ngược cho
        // các reader chưa migrate).
        await SecureStorageService.write('local_session_token', token);
        await SecureStorageService.write('auth_token', token);
        _cachedToken = token;
        return AuthResult(
          success: true,
          token: token,
          workspaces: workspacesList,
        );
      } else if (response.statusCode == 403) {
        return const AuthResult(
          success: false,
          errorMessage: 'Bạn không phải thành viên của workspace nào',
        );
      }
      return AuthResult(
        success: false,
        errorMessage:
            'Đồng bộ dữ liệu không thành công (mã lỗi ${response.statusCode})',
      );
    } catch (e) {
      debugPrint('syncFromPlatform error: $e');
      return const AuthResult(
        success: false,
        errorMessage: 'Lỗi kết nối đến máy chủ. Vui lòng kiểm tra lại mạng.',
      );
    }
  }

  /// Buoc cuoi cua ca login lan register: dong bo platform token xuong local
  /// (tao/dong bo core.users va tất cả workspace tuong ung), roi cache
  /// workspace/role qua getMe(). Tra ve true neu thanh cong.
  Future<bool> finishAuthentication({required String platformToken}) async {
    final syncResult = await syncFromPlatform(platformToken: platformToken);
    if (!syncResult.success) return false;
    await getMe();
    return true;
  }

  /// Hoàn tất xác thực cho một workspace cụ thể sau khi đã sync toàn bộ list.
  /// (Dùng sau khi người dùng chọn workspace từ Workspace Picker)
  Future<bool> finishAuthenticationForWorkspace({
    required String platformToken,
    required String workspaceId,
  }) async {
    // Lưu workspace_id vào secure storage
    await SecureStorageService.write('workspace_id', workspaceId);
    // Đã sync từ platform, bây giờ chỉ cần lấy ME data
    await getMe();
    return true;
  }

  /// Cap nhat ho so sau khi da dang nhap - dung de bo sung so dien thoai
  /// (khong con bat buoc luc dang ky bang email+password nua) va/hoac ten
  /// hien thi. Tra ve payload /identity/me moi nhat neu thanh cong, null neu loi.
  Future<Map<String, dynamic>?> updateProfile({
    String? phone,
    String? displayName,
  }) async {
    try {
      final body = <String, dynamic>{};
      if (phone != null) body['phone'] = phone;
      if (displayName != null) body['display_name'] = displayName;

      final response = await ApiClient.patch('/identity/me', body: body);
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      debugPrint('updateProfile error: $e');
      return null;
    }
  }

  Future<Map<String, dynamic>?> getMe() async {
    try {
      final response = await ApiClient.get('/identity/me');
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);

        // Cache workspace id — scope tenant duy nhất (M3 §7).
        if (data['workspace_id'] != null) {
          await SecureStorageService.write(
            'workspace_id',
            data['workspace_id'].toString(),
          );
        }
        if (data['role'] != null) {
          // Strategy Canvas 1-1-3: Foundation tab cần biết role để ẩn/hiện nút
          // "Phê duyệt" (chỉ admin/founder được approve, xem strategy_canvas_service.py).
          await SecureStorageService.write('role', data['role'].toString());
        }

        return data;
      }
      return null;
    } catch (e) {
      debugPrint('GetMe error: $e');
      return null;
    }
  }

  Future<void> logout() async {
    RealtimeService.disconnect();
    _cachedToken = null;
    await SecureStorageService.delete('auth_token');
    await SecureStorageService.delete('local_session_token');
    await SecureStorageService.delete('platform_access_token');
    await SecureStorageService.delete('workspace_id');
    await SecureStorageService.delete('role');
  }

  Future<String?> getCachedRole() async {
    return SecureStorageService.read('role');
  }
}

import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../../core/network/api_client.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AuthResult {
  final bool success;
  final String? errorMessage;
  final String? token;
  final String? companyId;

  const AuthResult({
    required this.success,
    this.errorMessage,
    this.token,
    this.companyId,
  });
}

class CompanyMembershipInfo {
  final String companyId;
  final String? name;
  final String roleId;

  const CompanyMembershipInfo({required this.companyId, required this.name, required this.roleId});

  factory CompanyMembershipInfo.fromJson(Map<String, dynamic> json) => CompanyMembershipInfo(
        companyId: json['company_id'].toString(),
        name: json['name'] as String?,
        roleId: json['role_id'] as String,
      );
}

/// control_plane (Central) la nguon su that cho danh tinh - dang ky/dang
/// nhap BAT BUOC online tren control_plane truoc, sau do sync xuong backend
/// local (javis) de lay 1 local JWT dung cho moi API local khac. Local
/// KHONG con dang ky/dang nhap doc lap bang email+password nua.
class AuthService {
  static String? _cachedToken;

  static bool get isAuthenticated => _cachedToken != null && _cachedToken!.isNotEmpty;

  static Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    _cachedToken = prefs.getString('auth_token');
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
      final url = Uri.parse('${ApiClient.baseUrl}/platform/auth/sessions');
      final response = await ApiClient.client.post(
        url,
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: {'username': identifier, 'password': password},
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final token = data['access_token'] as String?;
        if (token == null) {
          return const AuthResult(success: false, errorMessage: 'Phản hồi không hợp lệ từ máy chủ');
        }
        return AuthResult(success: true, token: token);
      } else if (response.statusCode == 401) {
        return const AuthResult(success: false, errorMessage: 'Email/Số điện thoại hoặc mật khẩu không chính xác');
      }
      return AuthResult(
        success: false,
        errorMessage: 'Đăng nhập không thành công (mã lỗi ${response.statusCode})',
      );
    } catch (e) {
      debugPrint('loginPlatform error: $e');
      return const AuthResult(success: false, errorMessage: 'Lỗi kết nối đến máy chủ. Vui lòng kiểm tra lại mạng.');
    }
  }

  /// Dang ky tren control_plane bang email+password, kem theo dung 1 trong 2:
  /// [companyName] (tao company moi, role founder) hoac [joinCompanyId]
  /// (tham gia company co san, role user). Tra ve ca platform token va
  /// company_id vua duoc gan (server quyet dinh, vd company moi tao chua
  /// biet id truoc), de goi syncFromPlatform() ngay khong can hoi lai.
  Future<AuthResult> registerPlatform({
    required String email,
    required String password,
    required String displayName,
    String? companyName,
    String? joinCompanyId,
  }) async {
    try {
      final response = await ApiClient.post(
        '/platform/auth/register',
        requiresAuth: false,
        body: {
          'email': email,
          'password': password,
          'full_name': displayName,
          'company_name': ?companyName,
          if (joinCompanyId != null) 'join_company_id': int.tryParse(joinCompanyId) ?? joinCompanyId,
        },
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final token = data['access_token'] as String?;
        final companyId = data['company_id'] as String?;
        if (token == null) {
          return const AuthResult(success: false, errorMessage: 'Phản hồi không hợp lệ từ máy chủ');
        }
        return AuthResult(success: true, token: token, companyId: companyId);
      } else if (response.statusCode == 409) {
        return const AuthResult(success: false, errorMessage: 'Email này đã được đăng ký');
      } else if (response.statusCode == 404) {
        return const AuthResult(success: false, errorMessage: 'Company muốn tham gia không tồn tại');
      } else if (response.statusCode == 422) {
        try {
          final data = jsonDecode(response.body);
          final detail = data['detail'];
          if (detail is List && detail.isNotEmpty) {
            final msg = detail[0]['msg'] ?? 'Dữ liệu không hợp lệ';
            return AuthResult(success: false, errorMessage: msg.toString());
          }
        } catch (_) {}
        return const AuthResult(success: false, errorMessage: 'Dữ liệu đăng ký không hợp lệ');
      }
      return AuthResult(
        success: false,
        errorMessage: 'Đăng ký không thành công (mã lỗi ${response.statusCode})',
      );
    } catch (e) {
      debugPrint('registerPlatform error: $e');
      return const AuthResult(success: false, errorMessage: 'Lỗi kết nối đến máy chủ. Vui lòng kiểm tra lại mạng.');
    }
  }

  /// Danh sach company ma tai khoan control_plane hien tai la thanh vien -
  /// dung [platformToken] tam thoi tu loginPlatform()/registerPlatform() (
  /// chua phai auth_token da luu cua app) de goi truoc khi sync ve local.
  Future<List<CompanyMembershipInfo>?> listMyCompanies(String platformToken) async {
    try {
      final url = Uri.parse('${ApiClient.baseUrl}/platform/auth/me/companies');
      final response = await ApiClient.client.get(url, headers: {'Authorization': 'Bearer $platformToken'});
      if (response.statusCode != 200) return null;
      final dynamic decoded = jsonDecode(response.body);
      final List<dynamic> data;
      if (decoded is List) {
        data = decoded;
      } else if (decoded is Map && decoded['companies'] is List) {
        data = decoded['companies'] as List<dynamic>;
      } else {
        return null;
      }
      return data.map((e) => CompanyMembershipInfo.fromJson(e as Map<String, dynamic>)).toList();
    } catch (e) {
      debugPrint('listMyCompanies error: $e');
      return null;
    }
  }

  /// Tao company moi tren control_plane cho platform user hien tai.
  Future<AuthResult> createCompany({
    required String platformToken,
    required String companyName,
  }) async {
    try {
      final url = Uri.parse('${ApiClient.baseUrl}/platform/auth/companies/create');
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
        return AuthResult(success: true, token: platformToken, companyId: companyId);
      } else if (response.statusCode == 422) {
        return const AuthResult(success: false, errorMessage: 'Tên công ty không hợp lệ');
      }
      return AuthResult(
        success: false,
        errorMessage: 'Tạo công ty không thành công (mã lỗi ${response.statusCode})',
      );
    } catch (e) {
      debugPrint('createCompany error: $e');
      return const AuthResult(success: false, errorMessage: 'Lỗi kết nối đến máy chủ. Vui lòng kiểm tra lại mạng.');
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
        return const AuthResult(success: false, errorMessage: 'Mã công ty không hợp lệ (phải là số)');
      }
      final url = Uri.parse('${ApiClient.baseUrl}/platform/auth/companies/join');
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
        return AuthResult(success: true, token: platformToken, companyId: resCompanyId);
      } else if (response.statusCode == 404) {
        return const AuthResult(success: false, errorMessage: 'Công ty muốn tham gia không tồn tại');
      }
      return AuthResult(
        success: false,
        errorMessage: 'Tham gia công ty không thành công (mã lỗi ${response.statusCode})',
      );
    } catch (e) {
      debugPrint('joinCompany error: $e');
      return const AuthResult(success: false, errorMessage: 'Lỗi kết nối đến máy chủ. Vui lòng kiểm tra lại mạng.');
    }
  }

  // ── Buoc 2: dong bo platform token + company da chon xuong local ──────────

  /// Goi sau khi da co platformToken (tu loginPlatform/registerPlatform) va
  /// da xac dinh company nao dang active (tu duy nhat 1 company, hoac nguoi
  /// dung da chon qua man Company Picker). Backend local se tao/dong bo
  /// core.users + workspace tuong ung roi phat local JWT - luu lai lam
  /// auth_token chinh thuc cua app.
  Future<AuthResult> syncFromPlatform({required String platformToken, required String companyId}) async {
    try {
      final response = await ApiClient.post(
        '/auth/sync-from-platform',
        requiresAuth: false,
        body: {'platform_access_token': platformToken, 'company_id': companyId},
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final token = data['access_token'] as String?;
        if (token == null) {
          return const AuthResult(success: false, errorMessage: 'Phản hồi không hợp lệ từ máy chủ');
        }
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('auth_token', token);
        _cachedToken = token;
        return AuthResult(success: true, token: token, companyId: companyId);
      } else if (response.statusCode == 403) {
        return const AuthResult(success: false, errorMessage: 'Bạn không phải thành viên của company này');
      }
      return AuthResult(
        success: false,
        errorMessage: 'Đồng bộ dữ liệu không thành công (mã lỗi ${response.statusCode})',
      );
    } catch (e) {
      debugPrint('syncFromPlatform error: $e');
      return const AuthResult(success: false, errorMessage: 'Lỗi kết nối đến máy chủ. Vui lòng kiểm tra lại mạng.');
    }
  }

  /// Buoc cuoi cua ca login lan register: dong bo platform token + company
  /// da xac dinh xuong local (tao/dong bo core.users va workspace tuong
  /// ung), roi cache workspace/brain/role qua getMe(). Dung chung cho
  /// AuthController (1 company) va CompanyPickerController (>=2 company).
  /// Tra ve true neu thanh cong - noi goi tu quyet dinh dieu huong sang hub.
  Future<bool> finishAuthentication({required String platformToken, required String companyId}) async {
    final syncResult = await syncFromPlatform(platformToken: platformToken, companyId: companyId);
    if (!syncResult.success) return false;
    await getMe();
    return true;
  }

  /// Cap nhat ho so sau khi da dang nhap - dung de bo sung so dien thoai
  /// (khong con bat buoc luc dang ky bang email+password nua) va/hoac ten
  /// hien thi. Tra ve payload /auth/me moi nhat neu thanh cong, null neu loi.
  Future<Map<String, dynamic>?> updateProfile({String? phone, String? displayName}) async {
    try {
      final body = <String, dynamic>{};
      if (phone != null) body['phone'] = phone;
      if (displayName != null) body['display_name'] = displayName;

      final response = await ApiClient.patch('/auth/me', body: body);
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
      final response = await ApiClient.get('/auth/me');
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);

        // Caching workspace and brain IDs for subsequent calls
        final prefs = await SharedPreferences.getInstance();
        if (data['workspace_id'] != null) {
          await prefs.setString('workspace_id', data['workspace_id'].toString());
        }
        if (data['brain_id'] != null) {
          await prefs.setString('brain_id', data['brain_id'].toString());
        }
        if (data['role'] != null) {
          // Strategy Canvas 1-1-3: Foundation tab cần biết role để ẩn/hiện nút
          // "Phê duyệt" (chỉ admin/founder được approve, xem strategy_canvas_service.py).
          await prefs.setString('role', data['role'].toString());
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
    _cachedToken = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('auth_token');
    await prefs.remove('workspace_id');
    await prefs.remove('brain_id');
    await prefs.remove('role');
  }

  Future<String?> getCachedRole() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('role');
  }
}

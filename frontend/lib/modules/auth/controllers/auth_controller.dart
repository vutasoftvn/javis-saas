import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../modules/auth/services/auth_service.dart';
import '../../../core/routing/app_routes.dart';

class AuthController extends GetxController {
  final AuthService _authService = AuthService();

  // Login State
  final isLoading = false.obs;
  final errorMessage = ''.obs;
  final rememberMe = false.obs;
  final isPasswordVisible = false.obs;

  final identifierController = TextEditingController();
  final passwordController = TextEditingController();

  // Register State
  final isRegisterLoading = false.obs;
  final registerErrorMessage = ''.obs;
  final isRegPasswordVisible = false.obs;
  final isRegConfirmVisible = false.obs;
  final registerStep = 1.obs; // 1 = Thong tin tai khoan, 2 = Thiet lap cong ty
  final registeredPlatformToken = ''.obs;

  final regDisplayNameController = TextEditingController();
  final regEmailController = TextEditingController();
  final regPasswordController = TextEditingController();
  final regConfirmPasswordController = TextEditingController();

  /// false = tạo công ty mới (regCompanyNameController), true = tham gia
  /// công ty có sẵn bằng mã (regJoinCompanyIdController).
  final isJoiningCompany = false.obs;
  final regCompanyNameController = TextEditingController();
  final regJoinCompanyIdController = TextEditingController();

  static final RegExp _emailRegExp = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');

  @override
  void onInit() {
    super.onInit();
    _loadSavedCredentials();
  }

  Future<void> _loadSavedCredentials() async {
    final prefs = await SharedPreferences.getInstance();
    final savedIdentifier = prefs.getString('saved_identifier');

    // Bản cài đặt cũ (trước khi vá lỗi) có thể còn key `saved_password` lưu
    // mật khẩu dạng plaintext trong SharedPreferences — xoá ngay, không bao
    // giờ đọc/gán giá trị này vào passwordController.
    if (prefs.containsKey('saved_password')) {
      await prefs.remove('saved_password');
    }

    if (savedIdentifier != null) {
      identifierController.text = savedIdentifier;
      rememberMe.value = true;
    }
  }

  @override
  void onClose() {
    identifierController.dispose();
    passwordController.dispose();
    regDisplayNameController.dispose();
    regEmailController.dispose();
    regPasswordController.dispose();
    regConfirmPasswordController.dispose();
    regCompanyNameController.dispose();
    regJoinCompanyIdController.dispose();
    super.onClose();
  }

  void clearRegisterForm() {
    regDisplayNameController.clear();
    regEmailController.clear();
    regPasswordController.clear();
    regConfirmPasswordController.clear();
    regCompanyNameController.clear();
    regJoinCompanyIdController.clear();
    isJoiningCompany.value = false;
    registerStep.value = 1;
    registeredPlatformToken.value = '';
    registerErrorMessage.value = '';
  }

  /// Đăng nhập: control_plane trước (bắt buộc online) → đồng bộ toàn bộ
  /// workspaces về local; nếu chỉ 1 workspace thì vào hub luôn, nếu nhiều
  /// thì chuyển sang màn Workspace Picker để chọn.
  Future<void> login([String? customId, String? customPwd]) async {
    final identifier = (customId ?? identifierController.text).trim();
    final password = customPwd ?? passwordController.text;

    if (identifier.isEmpty || password.isEmpty) {
      errorMessage.value = 'Vui lòng nhập đầy đủ thông tin đăng nhập';
      return;
    }

    isLoading.value = true;
    errorMessage.value = '';

    final loginResult = await _authService.loginPlatform(identifier, password);
    if (!loginResult.success || loginResult.token == null) {
      errorMessage.value = loginResult.errorMessage ?? 'Đăng nhập thất bại. Vui lòng kiểm tra lại thông tin.';
      isLoading.value = false;
      return;
    }
    final platformToken = loginResult.token!;

    // Đồng bộ toàn bộ workspaces từ backend — lấy danh sách workspace thực từ sync result
    final syncResult = await _authService.syncFromPlatform(platformToken: platformToken);
    if (!syncResult.success) {
      errorMessage.value = syncResult.errorMessage ?? 'Đồng bộ dữ liệu workspace thất bại. Vui lòng thử lại.';
      isLoading.value = false;
      return;
    }

    // Use workspaces returned by backend sync — NOT legacy company IDs
    final workspaces = syncResult.workspaces ?? [];
    if (workspaces.isEmpty) {
      errorMessage.value = 'Tài khoản chưa thuộc workspace nào.';
      isLoading.value = false;
      return;
    }

    // Chỉ ghi nhớ identifier (email/số điện thoại) — KHÔNG BAO GIỜ lưu mật
    // khẩu dạng plaintext vào SharedPreferences. Token phiên đăng nhập đã có
    // secure storage riêng (xem AuthService.syncFromPlatform).
    final prefs = await SharedPreferences.getInstance();
    if (rememberMe.value) {
      await prefs.setString('saved_identifier', identifier);
    } else {
      await prefs.remove('saved_identifier');
    }

    if (workspaces.length == 1) {
      // Auto-select single workspace
      final ok = await _authService.finishAuthenticationForWorkspace(
        platformToken: platformToken,
        workspaceId: workspaces.first.workspaceId,
      );
      if (ok) {
        Get.offAllNamed(AppRoutes.hub);
      } else {
        errorMessage.value = 'Đồng bộ dữ liệu workspace thất bại. Vui lòng thử lại.';
      }
    } else {
      isLoading.value = false;
      Get.toNamed(
        AppRoutes.workspacePicker,
        arguments: {'platformToken': platformToken, 'workspaces': workspaces},
      );
      return;
    }

    isLoading.value = false;
  }

  /// Bước 1: Đăng ký tài khoản cá nhân trên Control Plane (chưa sync về local).
  Future<void> submitAccountStep([String? customEmail, String? customPwd, String? customName]) async {
    final displayName = (customName ?? regDisplayNameController.text).trim();
    final email = (customEmail ?? regEmailController.text).trim();
    final password = customPwd ?? regPasswordController.text;
    final confirmPassword = regConfirmPasswordController.text;

    if (displayName.isEmpty) {
      registerErrorMessage.value = 'Vui lòng nhập Họ và tên';
      return;
    }

    if (email.isEmpty) {
      registerErrorMessage.value = 'Vui lòng nhập Email';
      return;
    }

    if (!_emailRegExp.hasMatch(email)) {
      registerErrorMessage.value = 'Email không hợp lệ';
      return;
    }

    if (password.length < 6) {
      registerErrorMessage.value = 'Mật khẩu phải có ít nhất 6 ký tự';
      return;
    }

    if (customPwd == null && password != confirmPassword) {
      registerErrorMessage.value = 'Mật khẩu xác nhận không trùng khớp';
      return;
    }

    isRegisterLoading.value = true;
    registerErrorMessage.value = '';

    try {
      final result = await _authService.registerPlatform(
        email: email,
        password: password,
        displayName: displayName,
      );

      if (!result.success || result.token == null) {
        registerErrorMessage.value = result.errorMessage ?? 'Đăng ký tài khoản thất bại. Vui lòng thử lại.';
        return;
      }

      registeredPlatformToken.value = result.token!;
      registerStep.value = 2;
    } catch (e) {
      registerErrorMessage.value = 'Đã có lỗi xảy ra: $e';
    } finally {
      isRegisterLoading.value = false;
    }
  }

  /// Bước 2: Thiết lập Workspace (Tạo mới hoặc Tham gia) -> Đồng bộ về Local.
  Future<void> submitCompanyStep() async {
    final token = registeredPlatformToken.value;
    if (token.isEmpty) {
      registerErrorMessage.value = 'Phiên đăng ký không hợp lệ. Vui lòng đăng ký lại.';
      registerStep.value = 1;
      return;
    }

    final companyName = isJoiningCompany.value ? null : regCompanyNameController.text.trim();
    final joinCompanyId = isJoiningCompany.value ? regJoinCompanyIdController.text.trim() : null;

    if (!isJoiningCompany.value && (companyName == null || companyName.isEmpty)) {
      registerErrorMessage.value = 'Vui lòng nhập tên workspace muốn tạo';
      return;
    }
    if (isJoiningCompany.value && (joinCompanyId == null || joinCompanyId.isEmpty)) {
      registerErrorMessage.value = 'Vui lòng nhập mã workspace muốn tham gia';
      return;
    }

    isRegisterLoading.value = true;
    registerErrorMessage.value = '';

    try {
      final AuthResult companyResult;
      if (isJoiningCompany.value) {
        companyResult = await _authService.joinCompany(
          platformToken: token,
          companyId: joinCompanyId!,
        );
      } else {
        companyResult = await _authService.createCompany(
          platformToken: token,
          companyName: companyName!,
        );
      }

      if (!companyResult.success || companyResult.companyId == null) {
        registerErrorMessage.value = companyResult.errorMessage ?? 'Thiết lập workspace thất bại. Vui lòng thử lại.';
        return;
      }

      // Bước 3: Đã có Account + Workspace -> Đồng bộ về Local Database
      final ok = await _authService.finishAuthentication(platformToken: token);

      if (ok) {
        Get.offAllNamed(AppRoutes.hub);
      } else {
        registerErrorMessage.value = 'Đăng ký thành công nhưng đồng bộ dữ liệu về Local thất bại. Vui lòng thử đăng nhập lại.';
      }
    } catch (e) {
      registerErrorMessage.value = 'Đã có lỗi xảy ra: $e';
    } finally {
      isRegisterLoading.value = false;
    }
  }

  void goToPreviousStep() {
    if (registerStep.value > 1) {
      registerStep.value = 1;
      registerErrorMessage.value = '';
    }
  }

  /// Backward-compatible register helper
  Future<void> register([String? customEmail, String? customPwd, String? customName]) async {
    if (registerStep.value == 1) {
      await submitAccountStep(customEmail, customPwd, customName);
    } else {
      await submitCompanyStep();
    }
  }
}

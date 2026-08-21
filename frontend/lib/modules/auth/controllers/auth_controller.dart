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

  final regDisplayNameController = TextEditingController();
  final regEmailController = TextEditingController();
  final regPasswordController = TextEditingController();
  final regConfirmPasswordController = TextEditingController();

  /// false = tạo công ty mới (regCompanyNameController), true = tham gia
  /// công ty có sẵn bằng mã (regJoinCompanyIdController) - RegisterRequest
  /// bên control_plane bắt buộc chọn đúng 1 trong 2.
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
    final savedPassword = prefs.getString('saved_password');

    if (savedIdentifier != null && savedPassword != null) {
      identifierController.text = savedIdentifier;
      passwordController.text = savedPassword;
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
    registerErrorMessage.value = '';
  }

  /// Đăng nhập: control_plane trước (bắt buộc online) → nếu tài khoản chỉ
  /// thuộc 1 company thì đồng bộ thẳng về local; nếu thuộc nhiều company thì
  /// chuyển sang màn chọn company (không bắt gõ company_id thủ công).
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

    final companies = await _authService.listMyCompanies(platformToken);
    if (companies == null) {
      errorMessage.value = 'Không tải được danh sách công ty. Vui lòng thử lại.';
      isLoading.value = false;
      return;
    }
    if (companies.isEmpty) {
      errorMessage.value = 'Tài khoản chưa thuộc công ty nào.';
      isLoading.value = false;
      return;
    }

    // Save or remove remembered credentials based on rememberMe
    final prefs = await SharedPreferences.getInstance();
    if (rememberMe.value) {
      await prefs.setString('saved_identifier', identifier);
      await prefs.setString('saved_password', password);
    } else {
      await prefs.remove('saved_identifier');
      await prefs.remove('saved_password');
    }

    if (companies.length == 1) {
      final ok = await _authService.finishAuthentication(
        platformToken: platformToken,
        companyId: companies.first.companyId,
      );
      if (ok) {
        Get.offAllNamed(AppRoutes.hub);
      } else {
        errorMessage.value = 'Đồng bộ dữ liệu công ty thất bại. Vui lòng thử lại.';
      }
    } else {
      isLoading.value = false;
      Get.toNamed(
        AppRoutes.companyPicker,
        arguments: {'platformToken': platformToken, 'companies': companies},
      );
      return;
    }

    isLoading.value = false;
  }

  Future<void> register([String? customEmail, String? customPwd, String? customName]) async {
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

    // Only check confirmPassword if registering through the form (when customPwd is null)
    if (customPwd == null && password != confirmPassword) {
      registerErrorMessage.value = 'Mật khẩu xác nhận không trùng khớp';
      return;
    }

    final companyName = isJoiningCompany.value ? null : regCompanyNameController.text.trim();
    final joinCompanyId = isJoiningCompany.value ? regJoinCompanyIdController.text.trim() : null;

    if (!isJoiningCompany.value && (companyName == null || companyName.isEmpty)) {
      registerErrorMessage.value = 'Vui lòng nhập tên công ty muốn tạo';
      return;
    }
    if (isJoiningCompany.value && (joinCompanyId == null || joinCompanyId.isEmpty)) {
      registerErrorMessage.value = 'Vui lòng nhập mã công ty muốn tham gia';
      return;
    }

    isRegisterLoading.value = true;
    registerErrorMessage.value = '';

    final result = await _authService.registerPlatform(
      email: email,
      password: password,
      displayName: displayName,
      companyName: companyName,
      joinCompanyId: joinCompanyId,
    );

    if (!result.success || result.token == null || result.companyId == null) {
      registerErrorMessage.value = result.errorMessage ?? 'Đăng ký thất bại. Vui lòng thử lại.';
      isRegisterLoading.value = false;
      return;
    }

    final ok = await _authService.finishAuthentication(
      platformToken: result.token!,
      companyId: result.companyId!,
    );
    if (ok) {
      Get.offAllNamed(AppRoutes.hub);
    } else {
      registerErrorMessage.value = 'Đăng ký thành công nhưng đồng bộ dữ liệu thất bại. Vui lòng đăng nhập lại.';
    }

    isRegisterLoading.value = false;
  }
}

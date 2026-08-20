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
  final regPhoneController = TextEditingController();
  final regPasswordController = TextEditingController();
  final regConfirmPasswordController = TextEditingController();

  static final RegExp _phoneRegExp = RegExp(r'^\+?\d{9,15}$');

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
    regPhoneController.dispose();
    regPasswordController.dispose();
    regConfirmPasswordController.dispose();
    super.onClose();
  }

  void clearRegisterForm() {
    regDisplayNameController.clear();
    regPhoneController.clear();
    regPasswordController.clear();
    regConfirmPasswordController.clear();
    registerErrorMessage.value = '';
  }

  Future<void> login([String? customId, String? customPwd]) async {
    final identifier = (customId ?? identifierController.text).trim();
    final password = customPwd ?? passwordController.text;

    if (identifier.isEmpty || password.isEmpty) {
      errorMessage.value = 'Vui lòng nhập đầy đủ thông tin đăng nhập';
      return;
    }

    isLoading.value = true;
    errorMessage.value = '';

    final result = await _authService.login(identifier, password);
    if (result.success) {
      // Save or remove credentials based on rememberMe
      final prefs = await SharedPreferences.getInstance();
      if (rememberMe.value) {
        await prefs.setString('saved_identifier', identifier);
        await prefs.setString('saved_password', password);
      } else {
        await prefs.remove('saved_identifier');
        await prefs.remove('saved_password');
      }

      // Get user profile to cache workspace_id and brain_id
      await _authService.getMe();
      Get.offAllNamed(AppRoutes.hub);
    } else {
      errorMessage.value = result.errorMessage ?? 'Đăng nhập thất bại. Vui lòng kiểm tra lại thông tin.';
    }

    isLoading.value = false;
  }

  Future<void> register([String? customPhone, String? customPwd, String? customName]) async {
    final displayName = (customName ?? regDisplayNameController.text).trim();
    final phoneRaw = (customPhone ?? regPhoneController.text).trim().replaceAll(' ', '').replaceAll('-', '');
    final password = customPwd ?? regPasswordController.text;
    final confirmPassword = regConfirmPasswordController.text;

    if (displayName.isEmpty) {
      registerErrorMessage.value = 'Vui lòng nhập Họ và tên';
      return;
    }

    if (phoneRaw.isEmpty) {
      registerErrorMessage.value = 'Vui lòng nhập Số điện thoại';
      return;
    }

    if (!_phoneRegExp.hasMatch(phoneRaw)) {
      registerErrorMessage.value = 'Số điện thoại không hợp lệ (từ 9 đến 15 chữ số, ví dụ 0912345678)';
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

    isRegisterLoading.value = true;
    registerErrorMessage.value = '';

    final result = await _authService.register(phoneRaw, password, displayName);
    if (result.success) {
      // Fetch profile to cache workspace_id, brain_id and role
      await _authService.getMe();
      Get.offAllNamed(AppRoutes.hub);
    } else {
      registerErrorMessage.value = result.errorMessage ?? 'Đăng ký thất bại. Vui lòng thử lại.';
    }

    isRegisterLoading.value = false;
  }
}


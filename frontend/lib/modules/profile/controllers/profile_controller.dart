import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../auth/services/auth_service.dart';
import '../../../core/network/realtime_service.dart';
import '../../../core/routing/app_routes.dart';

class ProfileController extends GetxController {
  final AuthService _authService = AuthService();

  final isLoading = true.obs;
  final isSaving = false.obs;
  final errorMessage = ''.obs;
  final successMessage = ''.obs;

  final userId = ''.obs;
  final email = ''.obs;
  final phone = Rxn<String>();
  final role = Rxn<String>();
  final displayName = ''.obs;

  final displayNameController = TextEditingController();
  final phoneController = TextEditingController();
  final isEditingPhone = false.obs;

  static final RegExp _phoneRegExp = RegExp(r'^\+?\d{9,15}$');

  @override
  void onInit() {
    super.onInit();
    loadProfile();
  }

  @override
  void onClose() {
    displayNameController.dispose();
    phoneController.dispose();
    super.onClose();
  }

  Future<void> loadProfile() async {
    isLoading.value = true;
    errorMessage.value = '';
    final me = await _authService.getMe();
    if (me == null) {
      errorMessage.value = 'Không tải được hồ sơ. Vui lòng đăng nhập lại.';
      isLoading.value = false;
      return;
    }
    userId.value = (me['id'] ?? '').toString();
    email.value = (me['email'] ?? '').toString();
    phone.value = me['phone'] as String?;
    role.value = me['role'] as String?;
    displayName.value = (me['display_name'] ?? '').toString();
    displayNameController.text = displayName.value;
    phoneController.text = phone.value ?? '';
    isLoading.value = false;
  }

  Future<void> saveDisplayName() async {
    final name = displayNameController.text.trim();
    if (name.isEmpty) {
      errorMessage.value = 'Họ và tên không được để trống';
      return;
    }
    await _save(displayName: name);
  }

  Future<void> savePhone() async {
    final raw = phoneController.text.trim().replaceAll(' ', '').replaceAll('-', '');
    if (raw.isEmpty) {
      errorMessage.value = 'Vui lòng nhập số điện thoại';
      return;
    }
    if (!_phoneRegExp.hasMatch(raw)) {
      errorMessage.value = 'Số điện thoại không hợp lệ (9-15 chữ số)';
      return;
    }
    final ok = await _save(phone: raw);
    if (ok) isEditingPhone.value = false;
  }

  Future<bool> _save({String? phone, String? displayName}) async {
    isSaving.value = true;
    errorMessage.value = '';
    successMessage.value = '';

    final result = await _authService.updateProfile(phone: phone, displayName: displayName);
    isSaving.value = false;

    if (result == null) {
      errorMessage.value = 'Cập nhật thất bại. Vui lòng thử lại.';
      return false;
    }

    if (result['phone'] != null) this.phone.value = result['phone'] as String?;
    if (result['display_name'] != null) {
      this.displayName.value = result['display_name'].toString();
    }
    successMessage.value = 'Đã cập nhật hồ sơ';
    return true;
  }

  Future<void> logout() async {
    RealtimeService.disconnect();
    await _authService.logout();
    Get.offAllNamed(AppRoutes.login);
  }
}

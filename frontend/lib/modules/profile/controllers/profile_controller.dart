import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../auth/services/auth_service.dart';
import '../../auth/services/core_auth_client.dart';
import '../../auth/services/core_profile_client.dart';
import '../../../core/network/realtime_service.dart';
import '../../../core/routing/app_routes.dart';

import '../../../core/localization/locale_controller.dart';
import '../../../core/localization/supported_locale.dart';

class ProfileController extends GetxController {
  ProfileController({
    AuthService? authService,
    CoreProfileClient? coreProfile,
    this.localeController,
  })  : _authService = authService ?? AuthService(),
        _coreProfile = coreProfile ?? CoreProfileClient();

  final AuthService _authService;
  // Phone/tên hiển thị thuộc Core (spec 2026-09-25 §8) — ghi thẳng vào Core.
  final CoreProfileClient _coreProfile;
  final LocaleController? localeController;

  final isLoading = true.obs;
  final isSaving = false.obs;
  final isSavingLocale = false.obs;
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
  final otpController = TextEditingController();
  /// Số mới đang chờ xác nhận OTP; null khi chưa yêu cầu đổi số.
  final pendingPhone = Rxn<String>();

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
    otpController.dispose();
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
    await _run(() async {
      displayName.value = await _coreProfile.updateDisplayName(name);
      displayNameController.text = displayName.value;
      successMessage.value = 'Đã cập nhật hồ sơ';
    });
  }

  /// Bước 1: Core gửi OTP tới số mới. Số chỉ đổi sau khi xác nhận OTP.
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
    await _run(() async {
      final challenge = await _coreProfile.requestPhoneChange(raw);
      pendingPhone.value = challenge.phone;
      otpController.clear();
      successMessage.value = 'Đã gửi mã xác nhận tới ${challenge.phone}';
    });
  }

  /// Bước 2: xác nhận OTP; chỉ khi Core trả số đã lưu mới cập nhật giao diện.
  Future<void> verifyPhoneOtp() async {
    final target = pendingPhone.value;
    final otp = otpController.text.trim();
    if (target == null) return;
    if (otp.isEmpty) {
      errorMessage.value = 'Vui lòng nhập mã xác nhận';
      return;
    }
    await _run(() async {
      phone.value = await _coreProfile.verifyPhoneChange(phone: target, otp: otp);
      pendingPhone.value = null;
      isEditingPhone.value = false;
      otpController.clear();
      successMessage.value = 'Đã cập nhật số điện thoại';
    });
  }

  void cancelPhoneEdit() {
    pendingPhone.value = null;
    isEditingPhone.value = false;
    otpController.clear();
  }

  Future<void> _run(Future<void> Function() action) async {
    isSaving.value = true;
    errorMessage.value = '';
    successMessage.value = '';
    try {
      await action();
    } on CoreAuthException catch (e) {
      errorMessage.value = e.statusCode == 401
          ? 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.'
          : 'Cập nhật thất bại: ${e.message}';
    } catch (e) {
      debugPrint('core profile update error: $e');
      errorMessage.value = 'Cập nhật thất bại. Vui lòng thử lại.';
    } finally {
      isSaving.value = false;
    }
  }

  Future<void> selectLocale(SupportedLocale newLocale) async {
    final lc = localeController ??
        (Get.isRegistered<LocaleController>() ? Get.find<LocaleController>() : null);
    if (lc == null || lc.current.value == newLocale) return;
    isSavingLocale.value = true;
    errorMessage.value = '';
    successMessage.value = '';

    final ok = await lc.updatePreference(newLocale);
    isSavingLocale.value = false;
    if (ok) {
      successMessage.value = newLocale == SupportedLocale.viVN
          ? 'Đã cập nhật ngôn ngữ sang Tiếng Việt'
          : 'Language updated to English';
    } else {
      errorMessage.value = lc.current.value == SupportedLocale.viVN
          ? 'Cập nhật ngôn ngữ thất bại. Vui lòng thử lại.'
          : 'Failed to update language. Please try again.';
    }
  }

  Future<void> logout() async {
    RealtimeService.disconnect();
    await _authService.logout();
    Get.offAllNamed(AppRoutes.login);
  }
}

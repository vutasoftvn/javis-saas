import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/auth_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/routing/app_routes.dart';

class RegisterView extends GetView<AuthController> {
  const RegisterView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundDark,
      body: Container(
        decoration: const BoxDecoration(
          gradient: AppTheme.backgroundRadialGradient,
        ),
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 32.0),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Container(
                padding: const EdgeInsets.all(32),
                decoration: BoxDecoration(
                  color: AppTheme.surfaceDark.withValues(alpha: 0.85),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: AppTheme.primary.withValues(alpha: 0.25),
                    width: 1,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: AppTheme.primary.withValues(alpha: 0.08),
                      blurRadius: 24,
                      offset: const Offset(0, 8),
                    ),
                  ],
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Header Logo & Branding
                    Center(
                      child: Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: AppTheme.primary.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(
                            color: AppTheme.primary.withValues(alpha: 0.4),
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: AppTheme.primary.withValues(alpha: 0.2),
                              blurRadius: 16,
                            ),
                          ],
                        ),
                        child: const Icon(
                          Icons.psychology,
                          size: 44,
                          color: AppTheme.primary,
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    const Text(
                      'Tạo Tài Khoản Mới',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.w800,
                        color: Colors.white,
                        letterSpacing: -0.5,
                      ),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Khởi tạo Brain & Không gian làm việc AI của bạn',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 13,
                        color: AppTheme.textMutedDark,
                      ),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      'Số điện thoại có thể bổ sung sau trong mục Hồ sơ',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 11,
                        color: AppTheme.textDimDark,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                    const SizedBox(height: 28),

                    // Error Message Display
                    Obx(() => controller.registerErrorMessage.value.isNotEmpty
                        ? Container(
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                            margin: const EdgeInsets.only(bottom: 20),
                            decoration: BoxDecoration(
                              color: AppTheme.accent.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(
                                color: AppTheme.accent.withValues(alpha: 0.6),
                              ),
                            ),
                            child: Row(
                              children: [
                                const Icon(Icons.error_outline, size: 20, color: AppTheme.accent),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Text(
                                    controller.registerErrorMessage.value,
                                    style: const TextStyle(
                                      color: AppTheme.accentLight,
                                      fontSize: 13,
                                      fontWeight: FontWeight.w500,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          )
                        : const SizedBox.shrink()),

                    // Full Name Input
                    TextField(
                      controller: controller.regDisplayNameController,
                      style: const TextStyle(color: Colors.white, fontSize: 14),
                      decoration: InputDecoration(
                        labelText: 'Họ và tên',
                        labelStyle: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
                        prefixIcon: const Icon(Icons.person_outline, color: AppTheme.primary, size: 20),
                        filled: true,
                        fillColor: AppTheme.backgroundDark.withValues(alpha: 0.8),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                          borderSide: const BorderSide(color: AppTheme.borderDark),
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                          borderSide: const BorderSide(color: AppTheme.borderDark),
                        ),
                        focusedBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                          borderSide: const BorderSide(color: AppTheme.primary, width: 1.5),
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),

                    // Email Input
                    TextField(
                      controller: controller.regEmailController,
                      keyboardType: TextInputType.emailAddress,
                      style: const TextStyle(color: Colors.white, fontSize: 14),
                      decoration: InputDecoration(
                        labelText: 'Email',
                        hintText: 'Ví dụ: ban@congty.com',
                        hintStyle: const TextStyle(color: AppTheme.textDimDark, fontSize: 12),
                        labelStyle: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
                        prefixIcon: const Icon(Icons.email_outlined, color: AppTheme.primary, size: 20),
                        filled: true,
                        fillColor: AppTheme.backgroundDark.withValues(alpha: 0.8),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                          borderSide: const BorderSide(color: AppTheme.borderDark),
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                          borderSide: const BorderSide(color: AppTheme.borderDark),
                        ),
                        focusedBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                          borderSide: const BorderSide(color: AppTheme.primary, width: 1.5),
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),

                    // Password Input
                    Obx(() => TextField(
                          controller: controller.regPasswordController,
                          obscureText: !controller.isRegPasswordVisible.value,
                          style: const TextStyle(color: Colors.white, fontSize: 14),
                          decoration: InputDecoration(
                            labelText: 'Mật khẩu (tối thiểu 6 ký tự)',
                            labelStyle: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
                            prefixIcon: const Icon(Icons.lock_outline, color: AppTheme.primary, size: 20),
                            suffixIcon: IconButton(
                              icon: Icon(
                                controller.isRegPasswordVisible.value
                                    ? Icons.visibility_outlined
                                    : Icons.visibility_off_outlined,
                                color: AppTheme.textMutedDark,
                                size: 20,
                              ),
                              onPressed: () {
                                controller.isRegPasswordVisible.toggle();
                              },
                            ),
                            filled: true,
                            fillColor: AppTheme.backgroundDark.withValues(alpha: 0.8),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10),
                              borderSide: const BorderSide(color: AppTheme.borderDark),
                            ),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10),
                              borderSide: const BorderSide(color: AppTheme.borderDark),
                            ),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10),
                              borderSide: const BorderSide(color: AppTheme.primary, width: 1.5),
                            ),
                          ),
                        )),
                    const SizedBox(height: 16),

                    // Confirm Password Input
                    Obx(() => TextField(
                          controller: controller.regConfirmPasswordController,
                          obscureText: !controller.isRegConfirmVisible.value,
                          style: const TextStyle(color: Colors.white, fontSize: 14),
                          decoration: InputDecoration(
                            labelText: 'Xác nhận mật khẩu',
                            labelStyle: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
                            prefixIcon: const Icon(Icons.lock_reset, color: AppTheme.primary, size: 20),
                            suffixIcon: IconButton(
                              icon: Icon(
                                controller.isRegConfirmVisible.value
                                    ? Icons.visibility_outlined
                                    : Icons.visibility_off_outlined,
                                color: AppTheme.textMutedDark,
                                size: 20,
                              ),
                              onPressed: () {
                                controller.isRegConfirmVisible.toggle();
                              },
                            ),
                            filled: true,
                            fillColor: AppTheme.backgroundDark.withValues(alpha: 0.8),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10),
                              borderSide: const BorderSide(color: AppTheme.borderDark),
                            ),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10),
                              borderSide: const BorderSide(color: AppTheme.borderDark),
                            ),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10),
                              borderSide: const BorderSide(color: AppTheme.primary, width: 1.5),
                            ),
                          ),
                        )),
                    const SizedBox(height: 20),

                    // Company choice toggle
                    Obx(() => Container(
                          decoration: BoxDecoration(
                            color: AppTheme.borderDark,
                            borderRadius: BorderRadius.circular(10),
                          ),
                          padding: const EdgeInsets.all(3),
                          child: Row(
                            children: [
                              Expanded(
                                child: _ChoiceTab(
                                  label: 'Tạo công ty mới',
                                  isSelected: !controller.isJoiningCompany.value,
                                  onTap: () => controller.isJoiningCompany.value = false,
                                ),
                              ),
                              Expanded(
                                child: _ChoiceTab(
                                  label: 'Tham gia công ty',
                                  isSelected: controller.isJoiningCompany.value,
                                  onTap: () => controller.isJoiningCompany.value = true,
                                ),
                              ),
                            ],
                          ),
                        )),
                    const SizedBox(height: 16),

                    Obx(() => controller.isJoiningCompany.value
                        ? TextField(
                            key: const ValueKey('join_company_id'),
                            controller: controller.regJoinCompanyIdController,
                            keyboardType: TextInputType.number,
                            style: const TextStyle(color: Colors.white, fontSize: 14),
                            decoration: InputDecoration(
                              labelText: 'Mã công ty (do người mời cung cấp)',
                              labelStyle: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
                              prefixIcon: const Icon(Icons.key_outlined, color: AppTheme.primary, size: 20),
                              filled: true,
                              fillColor: AppTheme.backgroundDark.withValues(alpha: 0.8),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(10),
                                borderSide: const BorderSide(color: AppTheme.borderDark),
                              ),
                              enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(10),
                                borderSide: const BorderSide(color: AppTheme.borderDark),
                              ),
                              focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(10),
                                borderSide: const BorderSide(color: AppTheme.primary, width: 1.5),
                              ),
                            ),
                          )
                        : TextField(
                            key: const ValueKey('company_name'),
                            controller: controller.regCompanyNameController,
                            style: const TextStyle(color: Colors.white, fontSize: 14),
                            decoration: InputDecoration(
                              labelText: 'Tên công ty',
                              hintText: 'Ví dụ: Acme Inc',
                              hintStyle: const TextStyle(color: AppTheme.textDimDark, fontSize: 12),
                              labelStyle: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
                              prefixIcon: const Icon(Icons.apartment_outlined, color: AppTheme.primary, size: 20),
                              filled: true,
                              fillColor: AppTheme.backgroundDark.withValues(alpha: 0.8),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(10),
                                borderSide: const BorderSide(color: AppTheme.borderDark),
                              ),
                              enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(10),
                                borderSide: const BorderSide(color: AppTheme.borderDark),
                              ),
                              focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(10),
                                borderSide: const BorderSide(color: AppTheme.primary, width: 1.5),
                              ),
                            ),
                          )),
                    const SizedBox(height: 28),

                    // Register Action Button
                    Obx(() => ElevatedButton(
                          onPressed: controller.isRegisterLoading.value
                              ? null
                              : () {
                                  controller.register();
                                },
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.primary,
                            foregroundColor: AppTheme.backgroundDarker,
                            elevation: 8,
                            shadowColor: AppTheme.primary.withValues(alpha: 0.4),
                            minimumSize: const Size(double.infinity, 50),
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(100),
                            ),
                          ),
                          child: controller.isRegisterLoading.value
                              ? const SizedBox(
                                  height: 20,
                                  width: 20,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: AppTheme.backgroundDarker,
                                  ),
                                )
                              : const Text(
                                  'Đăng Ký & Khởi Tạo Brain',
                                  style: TextStyle(
                                    fontSize: 15,
                                    fontWeight: FontWeight.bold,
                                    letterSpacing: 0.5,
                                  ),
                                ),
                        )),
                    const SizedBox(height: 20),

                    // Back to Login Link
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Text(
                          'Đã có tài khoản?',
                          style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
                        ),
                        TextButton(
                          onPressed: () {
                            controller.registerErrorMessage.value = '';
                            Get.offNamed(AppRoutes.login);
                          },
                          child: const Text(
                            'Đăng nhập ngay',
                            style: TextStyle(
                              color: AppTheme.primary,
                              fontWeight: FontWeight.w700,
                              fontSize: 13,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _ChoiceTab extends StatelessWidget {
  final String label;
  final bool isSelected;
  final VoidCallback onTap;

  const _ChoiceTab({required this.label, required this.isSelected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.primary.withValues(alpha: 0.15) : Colors.transparent,
          borderRadius: BorderRadius.circular(8),
          border: isSelected ? Border.all(color: AppTheme.primary.withValues(alpha: 0.5)) : null,
        ),
        child: Text(
          label,
          textAlign: TextAlign.center,
          style: TextStyle(
            color: isSelected ? AppTheme.primary : AppTheme.textMutedDark,
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }
}

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
              constraints: const BoxConstraints(maxWidth: 460),
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
                child: Obx(() {
                  final step = controller.registerStep.value;
                  return Column(
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
                          child: Icon(
                            step == 1 ? Icons.psychology : Icons.apartment,
                            size: 40,
                            color: AppTheme.primary,
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        step == 1 ? 'Tạo Tài Khoản Mới' : 'Thiết Lập Không Gian Làm Việc',
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.w800,
                          color: Colors.white,
                          letterSpacing: -0.5,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        step == 1
                            ? 'Khởi tạo tài khoản danh tính COSA Platform'
                            : 'Tạo hoặc tham gia công ty để đồng bộ dữ liệu Brain về JAVIS Local',
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontSize: 13,
                          color: AppTheme.textMutedDark,
                        ),
                      ),
                      const SizedBox(height: 20),

                      // Step Indicator
                      _StepProgressIndicator(currentStep: step),
                      const SizedBox(height: 24),

                      // Error Message Display
                      if (controller.registerErrorMessage.value.isNotEmpty) ...[
                        Container(
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
                        ),
                      ],

                      // Form content based on Step
                      if (step == 1) ...[
                        _buildStep1AccountForm(context),
                      ] else ...[
                        _buildStep2CompanyForm(context),
                      ],

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
                              controller.clearRegisterForm();
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
                  );
                }),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildStep1AccountForm(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
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
        const SizedBox(height: 28),

        // Next Step Button
        Obx(() => ElevatedButton(
              onPressed: controller.isRegisterLoading.value
                  ? null
                  : () {
                      controller.submitAccountStep();
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
                  : const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          'Tiếp tục: Thiết lập Công ty',
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 0.5,
                          ),
                        ),
                        SizedBox(width: 8),
                        Icon(Icons.arrow_forward, size: 18),
                      ],
                    ),
            )),
      ],
    );
  }

  Widget _buildStep2CompanyForm(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Company choice toggle
        Container(
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
                  icon: Icons.add_business_outlined,
                  isSelected: !controller.isJoiningCompany.value,
                  onTap: () => controller.isJoiningCompany.value = false,
                ),
              ),
              Expanded(
                child: _ChoiceTab(
                  label: 'Tham gia công ty',
                  icon: Icons.group_add_outlined,
                  isSelected: controller.isJoiningCompany.value,
                  onTap: () => controller.isJoiningCompany.value = true,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),

        if (controller.isJoiningCompany.value) ...[
          TextField(
            key: const ValueKey('join_company_id'),
            controller: controller.regJoinCompanyIdController,
            keyboardType: TextInputType.number,
            style: const TextStyle(color: Colors.white, fontSize: 14),
            decoration: InputDecoration(
              labelText: 'Mã công ty (do người mời cung cấp)',
              hintText: 'Ví dụ: 84250971596656640',
              hintStyle: const TextStyle(color: AppTheme.textDimDark, fontSize: 12),
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
          ),
          const SizedBox(height: 8),
          const Text(
            'Nhập mã công ty đã tồn tại để tham gia vào workspace chung.',
            style: TextStyle(fontSize: 11, color: AppTheme.textDimDark),
          ),
        ] else ...[
          TextField(
            key: const ValueKey('company_name'),
            controller: controller.regCompanyNameController,
            style: const TextStyle(color: Colors.white, fontSize: 14),
            decoration: InputDecoration(
              labelText: 'Tên công ty / Tổ chức',
              hintText: 'Ví dụ: VutaSoft, Acme Corp',
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
          ),
          const SizedBox(height: 8),
          const Text(
            'Bạn sẽ là Founder sở hữu công ty và không gian làm việc này.',
            style: TextStyle(fontSize: 11, color: AppTheme.textDimDark),
          ),
        ],

        const SizedBox(height: 28),

        // Complete Action Button
        ElevatedButton(
          onPressed: controller.isRegisterLoading.value
              ? null
              : () {
                  controller.submitCompanyStep();
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
                  'Hoàn Tất & Khởi Tạo Brain',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 0.5,
                  ),
                ),
        ),
        const SizedBox(height: 12),

        // Back to step 1 button
        OutlinedButton(
          onPressed: controller.isRegisterLoading.value
              ? null
              : () {
                  controller.goToPreviousStep();
                },
          style: OutlinedButton.styleFrom(
            foregroundColor: AppTheme.textMutedDark,
            side: const BorderSide(color: AppTheme.borderDark),
            minimumSize: const Size(double.infinity, 44),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(100),
            ),
          ),
          child: const Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.arrow_back, size: 16),
              SizedBox(width: 6),
              Text(
                'Quay lại bước 1',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _StepProgressIndicator extends StatelessWidget {
  final int currentStep;

  const _StepProgressIndicator({required this.currentStep});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _StepBadge(
            stepNumber: 1,
            label: 'Tài khoản',
            isActive: currentStep == 1,
            isCompleted: currentStep > 1,
          ),
        ),
        Container(
          width: 28,
          height: 2,
          margin: const EdgeInsets.symmetric(horizontal: 6),
          color: currentStep > 1 ? AppTheme.primary : AppTheme.borderDark,
        ),
        Expanded(
          child: _StepBadge(
            stepNumber: 2,
            label: 'Công ty & Brain',
            isActive: currentStep == 2,
            isCompleted: false,
          ),
        ),
      ],
    );
  }
}

class _StepBadge extends StatelessWidget {
  final int stepNumber;
  final String label;
  final bool isActive;
  final bool isCompleted;

  const _StepBadge({
    required this.stepNumber,
    required this.label,
    required this.isActive,
    required this.isCompleted,
  });

  @override
  Widget build(BuildContext context) {
    final activeColor = AppTheme.primary;
    final inactiveColor = AppTheme.textMutedDark;
    final borderColor = (isActive || isCompleted) ? activeColor : AppTheme.borderDark;
    final bgColor = isCompleted
        ? activeColor
        : (isActive ? activeColor.withValues(alpha: 0.15) : AppTheme.backgroundDark);

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 10),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: borderColor, width: isActive ? 1.5 : 1),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 20,
            height: 20,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: isCompleted
                  ? AppTheme.backgroundDarker
                  : (isActive ? activeColor : Colors.transparent),
              border: isCompleted ? null : Border.all(color: isActive ? activeColor : inactiveColor),
            ),
            child: Center(
              child: isCompleted
                  ? const Icon(Icons.check, size: 13, color: AppTheme.primary)
                  : Text(
                      '$stepNumber',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        color: isActive ? AppTheme.backgroundDarker : inactiveColor,
                      ),
                    ),
            ),
          ),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              label,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 12,
                fontWeight: (isActive || isCompleted) ? FontWeight.w700 : FontWeight.w500,
                color: isCompleted
                    ? AppTheme.backgroundDarker
                    : (isActive ? Colors.white : inactiveColor),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ChoiceTab extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool isSelected;
  final VoidCallback onTap;

  const _ChoiceTab({
    required this.label,
    required this.icon,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.primary.withValues(alpha: 0.15) : Colors.transparent,
          borderRadius: BorderRadius.circular(8),
          border: isSelected ? Border.all(color: AppTheme.primary.withValues(alpha: 0.5)) : null,
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              icon,
              size: 16,
              color: isSelected ? AppTheme.primary : AppTheme.textMutedDark,
            ),
            const SizedBox(width: 6),
            Flexible(
              child: Text(
                label,
                textAlign: TextAlign.center,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: isSelected ? AppTheme.primary : AppTheme.textMutedDark,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

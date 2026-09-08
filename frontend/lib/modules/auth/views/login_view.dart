import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/auth_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/routing/app_routes.dart';
import '../../../core/localization/app_translations.dart';
import '../../../core/localization/locale_controller.dart';
import 'widgets/auth_language_switcher.dart';

class LoginView extends GetView<AuthController> {
  const LoginView({super.key});

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
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Obx(() {
                    if (Get.isRegistered<LocaleController>()) {
                      Get.find<LocaleController>().current.value;
                    }
                    return Container(
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
                          // Logo Header
                          Center(
                            child: Container(
                              padding: const EdgeInsets.all(14),
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
                                size: 48,
                                color: AppTheme.primary,
                              ),
                            ),
                          ),
                          const SizedBox(height: 18),
                          const Text(
                            'COSA',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 26,
                              fontWeight: FontWeight.w800,
                              letterSpacing: -0.5,
                              color: Colors.white,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            L10nKey.hubSubtitle.tr,
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              fontSize: 13,
                              color: AppTheme.textMutedDark,
                            ),
                          ),
                          const SizedBox(height: 32),

                          // Error Box
                          Obx(() => controller.errorMessage.value.isNotEmpty
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
                                          controller.errorMessage.value,
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

                          // Identifier input
                          TextField(
                            controller: controller.identifierController,
                            style: const TextStyle(color: Colors.white, fontSize: 14),
                            decoration: InputDecoration(
                              labelText: L10nKey.authIdentifierLabel.tr,
                              hintText: L10nKey.authIdentifierHint.tr,
                              hintStyle: const TextStyle(color: AppTheme.textDimDark, fontSize: 12),
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

                          // Password input
                          Obx(() => TextField(
                                controller: controller.passwordController,
                                obscureText: !controller.isPasswordVisible.value,
                                style: const TextStyle(color: Colors.white, fontSize: 14),
                                decoration: InputDecoration(
                                  labelText: L10nKey.authPasswordLabel.tr,
                                  labelStyle: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
                                  prefixIcon: const Icon(Icons.lock_outline, color: AppTheme.primary, size: 20),
                                  suffixIcon: IconButton(
                                    icon: Icon(
                                      controller.isPasswordVisible.value
                                          ? Icons.visibility_outlined
                                          : Icons.visibility_off_outlined,
                                      color: AppTheme.textMutedDark,
                                      size: 20,
                                    ),
                                    onPressed: () {
                                      controller.isPasswordVisible.toggle();
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
                          const SizedBox(height: 14),

                          // Remember Me
                          Obx(() => Row(
                                children: [
                                  SizedBox(
                                    height: 24,
                                    width: 24,
                                    child: Checkbox(
                                      value: controller.rememberMe.value,
                                      onChanged: (value) {
                                        controller.rememberMe.value = value ?? false;
                                      },
                                      activeColor: AppTheme.primary,
                                      checkColor: AppTheme.backgroundDarker,
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Text(
                                    L10nKey.authRememberMe.tr,
                                    style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
                                  ),
                                ],
                              )),
                          const SizedBox(height: 24),

                          // Login button
                          Obx(() => ElevatedButton(
                                onPressed: controller.isLoading.value
                                    ? null
                                    : () {
                                        controller.login();
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
                                child: controller.isLoading.value
                                    ? const SizedBox(
                                        height: 20,
                                        width: 20,
                                        child: CircularProgressIndicator(
                                          strokeWidth: 2,
                                          color: AppTheme.backgroundDarker,
                                        ),
                                      )
                                    : Text(
                                        L10nKey.authLoginButton.tr,
                                        style: const TextStyle(
                                          fontSize: 15,
                                          fontWeight: FontWeight.bold,
                                          letterSpacing: 0.5,
                                        ),
                                      ),
                              )),
                          const SizedBox(height: 20),

                          // Register Link
                          Wrap(
                            alignment: WrapAlignment.center,
                            crossAxisAlignment: WrapCrossAlignment.center,
                            children: [
                              Text(
                                L10nKey.authNoAccount.tr,
                                style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
                              ),
                              TextButton(
                                onPressed: () {
                                  controller.errorMessage.value = '';
                                  controller.clearRegisterForm();
                                  Get.toNamed(AppRoutes.register);
                                },
                                child: Text(
                                  L10nKey.authCreateAccount.tr,
                                  style: const TextStyle(
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
                    );
                  }),
                  const SizedBox(height: 20),
                  const AuthLanguageSwitcher(),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

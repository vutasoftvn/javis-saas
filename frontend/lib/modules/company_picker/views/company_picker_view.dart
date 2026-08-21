import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/company_picker_controller.dart';
import '../../auth/services/auth_service.dart';
import '../../../core/theme/app_theme.dart';

class CompanyPickerView extends GetView<CompanyPickerController> {
  const CompanyPickerView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundDark,
      body: Container(
        decoration: const BoxDecoration(gradient: AppTheme.backgroundRadialGradient),
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Center(
                    child: Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppTheme.primary.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.4)),
                      ),
                      child: const Icon(Icons.apartment_outlined, size: 40, color: AppTheme.primary),
                    ),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Chọn công ty',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: Colors.white),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Tài khoản của bạn thuộc nhiều công ty - chọn công ty muốn làm việc trên máy này',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 13, color: AppTheme.textMutedDark),
                  ),
                  const SizedBox(height: 24),

                  Obx(() => controller.errorMessage.value.isNotEmpty
                      ? Container(
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                          margin: const EdgeInsets.only(bottom: 16),
                          decoration: BoxDecoration(
                            color: AppTheme.accent.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: AppTheme.accent.withValues(alpha: 0.6)),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.error_outline, size: 20, color: AppTheme.accent),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  controller.errorMessage.value,
                                  style: const TextStyle(color: AppTheme.accentLight, fontSize: 13),
                                ),
                              ),
                            ],
                          ),
                        )
                      : const SizedBox.shrink()),

                  ...controller.companies.map((c) => _CompanyTile(company: c)),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _CompanyTile extends StatelessWidget {
  final CompanyMembershipInfo company;

  const _CompanyTile({required this.company});

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<CompanyPickerController>();
    return Obx(() {
      final isSelecting = controller.selectingCompanyId.value == company.companyId;
      final isDisabled = controller.isLoading.value;

      return Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Material(
          color: AppTheme.surfaceDark.withValues(alpha: 0.85),
          borderRadius: BorderRadius.circular(12),
          child: InkWell(
            borderRadius: BorderRadius.circular(12),
            onTap: isDisabled ? null : () => controller.selectCompany(company.companyId),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.borderDark),
              ),
              child: Row(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: AppTheme.primary.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.business_outlined, color: AppTheme.primary, size: 20),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          company.name ?? 'Company #${company.companyId}',
                          style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          company.roleId,
                          style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                  if (isSelecting)
                    const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.primary),
                    )
                  else
                    const Icon(Icons.chevron_right, color: AppTheme.textMutedDark),
                ],
              ),
            ),
          ),
        ),
      );
    });
  }
}

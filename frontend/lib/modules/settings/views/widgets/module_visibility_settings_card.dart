import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/localization/app_translations.dart';
import '../../../../core/services/module_visibility_controller.dart';
import '../../../../core/session/session_controller.dart';
import '../../../../core/theme/app_theme.dart';

class ModuleVisibilitySettingsCard extends StatefulWidget {
  const ModuleVisibilitySettingsCard({super.key});

  @override
  State<ModuleVisibilitySettingsCard> createState() => _ModuleVisibilitySettingsCardState();
}

class _ModuleVisibilitySettingsCardState extends State<ModuleVisibilitySettingsCard> {
  bool _isUpdating = false;
  String? _errorMessage;

  bool _checkIsOperator() {
    if (!Get.isRegistered<SessionController>()) return false;
    final role = Get.find<SessionController>().active.value?.role.toLowerCase() ?? '';
    return role == 'founder' || role == 'co-founder' || role == 'admin' || role == 'owner';
  }

  Future<void> _toggleUserVisible(
    ModuleVisibilityController controller,
    OptionalModule module,
    bool value,
  ) async {
    setState(() {
      _isUpdating = true;
      _errorMessage = null;
    });

    final success = await controller.setMyVisible(module, value);
    if (!mounted) return;
    setState(() {
      _isUpdating = false;
      if (!success) {
        _errorMessage = L10nKey.settingsModuleUpdateError.tr;
      }
    });
  }

  Future<void> _toggleWorkspaceEnabled(
    ModuleVisibilityController controller,
    OptionalModule module,
    bool value,
  ) async {
    setState(() {
      _isUpdating = true;
      _errorMessage = null;
    });

    final success = await controller.setWorkspaceEnabled(module, value);
    if (!mounted) return;
    setState(() {
      _isUpdating = false;
      if (!success) {
        _errorMessage = L10nKey.settingsModuleUpdateError.tr;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<ModuleVisibilityController>()) {
      Get.put(ModuleVisibilityController());
    }
    final controller = Get.find<ModuleVisibilityController>();
    final isOperator = _checkIsOperator();

    return Container(
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.borderDark),
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppTheme.primary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.dashboard_customize_outlined, color: AppTheme.primary, size: 22),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      L10nKey.settingsModulesTitle.tr,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.textDark,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      L10nKey.settingsModulesSubtitle.tr,
                      style: const TextStyle(
                        fontSize: 13,
                        color: AppTheme.textMutedDark,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (_errorMessage != null) ...[
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: Colors.red.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.red.withValues(alpha: 0.3)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.error_outline, color: Colors.red, size: 18),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _errorMessage!,
                      style: const TextStyle(color: Colors.red, fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 16),
          const Divider(height: 1, color: AppTheme.borderDark),
          const SizedBox(height: 12),
          Obx(() {
            final modules = [OptionalModule.finance, OptionalModule.legal, OptionalModule.crm];
            return Column(
              children: modules.map((m) {
                final entry = controller.entries[m];
                final userVisible = entry?.userVisible ?? true;
                final wsEnabled = entry?.workspaceEnabled ?? true;

                final (icon, nameKey) = switch (m) {
                  OptionalModule.finance => (Icons.account_balance_wallet_outlined, L10nKey.moduleFinance),
                  OptionalModule.legal => (Icons.gavel_outlined, L10nKey.moduleLegal),
                  OptionalModule.crm => (Icons.point_of_sale_rounded, L10nKey.moduleCrm),
                };

                return Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: AppTheme.surfaceDark.withValues(alpha: 0.5),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppTheme.borderDark.withValues(alpha: 0.6)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(icon, size: 20, color: AppTheme.primary),
                          const SizedBox(width: 10),
                          Text(
                            nameKey.tr,
                            style: const TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                              color: AppTheme.textDark,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            L10nKey.settingsModuleUserVisible.tr,
                            style: const TextStyle(fontSize: 13, color: AppTheme.textDark),
                          ),
                          Switch(
                            value: userVisible,
                            onChanged: _isUpdating
                                ? null
                                : (v) => _toggleUserVisible(controller, m, v),
                            activeThumbColor: AppTheme.primary,
                          ),
                        ],
                      ),
                      if (isOperator) ...[
                        const Divider(height: 16, color: AppTheme.borderDark),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              L10nKey.settingsModuleWorkspaceEnabled.tr,
                              style: const TextStyle(fontSize: 13, color: AppTheme.textDark),
                            ),
                            Switch(
                              value: wsEnabled,
                              onChanged: _isUpdating
                                  ? null
                                  : (v) => _toggleWorkspaceEnabled(controller, m, v),
                              activeThumbColor: AppTheme.primary,
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                );
              }).toList(),
            );
          }),
        ],
      ),
    );
  }
}

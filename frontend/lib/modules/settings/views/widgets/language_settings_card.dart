import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/localization/app_translations.dart';
import '../../../../core/localization/locale_controller.dart';
import '../../../../core/localization/supported_locale.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_toast.dart';

/// Glassmorphic Language Settings Card for SettingsView.
/// Allows instant switching between Vietnamese and English with visual feedback.
class LanguageSettingsCard extends StatefulWidget {
  const LanguageSettingsCard({super.key});

  @override
  State<LanguageSettingsCard> createState() => _LanguageSettingsCardState();
}

class _LanguageSettingsCardState extends State<LanguageSettingsCard> {
  bool _isSaving = false;

  Future<void> _changeLocale(SupportedLocale locale) async {
    if (!Get.isRegistered<LocaleController>()) return;
    final lc = Get.find<LocaleController>();
    if (lc.current.value == locale) return;

    setState(() => _isSaving = true);
    try {
      await lc.updatePreference(locale);
      AppToast.success(
        locale == SupportedLocale.enUS
            ? 'Language updated to English'
            : 'Đã cập nhật ngôn ngữ sang Tiếng Việt',
      );
    } catch (_) {
      await lc.setLocale(locale);
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final lc = Get.isRegistered<LocaleController>()
        ? Get.find<LocaleController>()
        : null;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.borderDark),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.25),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppTheme.primary.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: AppTheme.primary.withValues(alpha: 0.3),
                    width: 0.8,
                  ),
                ),
                child: const Icon(
                  Icons.translate_rounded,
                  color: AppTheme.primary,
                  size: 22,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      L10nKey.settingsLanguageTitle.tr,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.textDark,
                        letterSpacing: 0.2,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      L10nKey.settingsLanguageSubtitle.tr,
                      style: const TextStyle(
                        fontSize: 13,
                        color: AppTheme.textMutedDark,
                        height: 1.3,
                      ),
                    ),
                  ],
                ),
              ),
              if (_isSaving)
                const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor: AlwaysStoppedAnimation<Color>(AppTheme.primary),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 16),
          const Divider(height: 1, color: AppTheme.borderDark),
          const SizedBox(height: 16),
          if (lc != null)
            Obx(() {
              final current = lc.current.value;
              return Row(
                children: [
                  Expanded(
                    child: _LanguageOptionTile(
                      key: const Key('settings_lang_vi'),
                      label: 'Tiếng Việt',
                      flagEmoji: '🇻🇳',
                      subLabel: 'Mặc định (vi-VN)',
                      isSelected: current == SupportedLocale.viVN,
                      isDisabled: _isSaving,
                      onTap: () => _changeLocale(SupportedLocale.viVN),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: _LanguageOptionTile(
                      key: const Key('settings_lang_en'),
                      label: 'English',
                      flagEmoji: '🇺🇸',
                      subLabel: 'International (en-US)',
                      isSelected: current == SupportedLocale.enUS,
                      isDisabled: _isSaving,
                      onTap: () => _changeLocale(SupportedLocale.enUS),
                    ),
                  ),
                ],
              );
            }),
        ],
      ),
    );
  }
}

class _LanguageOptionTile extends StatelessWidget {
  final String label;
  final String flagEmoji;
  final String subLabel;
  final bool isSelected;
  final bool isDisabled;
  final VoidCallback onTap;

  const _LanguageOptionTile({
    super.key,
    required this.label,
    required this.flagEmoji,
    required this.subLabel,
    required this.isSelected,
    required this.isDisabled,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final activeColor = AppTheme.primary;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: isDisabled ? null : onTap,
        borderRadius: BorderRadius.circular(12),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeInOut,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          decoration: BoxDecoration(
            color: isSelected
                ? activeColor.withValues(alpha: 0.12)
                : AppTheme.surfaceDarkHeader.withValues(alpha: 0.6),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: isSelected
                  ? activeColor.withValues(alpha: 0.7)
                  : AppTheme.borderDark,
              width: isSelected ? 1.5 : 1.0,
            ),
            boxShadow: isSelected
                ? [
                    BoxShadow(
                      color: activeColor.withValues(alpha: 0.18),
                      blurRadius: 12,
                      offset: const Offset(0, 2),
                    ),
                  ]
                : null,
          ),
          child: Row(
            children: [
              Text(
                flagEmoji,
                style: const TextStyle(fontSize: 24),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      style: TextStyle(
                        fontSize: 14.5,
                        fontWeight: isSelected ? FontWeight.bold : FontWeight.w600,
                        color: isSelected ? Colors.white : AppTheme.textDark,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      subLabel,
                      style: TextStyle(
                        fontSize: 11.5,
                        color: isSelected
                            ? activeColor.withValues(alpha: 0.9)
                            : AppTheme.textMutedDark,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(
                isSelected
                    ? Icons.radio_button_checked_rounded
                    : Icons.radio_button_off_rounded,
                size: 20,
                color: isSelected ? activeColor : AppTheme.textMutedDark,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

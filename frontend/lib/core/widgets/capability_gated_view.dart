import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../manifest/test_capability_manifest.dart';

/// Capability-gated view container (P1.3, TEST_READINESS_REAUDIT_2026-08-26.md).
/// Displays a graceful "Under Development / Capability Gated" view when the
/// required backend domain is disabled in the capability manifest.
class CapabilityGatedView extends StatelessWidget {
  final String moduleName;
  final bool isEnabled;
  final Widget child;
  final String? customMessage;
  final IconData icon;

  const CapabilityGatedView({
    super.key,
    required this.moduleName,
    required this.isEnabled,
    required this.child,
    this.customMessage,
    this.icon = Icons.construction_rounded,
  });

  /// Factory helper that automatically inspects the current TestCapabilityManifest.
  factory CapabilityGatedView.gated({
    Key? key,
    required String moduleName,
    required bool Function(TestCapabilityManifest manifest) capabilitySelector,
    required Widget child,
    String? customMessage,
    IconData icon = Icons.construction_rounded,
    TestCapabilityManifest? manifest,
  }) {
    final effectiveManifest = manifest ?? TestCapabilityManifest.current;
    final enabled = capabilitySelector(effectiveManifest);
    return CapabilityGatedView(
      key: key,
      moduleName: moduleName,
      isEnabled: enabled,
      customMessage: customMessage,
      icon: icon,
      child: child,
    );
  }

  @override
  Widget build(BuildContext context) {
    if (isEnabled) {
      return child;
    }

    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: Text(moduleName),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () {
            if (Navigator.of(context).canPop()) {
              Get.back();
            } else {
              Get.offAllNamed('/dashboard');
            }
          },
        ),
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 32.0),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: Container(
              padding: const EdgeInsets.all(32.0),
              decoration: BoxDecoration(
                color: colorScheme.surfaceContainerHighest.withValues(alpha: 0.3),
                borderRadius: BorderRadius.circular(16.0),
                border: Border.all(
                  color: colorScheme.outlineVariant.withValues(alpha: 0.5),
                ),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 72,
                    height: 72,
                    decoration: BoxDecoration(
                      color: colorScheme.primaryContainer.withValues(alpha: 0.4),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      icon,
                      size: 36,
                      color: colorScheme.primary,
                    ),
                  ),
                  const SizedBox(height: 20),
                  Text(
                    moduleName,
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.amber.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.amber.withValues(alpha: 0.5)),
                    ),
                    child: Text(
                      'Preview / Capability Gated',
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: Colors.amber[800],
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    customMessage ??
                        '$moduleName backend capabilities are currently in development or gated in this environment.',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.textTheme.bodyMedium?.color?.withValues(alpha: 0.8),
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 24),
                  FilledButton.icon(
                    onPressed: () {
                      if (Navigator.of(context).canPop()) {
                        Get.back();
                      } else {
                        Get.offAllNamed('/dashboard');
                      }
                    },
                    icon: const Icon(Icons.arrow_back),
                    label: const Text('Return to Safety'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

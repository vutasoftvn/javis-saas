import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/manifest/test_capability_manifest.dart';
import 'package:frontend/core/widgets/capability_gated_view.dart';

void main() {
  group('CapabilityGatedView Widget Tests (P1.3)', () {
    testWidgets('Renders child view when capability is enabled', (WidgetTester tester) async {
      await tester.pumpWidget(
        GetMaterialApp(
          home: CapabilityGatedView.gated(
            moduleName: 'Enabled Module',
            capabilitySelector: (m) => true,
            child: const Text('Child Content Rendered'),
          ),
        ),
      );

      expect(find.text('Child Content Rendered'), findsOneWidget);
      expect(find.text('Preview / Capability Gated'), findsNothing);
    });

    testWidgets('Renders gated placeholder when capability is disabled', (WidgetTester tester) async {
      const manifestWithDisabledVault = TestCapabilityManifest(
        vaultSupported: false,
      );

      await tester.pumpWidget(
        GetMaterialApp(
          home: CapabilityGatedView.gated(
            moduleName: 'Vault & Knowledge Store',
            manifest: manifestWithDisabledVault,
            capabilitySelector: (m) => m.vaultSupported,
            child: const Text('Sensitive Child Data'),
          ),
        ),
      );

      expect(find.text('Sensitive Child Data'), findsNothing);
      expect(find.text('Vault & Knowledge Store'), findsNWidgets(2)); // AppBar title + Header
      expect(find.text('Preview / Capability Gated'), findsOneWidget);
      expect(find.text('Return to Safety'), findsOneWidget);
    });
  });
}

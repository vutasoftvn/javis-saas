import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/settings/workforce/views/profile_composition_view.dart';

void main() {
  testWidgets('ProfileCompositionView displays missing capability and permission separately', (tester) async {
    final items = [
      const AgentReadinessItem(
        profileId: 'operations',
        profileName: 'Operations Agent',
        missingCapabilities: ['strategy.project.get', 'strategy.next_best_action.get'],
        missingPermissions: ['WRITE_STAGE'],
        isReady: false,
      ),
      const AgentReadinessItem(
        profileId: 'customer_support',
        profileName: 'Customer Support Copilot',
        missingCapabilities: [],
        missingPermissions: [],
        isReady: true,
      ),
    ];

    await tester.pumpWidget(
      MaterialApp(
        home: ProfileCompositionView(items: items),
      ),
    );

    // 1. Phải tìm thấy card operations và customer_support
    expect(find.byKey(const ValueKey('card_operations')), findsOneWidget);
    expect(find.byKey(const ValueKey('card_customer_support')), findsOneWidget);

    // 2. Customer support is ready
    expect(find.byKey(const ValueKey('ready_customer_support')), findsOneWidget);

    // 3. Operations displays Missing Capabilities separately
    expect(find.byKey(const ValueKey('missing_capabilities_operations')), findsOneWidget);
    expect(find.text('• strategy.project.get'), findsOneWidget);
    expect(find.text('• strategy.next_best_action.get'), findsOneWidget);

    // 4. Operations displays Missing Permissions separately
    expect(find.byKey(const ValueKey('missing_permissions_operations')), findsOneWidget);
    expect(find.text('• WRITE_STAGE'), findsOneWidget);
  });
}

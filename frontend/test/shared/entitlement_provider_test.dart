import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/shared/providers/entitlement_provider.dart';

void main() {
  group('EntitlementProvider', () {
    test('hasFeature returns false by default (fail-closed) before loading', () {
      final provider = EntitlementProvider();
      expect(provider.hasFeature('finance'), isFalse);
      expect(provider.hasFeature('strategy'), isFalse);
      expect(provider.hasFeature('unknown'), isFalse);
      expect(provider.loadedWorkspaceId, isNull);
    });

    test('hasFeature returns true only for enabled features when loaded', () {
      final provider = EntitlementProvider();
      provider.setEntitlementForTesting(
        features: {
          'strategy': true,
          'operations': true,
          'finance': false,
        },
        limits: {'max_members': 1},
      );

      expect(provider.hasFeature('strategy'), isTrue);
      expect(provider.hasFeature('operations'), isTrue);
      expect(provider.hasFeature('finance'), isFalse);
      expect(provider.getLimit('max_members'), 1);
    });

    test('reset clears features and returns to fail-closed state', () {
      final provider = EntitlementProvider();
      provider.setEntitlementForTesting(
        features: {'strategy': true},
      );
      expect(provider.hasFeature('strategy'), isTrue);

      provider.reset();
      expect(provider.hasFeature('strategy'), isFalse);
      expect(provider.loadedWorkspaceId, isNull);
    });
  });
}

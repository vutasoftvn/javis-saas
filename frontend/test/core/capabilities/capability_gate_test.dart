import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/capabilities/capability_gate.dart';

void main() {
  setUp(() {
    CapabilityGate.reset();
  });

  group('CapabilityGate & TestCapabilityManifest (Task 5)', () {
    test('default manifest allows sandbox-read and blocks arbitrary connectors', () {
      expect(CapabilityGate.canUseConnector('sandbox-read'), isTrue);
      expect(CapabilityGate.canUseConnector('arbitrary-shell-connector'), isFalse);
    });

    test('default manifest allows finite schedule kinds and blocks arbitrary cron', () {
      expect(CapabilityGate.canCreateSchedule('one_time'), isTrue);
      expect(CapabilityGate.canCreateSchedule('daily'), isTrue);
      expect(CapabilityGate.canCreateSchedule('weekdays'), isTrue);
      expect(CapabilityGate.canCreateSchedule('cron_expr'), isFalse);
    });

    test('supported artifact kinds check', () {
      expect(CapabilityGate.isArtifactSupported('assistant_output'), isTrue);
      expect(CapabilityGate.isArtifactSupported('report'), isTrue);
      expect(CapabilityGate.isArtifactSupported('table'), isTrue);
      expect(CapabilityGate.isArtifactSupported('file_export'), isTrue);
      expect(CapabilityGate.isArtifactSupported('binary_executable'), isFalse);
    });

    test('override manifest dynamically for test environments', () {
      CapabilityGate.overrideManifest(
        const TestCapabilityManifest(
          enabledConnectorKeys: ['custom-connector'],
          enabledScheduleKinds: ['one_time'],
        ),
      );

      expect(CapabilityGate.canUseConnector('custom-connector'), isTrue);
      expect(CapabilityGate.canUseConnector('sandbox-read'), isFalse);
      expect(CapabilityGate.canCreateSchedule('daily'), isFalse);
    });
  });
}

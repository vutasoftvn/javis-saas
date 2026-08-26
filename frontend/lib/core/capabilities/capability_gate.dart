import 'package:flutter/foundation.dart';

class TestCapabilityManifest {
  static const List<String> defaultEnabledConnectors = ['sandbox-read'];
  static const List<String> defaultEnabledSchedules = [
    'one_time',
    'daily',
    'weekdays',
  ];
  static const List<String> defaultSupportedArtifacts = [
    'assistant_output',
    'report',
    'table',
    'file_export',
  ];

  final List<String> enabledConnectorKeys;
  final List<String> enabledScheduleKinds;
  final List<String> supportedArtifactKinds;

  const TestCapabilityManifest({
    this.enabledConnectorKeys = defaultEnabledConnectors,
    this.enabledScheduleKinds = defaultEnabledSchedules,
    this.supportedArtifactKinds = defaultSupportedArtifacts,
  });
}

class CapabilityGate {
  static TestCapabilityManifest _manifest = const TestCapabilityManifest();

  static TestCapabilityManifest get manifest => _manifest;

  @visibleForTesting
  static void overrideManifest(TestCapabilityManifest manifest) {
    _manifest = manifest;
  }

  @visibleForTesting
  static void reset() {
    _manifest = const TestCapabilityManifest();
  }

  static bool canUseConnector(String connectorKey) {
    return _manifest.enabledConnectorKeys.contains(connectorKey);
  }

  static bool canCreateSchedule(String scheduleKind) {
    return _manifest.enabledScheduleKinds.contains(scheduleKind);
  }

  static bool isArtifactSupported(String artifactKind) {
    return _manifest.supportedArtifactKinds.contains(artifactKind);
  }
}

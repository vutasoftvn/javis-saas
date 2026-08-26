/// Test & Environment Capability Manifest (P0.5, TEST_READINESS_ADJUSTMENT_PLAN_2026-08-26.md)
/// Declares runtime capabilities, supported API contracts, and feature flags
/// to ensure test suites and UI components adapt dynamically.
class TestCapabilityManifest {
  final bool companyMicroservicesSupported;
  final bool cosaControlPlaneSupported;
  final bool agentOsSupported;
  final bool localWorkerSupported;
  final bool offlineModeSupported;
  final bool legacyExtensionsSupported;
  final String contractVersion;

  const TestCapabilityManifest({
    this.companyMicroservicesSupported = true,
    this.cosaControlPlaneSupported = true,
    this.agentOsSupported = true,
    this.localWorkerSupported = true,
    this.offlineModeSupported = true,
    this.legacyExtensionsSupported = false,
    this.contractVersion = '2026-08-26',
  });

  static const TestCapabilityManifest current = TestCapabilityManifest();

  Map<String, dynamic> toJson() => {
        'companyMicroservicesSupported': companyMicroservicesSupported,
        'cosaControlPlaneSupported': cosaControlPlaneSupported,
        'agentOsSupported': agentOsSupported,
        'localWorkerSupported': localWorkerSupported,
        'offlineModeSupported': offlineModeSupported,
        'legacyExtensionsSupported': legacyExtensionsSupported,
        'contractVersion': contractVersion,
      };
}

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/services/workspace_capability_manifest_model.dart';
import 'package:frontend/core/widgets/surface_state_view.dart';

Widget _host(Widget child) => MaterialApp(home: Scaffold(body: child));

CapabilityManifestSurface _surface({String? releaseNote}) => CapabilityManifestSurface(
      surfaceKey: 'k',
      moduleKey: 'm',
      featureKey: 'f',
      surfaceStatus: SurfaceStatus.planned,
      requiredCapabilities: const [],
      requiredConnectorKeys: const [],
      entitled: true,
      reasons: const [],
      contractEndpoint: null,
      releaseNote: releaseNote,
      updatedAt: null,
    );

void main() {
  testWidgets('AVAILABLE renders the child directly', (t) async {
    await t.pumpWidget(_host(SurfaceStateView(
      status: SurfaceStatus.available,
      child: const Text('LIVE'),
    )));
    expect(find.text('LIVE'), findsOneWidget);
    expect(find.byKey(const Key('surface_state_planned')), findsNothing);
  });

  testWidgets('PILOT shows a Pilot badge and still renders the child', (t) async {
    await t.pumpWidget(_host(SurfaceStateView(
      status: SurfaceStatus.pilot,
      pilotNote: 'limited cohort',
      child: const Text('LIVE'),
    )));
    expect(find.byKey(const Key('surface_state_pilot')), findsOneWidget);
    expect(find.text('Pilot'), findsOneWidget);
    expect(find.text('limited cohort'), findsOneWidget);
    expect(find.text('LIVE'), findsOneWidget);
  });

  testWidgets('CONFIGURATION_REQUIRED shows a setup CTA when provided', (t) async {
    var tapped = false;
    await t.pumpWidget(_host(SurfaceStateView(
      status: SurfaceStatus.configurationRequired,
      surface: _surface(releaseNote: 'connect CAS first'),
      onConfigure: () => tapped = true,
      child: const Text('LIVE'),
    )));
    expect(find.byKey(const Key('surface_state_configuration_required')), findsOneWidget);
    expect(find.text('connect CAS first'), findsOneWidget);
    expect(find.text('LIVE'), findsNothing);
    await t.tap(find.text('Thiết lập'));
    expect(tapped, isTrue);
  });

  testWidgets('PLANNED shows roadmap text and no action button', (t) async {
    await t.pumpWidget(_host(SurfaceStateView(
      status: SurfaceStatus.planned,
      surface: _surface(releaseNote: 'coming in R1.1'),
      onConfigure: () {},
      onRetry: () {},
      child: const Text('LIVE'),
    )));
    expect(find.byKey(const Key('surface_state_planned')), findsOneWidget);
    expect(find.text('coming in R1.1'), findsOneWidget);
    expect(find.text('LIVE'), findsNothing);
    expect(find.byType(FilledButton), findsNothing);
    expect(find.widgetWithText(FilledButton, 'Thiết lập'), findsNothing);
  });

  testWidgets('UNAVAILABLE shows a retry action', (t) async {
    var retried = false;
    await t.pumpWidget(_host(SurfaceStateView(
      status: SurfaceStatus.unavailable,
      onRetry: () => retried = true,
      child: const Text('LIVE'),
    )));
    expect(find.byKey(const Key('surface_state_unavailable')), findsOneWidget);
    expect(find.text('LIVE'), findsNothing);
    await t.tap(find.text('Thử lại'));
    expect(retried, isTrue);
  });
}

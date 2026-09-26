import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/hologram_hub/presentation/widgets/cyber_circuit_background.dart';
import 'package:frontend/modules/hologram_hub/presentation/widgets/planet_hologram_inspector_dialog.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('PlanetHologramData Model Tests', () {
    test('contains all 8 solar system planets with sacred Trống Đồng mappings', () {
      expect(PlanetHologramData.allPlanets.length, equals(8));

      final ids = PlanetHologramData.allPlanets.map((p) => p.id).toList();
      expect(ids, containsAll([
        'mercury',
        'venus',
        'earth',
        'mars',
        'jupiter',
        'saturn',
        'uranus',
        'neptune',
      ]));
    });

    test('verifies specific celestial features of key planets', () {
      final saturn = PlanetHologramData.findById('saturn')!;
      expect(saturn.hasRings, isTrue);
      expect(saturn.nameVi, equals('Thổ Tinh'));
      expect(saturn.nameEn, equals('Saturn'));
      expect(saturn.cosaBadgeVi, equals('QUẢN TRỊ & PHÁP TRỊ'));
      expect(saturn.cosaBadgeEn, equals('GOVERNANCE & LAW'));

      final earth = PlanetHologramData.findById('earth')!;
      expect(earth.hasMoon, isTrue);
      expect(earth.nameVi, equals('Trái Đất'));
      expect(earth.nameEn, equals('Earth'));
      expect(earth.cosaBadgeVi, equals('THỊ TRƯỜNG & PMF'));
      expect(earth.cosaBadgeEn, equals('TARGET MARKET & PMF'));

      final jupiter = PlanetHologramData.findById('jupiter')!;
      expect(jupiter.hasStripes, isTrue);
      expect(jupiter.nameVi, equals('Mộc Tinh'));
      expect(jupiter.nameEn, equals('Jupiter'));
      expect(jupiter.cosaBadgeVi, equals('TĂNG TRƯỞNG & VỐN'));
      expect(jupiter.cosaBadgeEn, equals('SCALE & CAPITAL'));

      final mars = PlanetHologramData.findById('mars')!;
      expect(mars.hasPolarCap, isTrue);
      expect(mars.nameVi, equals('Hỏa Tinh'));
      expect(mars.nameEn, equals('Mars'));
      expect(mars.cosaBadgeVi, equals('TIÊN PHONG ĐỘT PHÁ'));
      expect(mars.cosaBadgeEn, equals('BOLD EXPERIMENTS'));

      final mercury = PlanetHologramData.findById('mercury')!;
      expect(mercury.nameVi, equals('Thủy Tinh'));
      expect(mercury.nameEn, equals('Mercury'));
      expect(mercury.cosaBadgeVi, equals('TỐC ĐỘ PHẢN HỒI'));
      expect(mercury.cosaBadgeEn, equals('AGILE RESPONSE'));

      final uranus = PlanetHologramData.findById('uranus')!;
      expect(uranus.hasVerticalRing, isTrue);
      expect(uranus.nameVi, equals('Thiên Vương'));
      expect(uranus.nameEn, equals('Uranus'));
      expect(uranus.cosaBadgeVi, equals('DEEP-TECH MOAT'));
    });

    test('verifies bilingual localized getters across all 8 planets', () {
      for (final planet in PlanetHologramData.allPlanets) {
        expect(planet.name(false), equals(planet.nameVi));
        expect(planet.name(true), equals(planet.nameEn));

        expect(planet.localizedCosaRole(false), equals(planet.cosaRoleVi));
        expect(planet.localizedCosaRole(true), equals(planet.cosaRoleEn));

        expect(planet.localizedCosaBadge(false), equals(planet.cosaBadgeVi));
        expect(planet.localizedCosaBadge(true), equals(planet.cosaBadgeEn));

        expect(planet.localizedCosaDescription(false), equals(planet.cosaDescriptionVi));
        expect(planet.localizedCosaDescription(true), equals(planet.cosaDescriptionEn));

        expect(planet.localizedCosaMetric(false), equals(planet.cosaMetricVi));
        expect(planet.localizedCosaMetric(true), equals(planet.cosaMetricEn));

        expect(planet.localizedChineseStarName(false), equals(planet.chineseStarNameVi));
        expect(planet.localizedChineseStarName(true), equals(planet.chineseStarNameEn));

        expect(planet.localizedSolarDistance(false), equals(planet.solarDistanceVi));
        expect(planet.localizedSolarDistance(true), equals(planet.solarDistanceEn));

        expect(planet.localizedOrbitalPeriod(false), equals(planet.orbitalPeriodVi));
        expect(planet.localizedOrbitalPeriod(true), equals(planet.orbitalPeriodEn));

        expect(planet.localizedSurfaceTemp(false), equals(planet.surfaceTempVi));
        expect(planet.localizedSurfaceTemp(true), equals(planet.surfaceTempEn));

        expect(planet.localizedKeyFeatures(false), equals(planet.keyFeaturesVi));
        expect(planet.localizedKeyFeatures(true), equals(planet.keyFeaturesEn));
      }
    });
  });

  group('PlanetHologramInspectorDialog Widget Tests', () {
    testWidgets('renders dialog for Saturn with Vietnamese language when isEn is false', (tester) async {
      final saturn = PlanetHologramData.findById('saturn')!;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: PlanetHologramInspectorDialog(
              planet: saturn,
              isEn: false,
            ),
          ),
        ),
      );

      // Verify Vietnamese Top Bar
      expect(find.textContaining('THỔ TINH'), findsWidgets);
      expect(find.text('♄'), findsOneWidget);

      // Verify Vietnamese COSA OS Section
      expect(find.text('BIỂU TƯỢNG COSA OS'), findsOneWidget);
      expect(find.text('QUẢN TRỊ & PHÁP TRỊ'), findsOneWidget);
      expect(find.textContaining('Tuân thủ SLA'), findsOneWidget);

      // Verify Vietnamese Astronomical Specs
      expect(find.text('THÔNG SỐ THIÊN VĂN'), findsOneWidget);
      expect(find.text('Trấn Tinh (Thổ Đức)'), findsOneWidget);
      expect(find.text('1.43 tỷ km (9.58 AU)'), findsOneWidget);

      // Advance frames for rotating 3D preview
      await tester.pump(const Duration(milliseconds: 300));
      expect(find.byType(CustomPaint), findsWidgets);
    });

    testWidgets('renders dialog for Saturn with English language when isEn is true', (tester) async {
      final saturn = PlanetHologramData.findById('saturn')!;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: PlanetHologramInspectorDialog(
              planet: saturn,
              isEn: true,
            ),
          ),
        ),
      );

      // Verify English Top Bar
      expect(find.textContaining('SATURN'), findsWidgets);
      expect(find.text('♄'), findsOneWidget);

      // Verify English COSA OS Section
      expect(find.text('COSA OS ARCHITECTURAL METAPHOR'), findsOneWidget);
      expect(find.text('GOVERNANCE & LAW'), findsOneWidget);
      expect(find.textContaining('SLA Compliance'), findsOneWidget);

      // Verify English Astronomical Specs
      expect(find.text('ASTRONOMICAL SPECIFICATIONS'), findsOneWidget);
      expect(find.text('Zhenxing (Saturn Star - Earth Virtue)'), findsOneWidget);
      expect(find.text('1.43B km (9.58 AU)'), findsOneWidget);

      // Verify English Orbital Mechanics
      expect(find.text('TRỐNG ĐỒNG ORBITAL MECHANICS'), findsOneWidget);
      expect(find.text('Drum Radius Ratio'), findsOneWidget);

      await tester.pump(const Duration(milliseconds: 300));
      expect(find.byType(CustomPaint), findsWidgets);
    });

    testWidgets('renders dialog for Earth with Moon and closes when ✕ button is pressed', (tester) async {
      final earth = PlanetHologramData.findById('earth')!;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) {
                return ElevatedButton(
                  onPressed: () => PlanetHologramInspectorDialog.show(context, earth, isEn: false),
                  child: const Text('Open Inspector'),
                );
              },
            ),
          ),
        ),
      );

      // Tap open
      await tester.tap(find.text('Open Inspector'));
      await tester.pump(const Duration(milliseconds: 350));

      expect(find.textContaining('TRÁI ĐẤT'), findsWidgets);
      expect(find.text('THỊ TRƯỜNG & PMF'), findsOneWidget);

      // Tap close button ✕
      final closeBtn = find.byIcon(Icons.close_rounded);
      expect(closeBtn, findsOneWidget);
      await tester.tap(closeBtn);
      await tester.pump(const Duration(milliseconds: 350));

      // Dialog is dismissed
      expect(find.text('THỊ TRƯỜNG & PMF'), findsNothing);
    });
  });

  group('CyberCircuitBackground Planet Tap & Hitbox Tests', () {
    testWidgets('triggers onPlanetTap callback when tapped near a moving planet', (tester) async {
      PlanetHologramData? tappedPlanet;

      // Set fixed screen size 800x800
      tester.view.physicalSize = const Size(800, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CyberCircuitBackground(
              isEn: false,
              onPlanetTap: (planet) {
                tappedPlanet = planet;
              },
              child: const SizedBox.expand(),
            ),
          ),
        ),
      );

      await tester.pump(const Duration(milliseconds: 100));

      const center = Offset(400, 400);
      const drumRadius = 190.0;

      // Pick Saturn: orbitRatio = 0.89, startAngle = alignmentAxis (-pi / 3.8)
      final saturn = PlanetHologramData.findById('saturn')!;
      final saturnOrbit = drumRadius * saturn.orbitRatio;
      final saturnX = center.dx + math.cos(saturn.startAngle) * saturnOrbit;
      final saturnY = center.dy + math.sin(saturn.startAngle) * saturnOrbit;
      final saturnPos = Offset(saturnX, saturnY);

      // Tap within the generous hitbox (~36px) of Saturn
      final gesture = await tester.startGesture(saturnPos + const Offset(2, 2));
      await tester.pump(const Duration(milliseconds: 50));
      await gesture.up();
      await tester.pump(const Duration(milliseconds: 100));

      expect(tappedPlanet, isNotNull);
      expect(tappedPlanet!.id, equals('saturn'));
    });

    testWidgets('opens PlanetHologramInspectorDialog on default tap when no callback is provided', (tester) async {
      tester.view.physicalSize = const Size(800, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: CyberCircuitBackground(
              isEn: false,
              child: SizedBox.expand(),
            ),
          ),
        ),
      );

      await tester.pump(const Duration(milliseconds: 100));

      const center = Offset(400, 400);
      const drumRadius = 190.0;

      // Pick Jupiter: orbitRatio = 0.76
      final jupiter = PlanetHologramData.findById('jupiter')!;
      final jupiterOrbit = drumRadius * jupiter.orbitRatio;
      final jupiterX = center.dx + math.cos(jupiter.startAngle) * jupiterOrbit;
      final jupiterY = center.dy + math.sin(jupiter.startAngle) * jupiterOrbit;
      final jupiterPos = Offset(jupiterX, jupiterY);

      // Tap Jupiter within hitbox
      final gesture = await tester.startGesture(jupiterPos);
      await tester.pump(const Duration(milliseconds: 50));
      await gesture.up();
      await tester.pump(const Duration(milliseconds: 350));

      // Verify that PlanetHologramInspectorDialog was opened in Vietnamese
      expect(find.byType(PlanetHologramInspectorDialog), findsOneWidget);
      expect(find.textContaining('MỘC TINH'), findsWidgets);
      expect(find.text('TĂNG TRƯỞNG & VỐN'), findsOneWidget);
    });
  });
}

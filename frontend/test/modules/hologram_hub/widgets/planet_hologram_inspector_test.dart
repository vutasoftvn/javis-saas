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
      expect(saturn.cosaBadge, equals('QUẢN TRỊ & PHÁP TRỊ'));

      final earth = PlanetHologramData.findById('earth')!;
      expect(earth.hasMoon, isTrue);
      expect(earth.nameVi, equals('Trái Đất'));
      expect(earth.cosaBadge, equals('THỊ TRƯỜNG & PMF'));

      final jupiter = PlanetHologramData.findById('jupiter')!;
      expect(jupiter.hasStripes, isTrue);
      expect(jupiter.nameVi, equals('Mộc Tinh'));
      expect(jupiter.cosaBadge, equals('TĂNG TRƯỞNG & VỐN'));

      final mars = PlanetHologramData.findById('mars')!;
      expect(mars.hasPolarCap, isTrue);
      expect(mars.nameVi, equals('Hỏa Tinh'));
      expect(mars.cosaBadge, equals('TIÊN PHONG ĐỘT PHÁ'));

      final mercury = PlanetHologramData.findById('mercury')!;
      expect(mercury.nameVi, equals('Thủy Tinh'));
      expect(mercury.cosaBadge, equals('TỐC ĐỘ PHẢN HỒI'));

      final uranus = PlanetHologramData.findById('uranus')!;
      expect(uranus.hasVerticalRing, isTrue);
      expect(uranus.cosaBadge, equals('DEEP-TECH MOAT'));
    });
  });

  group('PlanetHologramInspectorDialog Widget Tests', () {
    testWidgets('renders dialog for Saturn with Cassini rings and COSA OS specs', (tester) async {
      final saturn = PlanetHologramData.findById('saturn')!;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: PlanetHologramInspectorDialog(planet: saturn),
          ),
        ),
      );

      // Verify Top Bar
      expect(find.text('THỔ TINH'), findsOneWidget);
      expect(find.textContaining('SATURN'), findsOneWidget);
      expect(find.text('♄'), findsOneWidget);

      // Verify COSA OS Section
      expect(find.text('BIỂU TƯỢNG COSA OS'), findsOneWidget);
      expect(find.text('QUẢN TRỊ & PHÁP TRỊ'), findsOneWidget);
      expect(find.textContaining('Tuân thủ SLA'), findsOneWidget);

      // Verify Astronomical Specs
      expect(find.text('THÔNG SỐ THIÊN VĂN'), findsOneWidget);
      expect(find.text('Trấn Tinh (Thổ Đức)'), findsOneWidget);
      expect(find.text('1.43 tỷ km (9.58 AU)'), findsOneWidget);

      // Advance frames for rotating 3D preview
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
                  onPressed: () => PlanetHologramInspectorDialog.show(context, earth),
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

      expect(find.text('TRÁI ĐẤT'), findsOneWidget);
      expect(find.text('THỊ TRƯỜNG & PMF'), findsOneWidget);

      // Tap close button ✕
      final closeBtn = find.byIcon(Icons.close_rounded);
      expect(closeBtn, findsOneWidget);
      await tester.tap(closeBtn);
      await tester.pump(const Duration(milliseconds: 350));

      // Dialog is dismissed
      expect(find.text('TRÁI ĐẤT'), findsNothing);
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
              onPlanetTap: (planet) {
                tappedPlanet = planet;
              },
              child: const SizedBox.expand(),
            ),
          ),
        ),
      );

      await tester.pump(const Duration(milliseconds: 100));

      // Calculate position of a planet at initial frame (t=0)
      // Screen size = 800x800, center = (400, 400)
      // Drum size = clamp(800 * 0.46 = 368, 380, 780) = 380.0
      // drumRadius = 190.0
      const center = Offset(400, 400);
      const drumRadius = 190.0;

      // Pick Saturn: orbitRatio = 0.89, startAngle = alignmentAxis (-pi / 3.8)
      final saturn = PlanetHologramData.findById('saturn')!;
      final saturnOrbit = drumRadius * saturn.orbitRatio;
      final saturnX = center.dx + math.cos(saturn.startAngle) * saturnOrbit;
      final saturnY = center.dy + math.sin(saturn.startAngle) * saturnOrbit;
      final saturnPos = Offset(saturnX, saturnY);

      // Tap within the generous hitbox (~36px) of Saturn
      final gesture = await tester.startGesture(saturnPos + const Offset(5, 5));
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

      // Verify that PlanetHologramInspectorDialog was opened
      expect(find.byType(PlanetHologramInspectorDialog), findsOneWidget);
      expect(find.text('MỘC TINH'), findsOneWidget);
      expect(find.text('TĂNG TRƯỞNG & VỐN'), findsOneWidget);
    });
  });
}

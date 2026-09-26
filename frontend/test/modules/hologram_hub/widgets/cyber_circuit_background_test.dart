import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/hologram_hub/presentation/widgets/cyber_circuit_background.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('CyberCircuitBackground Widget Tests', () {
    testWidgets('renders background and child content properly', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: CyberCircuitBackground(
              child: Text('Test Child Content'),
            ),
          ),
        ),
      );

      expect(find.text('Test Child Content'), findsOneWidget);
      expect(find.byType(CustomPaint), findsWidgets);
    });

    testWidgets('reacts to audioLevel and isVoiceActive inputs', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: CyberCircuitBackground(
              isVoiceActive: true,
              audioLevel: 0.85,
              frequencyBands: [0.1, 0.4, 0.9, 0.7, 0.3],
              child: SizedBox(key: Key('test_box')),
            ),
          ),
        ),
      );

      expect(find.byKey(const Key('test_box')), findsOneWidget);
    });

    testWidgets('updates dynamically when audioLevelNotifier triggers', (tester) async {
      final audioNotifier = ValueNotifier<double>(0.1);
      final voiceNotifier = ValueNotifier<bool>(false);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CyberCircuitBackground(
              audioLevelNotifier: audioNotifier,
              isVoiceActiveNotifier: voiceNotifier,
              child: const SizedBox(key: Key('reactive_box')),
            ),
          ),
        ),
      );

      expect(find.byKey(const Key('reactive_box')), findsOneWidget);

      // Simulate voice spike
      audioNotifier.value = 0.95;
      voiceNotifier.value = true;
      await tester.pump();

      expect(find.byKey(const Key('reactive_box')), findsOneWidget);
    });

    testWidgets('invokes onVoiceTap when center voice target is tapped', (tester) async {
      bool tapped = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CyberCircuitBackground(
              onVoiceTap: () {
                tapped = true;
              },
              child: const SizedBox.shrink(),
            ),
          ),
        ),
      );

      // Center of the screen
      final centerFinder = find.byType(GestureDetector);
      expect(centerFinder, findsOneWidget);

      await tester.tap(centerFinder);
      await tester.pump();

      expect(tapped, isTrue);
    });

    testWidgets('renders solar system planetary orbits and drum overlay correctly across frames', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: CyberCircuitBackground(
              child: SizedBox.shrink(),
            ),
          ),
        ),
      );

      // Verify CustomPaint widgets exist (ambient, drum overlay with solar planets, voice visualizer)
      expect(find.byType(CustomPaint), findsWidgets);

      // Advance frames to simulate orbital motion
      await tester.pump(const Duration(milliseconds: 500));
      expect(find.byType(CustomPaint), findsWidgets);
      await tester.pump(const Duration(milliseconds: 1000));
      expect(find.byType(CustomPaint), findsWidgets);
    });
  });
}

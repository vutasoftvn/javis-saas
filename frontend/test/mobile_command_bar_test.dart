import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/hologram_hub/presentation/widgets/miva_hologram_core.dart';
import 'package:frontend/modules/hologram_hub/presentation/widgets/mobile_command_bar.dart';

void main() {
  testWidgets('MobileCommandBar displays mic icon when idle and collapses waveform', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: MobileCommandBar(
            runtimeState: HologramRuntimeState.idle,
            isChatInputActive: false,
            isVoiceListening: false,
            isConversationModeActive: false,
            onOpenChat: () {},
            onCloseChat: () {},
            onVoiceTap: () {},
            onSubmit: (_) {},
          ),
        ),
      ),
    );

    // Should show keyboard and mic icons
    expect(find.byIcon(Icons.keyboard_alt_outlined), findsOneWidget);
    expect(find.byIcon(Icons.mic_rounded), findsOneWidget);
    expect(find.byIcon(Icons.stop_rounded), findsNothing);
    expect(find.byKey(const ValueKey('audio_waveform_banner')), findsNothing);
  });

  testWidgets('MobileCommandBar displays stop icon and audio waveform banner when realtime voice is active', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: MobileCommandBar(
            runtimeState: HologramRuntimeState.listening,
            isChatInputActive: false,
            isVoiceListening: true,
            isConversationModeActive: true,
            onOpenChat: () {},
            onCloseChat: () {},
            onVoiceTap: () {},
            onSubmit: (_) {},
          ),
        ),
      ),
    );

    await tester.pump(const Duration(milliseconds: 350));

    // Should show stop icon and audio waveform banner
    expect(find.byIcon(Icons.stop_rounded), findsOneWidget);
    expect(find.byKey(const ValueKey('audio_waveform_banner')), findsOneWidget);
    expect(find.text('Đang lắng nghe...'), findsOneWidget);
  });

  testWidgets('MobileCommandBar displays COSA speaking status in waveform banner', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: MobileCommandBar(
            runtimeState: HologramRuntimeState.speaking,
            isChatInputActive: false,
            isVoiceListening: false,
            isConversationModeActive: true,
            onOpenChat: () {},
            onCloseChat: () {},
            onVoiceTap: () {},
            onSubmit: (_) {},
          ),
        ),
      ),
    );

    await tester.pump(const Duration(milliseconds: 350));

    expect(find.byIcon(Icons.stop_rounded), findsOneWidget);
    expect(find.byKey(const ValueKey('audio_waveform_banner')), findsOneWidget);
    expect(find.text('COSA đang nói...'), findsOneWidget);
  });

  testWidgets('MobileCommandBar displays thinking status in waveform banner', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: MobileCommandBar(
            runtimeState: HologramRuntimeState.thinking,
            isChatInputActive: false,
            isVoiceListening: false,
            isConversationModeActive: true,
            onOpenChat: () {},
            onCloseChat: () {},
            onVoiceTap: () {},
            onSubmit: (_) {},
          ),
        ),
      ),
    );

    await tester.pump(const Duration(milliseconds: 350));

    expect(find.byIcon(Icons.stop_rounded), findsOneWidget);
    expect(find.byKey(const ValueKey('audio_waveform_banner')), findsOneWidget);
    expect(find.text('Đang suy nghĩ...'), findsOneWidget);
  });
}

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';

import 'package:frontend/modules/hologram_hub/controllers/hologram_hub_controller.dart';
import 'package:frontend/modules/hologram_hub/presentation/widgets/chat/hub_chat_message_bubble.dart';

/// Regression coverage cho HTTPS-only link guard trong
/// `HubChatMessageBubble.onTapLink` (Task 7, review round 1). Test này KHÔNG
/// mock platform channel của `url_launcher` — thay vào đó widget nhận một
/// `launchUrlOverride` injectable (fake launcher) để capture URI thực sự
/// "mở" mà không đụng tới plugin thật. Nếu ai đó đổi `&&` thành `||` trong
/// `isExternalLinkSchemeAllowed`, hoặc bỏ guard khỏi `onTapLink`, các test
/// dưới đây phải FAIL.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({
      'auth_token': 'test_token',
      'workspace_id': 'ws_123',
    });
    Get.testMode = true;
  });

  tearDown(() {
    Get.reset();
  });

  group('isExternalLinkSchemeAllowed (pure guard logic)', () {
    test('https is always allowed', () {
      expect(isExternalLinkSchemeAllowed('https', debugMode: true), isTrue);
      expect(isExternalLinkSchemeAllowed('https', debugMode: false), isTrue);
      expect(isExternalLinkSchemeAllowed('HTTPS', debugMode: false), isTrue);
    });

    test('http is allowed only in debug mode', () {
      expect(isExternalLinkSchemeAllowed('http', debugMode: true), isTrue);
      expect(isExternalLinkSchemeAllowed('http', debugMode: false), isFalse);
    });

    test('any other scheme is never allowed, debug or not', () {
      expect(isExternalLinkSchemeAllowed('ftp', debugMode: true), isFalse);
      expect(isExternalLinkSchemeAllowed('javascript', debugMode: false), isFalse);
      expect(isExternalLinkSchemeAllowed('file', debugMode: true), isFalse);
    });
  });

  group('HubChatMessageBubble.onTapLink end-to-end', () {
    Future<MarkdownTapLinkCallback> pumpAndGetOnTapLink(
      WidgetTester tester, {
      required LaunchUrlFn launchUrlOverride,
    }) async {
      final controller = HologramHubController();
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: HubChatMessageBubble(
              message: const {
                'role': 'assistant',
                'text': 'Xem thêm tại [tài liệu](https://docs.cosa.vn/help)',
              },
              controller: controller,
              launchUrlOverride: launchUrlOverride,
            ),
          ),
        ),
      );
      final markdown = tester.widget<MarkdownBody>(find.byType(MarkdownBody));
      expect(markdown.onTapLink, isNotNull);
      return markdown.onTapLink!;
    }

    testWidgets('opens an https link', (tester) async {
      final opened = <Uri>[];
      final onTapLink = await pumpAndGetOnTapLink(
        tester,
        launchUrlOverride: (uri, {mode = LaunchMode.platformDefault}) async {
          opened.add(uri);
          return true;
        },
      );

      onTapLink('tài liệu', 'https://docs.cosa.vn/help', '');

      expect(opened, equals(<Uri>[Uri.parse('https://docs.cosa.vn/help')]));
    });

    testWidgets('does not open a non-http(s) scheme (e.g. javascript:)', (tester) async {
      final opened = <Uri>[];
      final onTapLink = await pumpAndGetOnTapLink(
        tester,
        launchUrlOverride: (uri, {mode = LaunchMode.platformDefault}) async {
          opened.add(uri);
          return true;
        },
      );

      onTapLink('click me', 'javascript:alert(1)', '');

      expect(opened, isEmpty);
    });

    testWidgets('flutter test runs as a debug build, so http is allowed here — '
        'production-mode rejection of http is covered by the pure '
        'isExternalLinkSchemeAllowed(debugMode: false) tests above', (tester) async {
      final opened = <Uri>[];
      final onTapLink = await pumpAndGetOnTapLink(
        tester,
        launchUrlOverride: (uri, {mode = LaunchMode.platformDefault}) async {
          opened.add(uri);
          return true;
        },
      );

      onTapLink('legacy link', 'http://intranet.local/doc', '');

      expect(opened, equals(<Uri>[Uri.parse('http://intranet.local/doc')]));
    });
  });
}

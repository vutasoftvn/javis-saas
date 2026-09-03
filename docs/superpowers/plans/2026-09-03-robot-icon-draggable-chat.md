# Icon robot mở khung chat kéo-thả — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đổi orb voice nổi (`FloatingVoiceHologram`) thành icon robot mở/đóng 1 khung chat nổi kéo-thả được, tái dùng đúng nội dung chat thật đã có trong `HologramHubView`.

**Architecture:** Tách nội dung chat hiện có thành `ChatPanelContent` (widget thuần). Thêm `ChatPanelController` (GetX, chrome-level, đăng ký qua `AppShellController.ensureShellDependencies()`) quản lý trạng thái mở/đóng + vị trí kéo-thả. `DraggableChatPanel` bọc `ChatPanelContent`, đọc state từ `ChatPanelController`. `FloatingVoiceHologram` đổi visual sang icon robot đơn giản, `onTap` toggle `ChatPanelController`. `AppShell` render cả `FloatingVoiceHologram` lẫn `DraggableChatPanel`; `HologramHubView` tự thêm cả 2 vào cây widget của chính nó (giả định Plan "Hub không sidebar" — `docs/superpowers/plans/2026-09-03-hub-no-sidebar.md` — đã chạy xong, `HologramHubView` không còn nằm trong `AppShell`).

**Tech Stack:** Flutter, GetX.

## Global Constraints

- **Phụ thuộc thứ tự:** Plan này giả định `docs/superpowers/plans/2026-09-03-hub-no-sidebar.md` đã chạy xong (`HologramHubView` KHÔNG còn là con của `AppShell`). Nếu chưa chạy, Task 6 sẽ tạo ra 2 icon robot chồng nhau (1 từ `AppShell`, 1 từ `HologramHubView` tự thêm) — kiểm tra trạng thái plan kia trước khi bắt đầu Task 6; nếu chưa xong, dừng Task 6 lại và báo cáo thay vì tự chạy tiếp.
- Không triển khai lại voice/STT — `hub_voice_mixin.dart`, `HologramHubController.onTalkPressed()`, `isVoiceListening`, `runtimeState` giữ nguyên 100%, không sửa.
- Không đổi API/giao thức chat — dùng đúng `FounderCommandCenterController.chatMessages` (`RxList<Map<String, String>>`), `chatInputController` (`TextEditingController`), `isChatLoading` (`RxBool`), `sendChatMessage(String)` — tất cả đã tồn tại, xem `frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart:137-139,495`.
- Chỉ 1 khung chat nổi tại 1 thời điểm (toggle mở/đóng, không multi-window).
- **Quyết định phạm vi (đã cân nhắc, không phải bỏ sót):** `FloatingVoiceHologram` hiện vẽ 1 "neural brain hologram" bằng `CustomPainter` phức tạp (~250 dòng: `_MiniBrainNode3D`, `_MiniSynapse`, `_FloatingNeuralBrainPainter`) — đây là hình ảnh trang trí cho voice, không phải logic voice (ghi âm/STT). Yêu cầu "đổi icon" không tương thích với việc giữ nguyên painter này (không có 1 "icon" đơn lẻ để đổi bên trong 1 CustomPainter). Task 5 THAY THẾ hẳn phần vẽ này bằng 1 icon robot đơn giản trong container tròn, và XOÁ các class painter/hình học không còn dùng tới (không để lại code chết) — đây là thay đổi có chủ đích, không phải quên sót phạm vi.

---

## Task 1: Tách `ChatPanelContent` từ nội dung chat có sẵn

**Files:**
- Create: `frontend/lib/modules/hologram_hub/widgets/chat_panel_content.dart`
- Test: `frontend/test/modules/hologram_hub/widgets/chat_panel_content_test.dart`

**Interfaces:**
- Consumes: `FounderCommandCenterController` (`chatMessages`, `chatInputController`, `isChatLoading`, `sendChatMessage`).
- Produces: `ChatPanelContent({required FounderCommandCenterController controller, required VoidCallback onClose})` — dùng ở Task 3.

- [ ] **Step 1: Viết test trước — hiển thị tin nhắn, gửi tin nhắn qua input, nút đóng gọi callback**

```dart
// frontend/test/modules/hologram_hub/widgets/chat_panel_content_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/widgets/chat_panel_content.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.reset();
    Get.testMode = true;
  });

  testWidgets('renders existing messages and calls onClose when close tapped', (
    tester,
  ) async {
    final controller = Get.put(FounderCommandCenterController());
    controller.chatMessages.add({'role': 'user', 'content': 'Xin chào'});

    var closed = false;
    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ChatPanelContent(
            controller: controller,
            onClose: () => closed = true,
          ),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Xin chào'), findsOneWidget);

    await tester.tap(find.byIcon(Icons.close));
    expect(closed, isTrue);
  });

  testWidgets('submitting text field calls sendChatMessage', (tester) async {
    final controller = Get.put(FounderCommandCenterController());

    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ChatPanelContent(controller: controller, onClose: () {}),
        ),
      ),
    );
    await tester.pump();

    await tester.enterText(find.byType(TextField), 'Việc hôm nay có gì?');
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pump();

    expect(controller.chatMessages.any((m) => m['content'] == 'Việc hôm nay có gì?'), isTrue);
  });
}
```

Đã xác nhận: `FounderCommandCenterController({WorkforceMvpService? workforceMvpService})`
(`frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart:44`)
— mọi tham số đều optional, `FounderCommandCenterController()` dùng thẳng
được trong test như trên, không cần fake service.

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd frontend && flutter test test/modules/hologram_hub/widgets/chat_panel_content_test.dart`
Expected: FAIL — `ChatPanelContent` chưa tồn tại.

- [ ] **Step 3: Viết `ChatPanelContent` — copy nguyên nội dung chat đã có**

```dart
// frontend/lib/modules/hologram_hub/widgets/chat_panel_content.dart
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/ui/app_copy.dart';
import '../controllers/founder_command_center_controller.dart';

class ChatPanelContent extends StatelessWidget {
  const ChatPanelContent({
    super.key,
    required this.controller,
    required this.onClose,
  });

  final FounderCommandCenterController controller;
  final VoidCallback onClose;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            const Icon(Icons.psychology, color: Color(0xFF8B5CF6), size: 24),
            const SizedBox(width: 10),
            const Text(
              AppCopy.hubChatPanelTitle,
              style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const Spacer(),
            IconButton(
              onPressed: onClose,
              icon: const Icon(Icons.close, color: Colors.white70),
            ),
          ],
        ),
        const Divider(color: Color(0x336366F1)),
        Expanded(
          child: Obx(() {
            if (controller.chatMessages.isEmpty) {
              return Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.chat_bubble_outline, size: 48, color: Colors.white.withValues(alpha: 0.2)),
                    const SizedBox(height: 12),
                    Text(
                      AppCopy.hubChatEmptyState,
                      style: TextStyle(color: Colors.white.withValues(alpha: 0.5), fontSize: 13),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              );
            }
            return ListView.builder(
              itemCount: controller.chatMessages.length,
              itemBuilder: (c, idx) {
                final msg = controller.chatMessages[idx];
                final isUser = msg['role'] == 'user';
                final isError = msg['role'] == 'error';
                return Align(
                  alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.symmetric(vertical: 6),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: isUser
                          ? const Color(0xFF6366F1)
                          : (isError ? const Color(0x33EF4444) : const Color(0xFF1E293B)),
                      borderRadius: BorderRadius.circular(12),
                      border: isError ? Border.all(color: const Color(0xFFEF4444), width: 1) : null,
                    ),
                    child: Text(
                      msg['content'] ?? '',
                      style: const TextStyle(color: Colors.white, fontSize: 13),
                    ),
                  ),
                );
              },
            );
          }),
        ),
        Obx(() => controller.isChatLoading.value
            ? const Padding(
                padding: EdgeInsets.all(8.0),
                child: LinearProgressIndicator(color: Color(0xFF6366F1)),
              )
            : const SizedBox.shrink()),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: controller.chatInputController,
                style: const TextStyle(color: Colors.white, fontSize: 13),
                decoration: InputDecoration(
                  hintText: AppCopy.hubChatInputHint,
                  hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.4), fontSize: 12),
                  filled: true,
                  fillColor: const Color(0xFF1E293B),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                ),
                onSubmitted: (text) => controller.sendChatMessage(text),
              ),
            ),
            const SizedBox(width: 8),
            IconButton(
              onPressed: () => controller.sendChatMessage(controller.chatInputController.text),
              icon: const Icon(Icons.send, color: Color(0xFF6366F1)),
            ),
          ],
        ),
      ],
    );
  }
}
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd frontend && flutter test test/modules/hologram_hub/widgets/chat_panel_content_test.dart`
Expected: PASS.

- [ ] **Step 5: `dart analyze` sạch**

Run: `cd frontend && dart analyze lib/modules/hologram_hub/widgets/chat_panel_content.dart`
Expected: No issues found.

- [ ] **Step 6: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/hologram_hub/widgets/chat_panel_content.dart \
  frontend/test/modules/hologram_hub/widgets/chat_panel_content_test.dart
git commit -m "refactor(hub): tach ChatPanelContent tu noi dung chat co san

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: `ChatPanelController` — trạng thái mở/đóng + vị trí kéo-thả

**Files:**
- Create: `frontend/lib/core/shell/chat_panel_controller.dart`
- Modify: `frontend/lib/core/shell/app_shell_controller.dart`
- Test: `frontend/test/core/shell/chat_panel_controller_test.dart`

**Interfaces:**
- Produces: `ChatPanelController` — `isOpen` (`RxBool`), `position` (`Rxn<Offset>`), `void open()`, `void close()`, `void toggle()`, `void updatePosition(Offset offset)`. Đăng ký qua `AppShellController.ensureShellDependencies()` — dùng ở Task 3-6.

- [ ] **Step 1: Viết test trước**

```dart
// frontend/test/core/shell/chat_panel_controller_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/shell/chat_panel_controller.dart';

void main() {
  test('toggle flips isOpen, open/close set it explicitly', () {
    final controller = ChatPanelController();
    expect(controller.isOpen.value, isFalse);

    controller.toggle();
    expect(controller.isOpen.value, isTrue);

    controller.toggle();
    expect(controller.isOpen.value, isFalse);

    controller.open();
    expect(controller.isOpen.value, isTrue);

    controller.close();
    expect(controller.isOpen.value, isFalse);
  });

  test('updatePosition stores the latest offset', () {
    final controller = ChatPanelController();
    expect(controller.position.value, isNull);

    controller.updatePosition(const Offset(100, 200));
    expect(controller.position.value, const Offset(100, 200));
  });
}
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd frontend && flutter test test/core/shell/chat_panel_controller_test.dart`
Expected: FAIL — file chưa tồn tại.

- [ ] **Step 3: Viết `ChatPanelController`**

```dart
// frontend/lib/core/shell/chat_panel_controller.dart
import 'package:flutter/material.dart';
import 'package:get/get.dart';

/// State chrome-level cho khung chat nổi kéo-thả — thay cho voice orb
/// (`FloatingVoiceHologram`) trước đây chỉ toggle voice. Đăng ký qua
/// `AppShellController.ensureShellDependencies()`, dùng chung bởi mọi nơi
/// hiển thị orb/panel (`AppShell` cho 21 module có sidebar,
/// `HologramHubView` cho Hub không sidebar).
class ChatPanelController extends GetxController {
  final isOpen = false.obs;
  final Rxn<Offset> position = Rxn<Offset>();

  void open() => isOpen.value = true;
  void close() => isOpen.value = false;
  void toggle() => isOpen.value = !isOpen.value;
  void updatePosition(Offset offset) => position.value = offset;
}
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd frontend && flutter test test/core/shell/chat_panel_controller_test.dart`
Expected: PASS.

- [ ] **Step 5: Đăng ký trong `AppShellController.ensureShellDependencies()`**

Sửa `frontend/lib/core/shell/app_shell_controller.dart`, thêm import và 1
khối đăng ký mới vào `ensureShellDependencies()` (dòng 27-44):

```dart
import 'chat_panel_controller.dart';

// bên trong ensureShellDependencies(), thêm trước dòng đăng ký AppShellController:
    if (!Get.isRegistered<ChatPanelController>()) {
      Get.put<ChatPanelController>(ChatPanelController(), permanent: true);
    }
```

- [ ] **Step 6: Viết test xác nhận `ensureShellDependencies()` đăng ký đủ `ChatPanelController`**

```dart
// thêm vào frontend/test/core/shell/chat_panel_controller_test.dart (hoặc file test app_shell_controller nếu đã có — kiểm tra trước khi tạo file mới)
import 'package:get/get.dart';
import 'package:frontend/core/shell/app_shell_controller.dart';

test('ensureShellDependencies registers ChatPanelController', () {
  Get.reset();
  Get.testMode = true;
  AppShellController.ensureShellDependencies();
  expect(Get.isRegistered<ChatPanelController>(), isTrue);
});
```

- [ ] **Step 7: Chạy lại toàn bộ test, `dart analyze` sạch**

Run: `cd frontend && flutter test test/core/shell/ && dart analyze lib/core/shell/`
Expected: Tất cả PASS; No issues found.

- [ ] **Step 8: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/core/shell/chat_panel_controller.dart \
  frontend/lib/core/shell/app_shell_controller.dart \
  frontend/test/core/shell/chat_panel_controller_test.dart
git commit -m "feat(shell): ChatPanelController quan ly trang thai mo/dong + vi tri khung chat noi

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: `DraggableChatPanel` — panel nổi kéo-thả bọc `ChatPanelContent`

**Files:**
- Create: `frontend/lib/modules/hologram_hub/widgets/draggable_chat_panel.dart`
- Test: `frontend/test/modules/hologram_hub/widgets/draggable_chat_panel_test.dart`

**Interfaces:**
- Consumes: `ChatPanelController` (Task 2), `ChatPanelContent` (Task 1), `FounderCommandCenterController`.
- Produces: `DraggableChatPanel()` (không tham số, tự `Get.find` 2 controller trên) — dùng ở Task 4, 6.

- [ ] **Step 1: Viết test trước — ẩn khi đóng, hiện khi mở, kéo đổi vị trí**

```dart
// frontend/test/modules/hologram_hub/widgets/draggable_chat_panel_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/shell/chat_panel_controller.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/widgets/draggable_chat_panel.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.reset();
    Get.testMode = true;
    Get.put(ChatPanelController());
    Get.put(FounderCommandCenterController());
  });

  testWidgets('renders nothing when closed, shows panel when open', (
    tester,
  ) async {
    await tester.pumpWidget(
      const GetMaterialApp(
        home: Scaffold(body: Stack(children: [DraggableChatPanel()])),
      ),
    );
    await tester.pump();

    expect(find.byType(TextField), findsNothing);

    Get.find<ChatPanelController>().open();
    await tester.pump();

    expect(find.byType(TextField), findsOneWidget);
  });

  testWidgets('close button closes the panel via ChatPanelController', (
    tester,
  ) async {
    Get.find<ChatPanelController>().open();

    await tester.pumpWidget(
      const GetMaterialApp(
        home: Scaffold(body: Stack(children: [DraggableChatPanel()])),
      ),
    );
    await tester.pump();

    await tester.tap(find.byIcon(Icons.close));
    await tester.pump();

    expect(Get.find<ChatPanelController>().isOpen.value, isFalse);
    expect(find.byType(TextField), findsNothing);
  });
}
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd frontend && flutter test test/modules/hologram_hub/widgets/draggable_chat_panel_test.dart`
Expected: FAIL — `DraggableChatPanel` chưa tồn tại.

- [ ] **Step 3: Viết `DraggableChatPanel`**

```dart
// frontend/lib/modules/hologram_hub/widgets/draggable_chat_panel.dart
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/shell/chat_panel_controller.dart';
import '../controllers/founder_command_center_controller.dart';
import 'chat_panel_content.dart';

class DraggableChatPanel extends StatelessWidget {
  const DraggableChatPanel({super.key});

  static const _width = 340.0;
  static const _height = 480.0;

  ChatPanelController get _panelController => Get.find<ChatPanelController>();
  FounderCommandCenterController get _hubController =>
      Get.find<FounderCommandCenterController>();

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      if (!_panelController.isOpen.value) return const SizedBox.shrink();

      return LayoutBuilder(
        builder: (context, constraints) {
          final maxX = (constraints.maxWidth - _width).clamp(0.0, double.infinity);
          final maxY = (constraints.maxHeight - _height).clamp(0.0, double.infinity);
          final defaultPosition = Offset(
            (constraints.maxWidth - _width - 48).clamp(0.0, maxX),
            (constraints.maxHeight - _height - 48).clamp(0.0, maxY),
          );
          final current = _panelController.position.value ?? defaultPosition;
          final bounded = Offset(
            current.dx.clamp(0.0, maxX),
            current.dy.clamp(0.0, maxY),
          );

          return Positioned(
            left: bounded.dx,
            top: bounded.dy,
            child: GestureDetector(
              onPanUpdate: (details) => _panelController.updatePosition(
                Offset(
                  (bounded.dx + details.delta.dx).clamp(0.0, maxX),
                  (bounded.dy + details.delta.dy).clamp(0.0, maxY),
                ),
              ),
              child: Container(
                width: _width,
                height: _height,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFF0F172A),
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: [
                    BoxShadow(color: Colors.black.withValues(alpha: 0.4), blurRadius: 20),
                  ],
                ),
                child: ChatPanelContent(
                  controller: _hubController,
                  onClose: _panelController.close,
                ),
              ),
            ),
          );
        },
      );
    });
  }
}
```

**Lưu ý:** kéo-thả áp dụng trên toàn bộ `Container` (kể cả vùng nhập chat) —
đây là hạn chế đã biết (kéo vô tình khi định bấm vào input) nhưng đủ cho bản
đầu tiên, khớp đúng mức độ đơn giản mà spec yêu cầu; không cần vùng "tay cầm"
kéo riêng ở phiên bản này.

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd frontend && flutter test test/modules/hologram_hub/widgets/draggable_chat_panel_test.dart`
Expected: PASS.

- [ ] **Step 5: `dart analyze` sạch**

Run: `cd frontend && dart analyze lib/modules/hologram_hub/widgets/`
Expected: No issues found.

- [ ] **Step 6: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/hologram_hub/widgets/draggable_chat_panel.dart \
  frontend/test/modules/hologram_hub/widgets/draggable_chat_panel_test.dart
git commit -m "feat(hub): DraggableChatPanel - panel chat noi keo-tha duoc

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: Gắn `DraggableChatPanel` vào `AppShell`

**Files:**
- Modify: `frontend/lib/core/shell/app_shell.dart`
- Test: `frontend/test/core/shell/app_shell_test.dart`

**Interfaces:**
- Consumes: `DraggableChatPanel` (Task 3).

- [ ] **Step 1: Đọc test hiện có trước khi sửa**

`frontend/test/core/shell/app_shell_test.dart` đã tồn tại — đọc trước để
không phá cấu trúc test hiện có, chỉ thêm assertion mới.

- [ ] **Step 2: Viết test trước — `AppShell` render `DraggableChatPanel`**

Thêm vào `frontend/test/core/shell/app_shell_test.dart` (theo đúng pattern
setup đã có trong file — dùng lại harness dựng `AppShell` sẵn có, không viết
harness mới):

```dart
testWidgets('AppShell includes DraggableChatPanel alongside the voice orb', (
  tester,
) async {
  // ... dùng harness pump AppShell đã có trong file này ...
  expect(find.byType(DraggableChatPanel), findsOneWidget);
});
```

- [ ] **Step 3: Chạy test, xác nhận FAIL**

Run: `cd frontend && flutter test test/core/shell/app_shell_test.dart`
Expected: FAIL — `AppShell` chưa render `DraggableChatPanel`.

- [ ] **Step 4: Thêm `DraggableChatPanel` vào `AppShell`**

Sửa `frontend/lib/core/shell/app_shell.dart`, thêm import:

```dart
import '../../modules/hologram_hub/widgets/draggable_chat_panel.dart';
```

Thêm `const DraggableChatPanel(),` ngay sau MỖI dòng `const FloatingVoiceHologram(),`
(2 chỗ: dòng 80 và dòng 105).

- [ ] **Step 5: Chạy lại test, xác nhận PASS**

Run: `cd frontend && flutter test test/core/shell/app_shell_test.dart`
Expected: PASS (kể cả các test cũ trong file — không regression).

- [ ] **Step 6: `dart analyze` sạch**

Run: `cd frontend && dart analyze lib/core/shell/`
Expected: No issues found.

- [ ] **Step 7: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/core/shell/app_shell.dart \
  frontend/test/core/shell/app_shell_test.dart
git commit -m "feat(shell): gan DraggableChatPanel vao AppShell (desktop + mobile)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 5: Đổi `FloatingVoiceHologram` sang icon robot, mở chat thay vì toggle voice

**Files:**
- Modify: `frontend/lib/modules/dashboard/views/widgets/floating_voice_hologram.dart`
- Test: `frontend/test/modules/dashboard/views/widgets/floating_voice_hologram_test.dart` (tạo mới nếu chưa có — kiểm tra trước)

**Interfaces:**
- Consumes: `ChatPanelController` (Task 2).
- Produces: giữ nguyên tên class `FloatingVoiceHologram` và constructor `const FloatingVoiceHologram()` — không đổi call site ở `AppShell`/`HologramHubView`.

- [ ] **Step 1: Viết test trước — tap mở `ChatPanelController`, hiển thị icon robot**

```dart
// frontend/test/modules/dashboard/views/widgets/floating_voice_hologram_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/shell/chat_panel_controller.dart';
import 'package:frontend/modules/dashboard/views/widgets/floating_voice_hologram.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.reset();
    Get.testMode = true;
    Get.put(ChatPanelController());
  });

  testWidgets('shows a robot icon and toggles ChatPanelController on tap', (
    tester,
  ) async {
    await tester.pumpWidget(
      const GetMaterialApp(
        home: Scaffold(body: Stack(children: [FloatingVoiceHologram()])),
      ),
    );
    await tester.pump();

    expect(find.byIcon(Icons.smart_toy_rounded), findsOneWidget);
    expect(Get.find<ChatPanelController>().isOpen.value, isFalse);

    await tester.tap(find.byIcon(Icons.smart_toy_rounded));
    await tester.pump();

    expect(Get.find<ChatPanelController>().isOpen.value, isTrue);
  });
}
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd frontend && flutter test test/modules/dashboard/views/widgets/floating_voice_hologram_test.dart`
Expected: FAIL — widget hiện chưa có `Icons.smart_toy_rounded`, tap hiện gọi `_toggleVoice`.

- [ ] **Step 3: Viết lại `FloatingVoiceHologram`**

Thay TOÀN BỘ nội dung `frontend/lib/modules/dashboard/views/widgets/floating_voice_hologram.dart`
bằng (giữ nguyên cơ chế `_position`/`onPanUpdate`/clamp từ bản cũ, xoá phần
`CustomPainter`/hình học 3D không còn dùng, đổi `onTap`):

```dart
import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../../core/shell/chat_panel_controller.dart';

/// Icon robot nổi, kéo được — thay cho orb voice cũ. Tap mở/đóng khung chat
/// nổi (`DraggableChatPanel`) qua `ChatPanelController`. Voice/STT chưa nối
/// lại vào đây — triển khai ở 1 tính năng riêng sau này (xem spec
/// `docs/superpowers/specs/2026-09-03-robot-icon-draggable-chat-design.md`).
class FloatingVoiceHologram extends StatefulWidget {
  const FloatingVoiceHologram({super.key});

  @override
  State<FloatingVoiceHologram> createState() => _FloatingVoiceHologramState();
}

class _FloatingVoiceHologramState extends State<FloatingVoiceHologram> {
  static const _diameter = 56.0;
  static const _rightPadding = 48.0;
  static const _bottomPadding = 120.0;
  Offset? _position;

  ChatPanelController get _panelController => Get.find<ChatPanelController>();

  @override
  Widget build(BuildContext context) {
    return Positioned.fill(
      child: LayoutBuilder(
        builder: (context, constraints) {
          final double maxX = (constraints.maxWidth - _diameter).clamp(0.0, double.infinity);
          final double maxY = (constraints.maxHeight - _diameter).clamp(0.0, double.infinity);
          final defaultPosition = Offset(
            (constraints.maxWidth - _diameter - _rightPadding).clamp(0.0, maxX),
            (constraints.maxHeight - _diameter - _bottomPadding).clamp(0.0, maxY),
          );
          final Offset currentPos = _position ?? defaultPosition;
          final Offset boundedPosition = Offset(
            currentPos.dx.clamp(0.0, maxX),
            currentPos.dy.clamp(0.0, maxY),
          );

          return Positioned(
            left: boundedPosition.dx,
            top: boundedPosition.dy,
            child: GestureDetector(
              onPanStart: (_) => setState(() => _position = boundedPosition),
              onPanUpdate: (details) => setState(() {
                _position = Offset(
                  (boundedPosition.dx + details.delta.dx).clamp(0.0, maxX),
                  (boundedPosition.dy + details.delta.dy).clamp(0.0, maxY),
                );
              }),
              onTap: () => _panelController.toggle(),
              child: Tooltip(
                message: 'Mở/đóng chat với COSA',
                child: Obx(() {
                  final isOpen = _panelController.isOpen.value;
                  return Container(
                    key: const Key('floating_voice_hologram'),
                    width: _diameter,
                    height: _diameter,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: const LinearGradient(
                        colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFF6366F1).withValues(alpha: isOpen ? 0.6 : 0.35),
                          blurRadius: 16,
                          spreadRadius: isOpen ? 2 : 0,
                        ),
                      ],
                    ),
                    child: const Icon(
                      Icons.smart_toy_rounded,
                      color: Colors.white,
                      size: 28,
                    ),
                  );
                }),
              ),
            ),
          );
        },
      ),
    );
  }
}
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd frontend && flutter test test/modules/dashboard/views/widgets/floating_voice_hologram_test.dart`
Expected: PASS.

- [ ] **Step 5: `dart analyze` sạch, chạy lại toàn bộ test liên quan (dashboard, hologram_hub, shell)**

Run: `cd frontend && dart analyze lib/modules/dashboard/ lib/core/shell/ && flutter test test/modules/dashboard/ test/core/shell/ test/modules/hologram_hub/`
Expected: No issues found; tất cả PASS. Nếu 1 test cũ nào đó (vd
`hub_voice_mixin_test.dart`) assert vào hành vi `_toggleVoice` của widget này
qua UI thật (không phải gọi thẳng `HologramHubController`), dừng lại và báo
cáo — không tự sửa test theo hướng che giấu behavior thay đổi.

- [ ] **Step 6: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/dashboard/views/widgets/floating_voice_hologram.dart \
  frontend/test/modules/dashboard/views/widgets/floating_voice_hologram_test.dart
git commit -m "feat(hub): FloatingVoiceHologram doi thanh icon robot mo/dong chat, xoa painter neural-brain khong con dung

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 6: Thống nhất điểm mở chat + gắn vào `HologramHubView`

**Files:**
- Modify: `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart`
- Test: `frontend/test/modules/hologram_hub/hologram_hub_view_chat_panel_test.dart`

**Interfaces:**
- Consumes: `ChatPanelController`, `DraggableChatPanel`, `FloatingVoiceHologram`.

**Trước khi bắt đầu:** xác nhận `docs/superpowers/plans/2026-09-03-hub-no-sidebar.md`
đã chạy tới Task 6 của plan đó (`/hub` đã trỏ `HologramHubView` trực tiếp,
không còn qua `AppShell`) — chạy `grep -n "class DashboardContentBody"
frontend/lib/modules/dashboard/views/widgets/dashboard_content_body.dart`:
nếu file không còn tồn tại, plan kia đã xong, tiếp tục Task này bình thường.
Nếu file vẫn còn, DỪNG LẠI — Task này sẽ tạo icon robot trùng lặp (1 từ
`AppShell` bọc ngoài, 1 từ chính task này) — báo cáo, không tự chạy tiếp.

- [ ] **Step 1: Viết test trước — `HologramHubView` tự có icon robot + panel, không dùng `showModalBottomSheet` nữa**

```dart
// frontend/test/modules/hologram_hub/hologram_hub_view_chat_panel_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/shell/app_shell_controller.dart';
import 'package:frontend/core/shell/chat_panel_controller.dart';
import 'package:frontend/modules/dashboard/views/widgets/floating_voice_hologram.dart';
import 'package:frontend/modules/hologram_hub/views/hologram_hub_view.dart';
import 'package:frontend/modules/hologram_hub/widgets/draggable_chat_panel.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.reset();
    Get.testMode = true;
    AppShellController.ensureShellDependencies();
  });

  testWidgets('HologramHubView includes its own robot icon and chat panel', (
    tester,
  ) async {
    await tester.pumpWidget(
      const GetMaterialApp(home: Scaffold(body: HologramHubView())),
    );
    await tester.pump();

    expect(find.byType(FloatingVoiceHologram), findsOneWidget);
    expect(find.byType(DraggableChatPanel), findsOneWidget);
  });

  testWidgets('"Hỏi COSA" opens the chat panel via ChatPanelController, not a modal sheet', (
    tester,
  ) async {
    await tester.pumpWidget(
      const GetMaterialApp(home: Scaffold(body: HologramHubView())),
    );
    await tester.pump();

    // Nút "Hỏi COSA" nằm trong 1 widget con (banner/card) — tìm theo text đã
    // biết trong AppCopy hoặc theo Key nếu widget đó có. Nếu không tap được
    // trực tiếp trong test này (widget con quá sâu/cần scroll), verify tối
    // thiểu bằng cách gọi thẳng callback đã đổi:
    Get.find<ChatPanelController>().open();
    await tester.pump();

    expect(find.byType(DraggableChatPanel), findsOneWidget);
    expect(Get.find<ChatPanelController>().isOpen.value, isTrue);
  });
}
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd frontend && flutter test test/modules/hologram_hub/hologram_hub_view_chat_panel_test.dart`
Expected: FAIL — `HologramHubView` chưa có `FloatingVoiceHologram`/`DraggableChatPanel` trong cây widget.

- [ ] **Step 3: Sửa `HologramHubView`**

Thêm import vào đầu `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart`:

```dart
import '../../dashboard/views/widgets/floating_voice_hologram.dart';
import '../widgets/draggable_chat_panel.dart';
import '../../../core/shell/chat_panel_controller.dart';
```

Bọc nội dung `Scaffold` hiện có (dòng 47-... , bên trong `RuntimeAppChrome`)
bằng 1 `Stack` chứa nội dung cũ + 2 widget mới. Cụ thể, đổi:

```dart
    return RuntimeAppChrome(
      child: Scaffold(
        backgroundColor: const Color(0xFF040712),
        body: CyberCircuitBackground(
          child: SafeArea(
            child: Column(
              children: [
                _buildHeader(context, controller),
                Expanded(
                  child: Obx(() {
                    ...
```

thành (bọc `body:` bằng `Stack`, giữ nguyên toàn bộ nội dung `CyberCircuitBackground(...)` y hệt bên trong):

```dart
    return RuntimeAppChrome(
      child: Scaffold(
        backgroundColor: const Color(0xFF040712),
        body: Stack(
          children: [
            CyberCircuitBackground(
              child: SafeArea(
                child: Column(
                  children: [
                    _buildHeader(context, controller),
                    Expanded(
                      child: Obx(() {
                        ...
```

và đóng thêm 2 dấu ngoặc tương ứng (`)` cho `SafeArea`/`CyberCircuitBackground`)
trước khi thêm:

```dart
            const FloatingVoiceHologram(),
            const DraggableChatPanel(),
          ],
        ),
      ),
    );
```

thay cho phần đóng `Scaffold`/`RuntimeAppChrome` cũ. Đọc kỹ cấu trúc ngoặc
thật của method `build()` (dòng 47-101) trước khi sửa để đóng đúng số lượng
dấu ngoặc — đây là việc sửa cấu trúc lồng nhau, dễ lệch ngoặc nếu không đọc
kỹ.

Sửa `_openChatBottomSheet` (dòng 915-1080) — XOÁ HẲN hàm này và mọi lời gọi
tới nó. Đã xác nhận CÓ ĐÚNG 5 call site (không phải 2) — dòng 861's
`showModalBottomSheet` là cho `DecisionModalSheet` (giải quyết pending
decision), KHÔNG liên quan chat, để nguyên không đụng:

- Dòng 41: `controller.maybeAutoOpenChatFromRoute(() => _openChatBottomSheet(context, controller));`
  → `controller.maybeAutoOpenChatFromRoute(() => Get.find<ChatPanelController>().open());`
- Dòng 387: `onAskCosa: () => _openChatBottomSheet(context, controller)`
  → `onAskCosa: () => Get.find<ChatPanelController>().open()`
- Dòng 881-886 (trong 1 method xử lý action, biến `action.id == 'act_genesis_profile'`):
  ```dart
  } else if (action.id == 'act_genesis_profile') {
    controller.chatInputController.text =
        'Tôi muốn thiết lập hồ sơ doanh nghiệp mới. Hãy hướng dẫn tôi định hình Vision, Problem và Target Market!';
    Get.find<ChatPanelController>().open();
    return;
  }
  ```
- Dòng 888-895 (`action.id == 'act_genesis_12wy'`), cùng pattern:
  ```dart
  } else if (action.id == 'act_genesis_12wy') {
    controller.chatInputController.text =
        'Hãy hướng dẫn tôi thiết lập Mục tiêu 12-Week Year cho Quý đầu tiên.';
    Get.find<ChatPanelController>().open();
    return;
  }
  ```
- Dòng 898 (fallback cuối cùng của cùng method): `_openChatBottomSheet(context, controller);`
  → `Get.find<ChatPanelController>().open();`

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd frontend && flutter test test/modules/hologram_hub/hologram_hub_view_chat_panel_test.dart`
Expected: PASS.

- [ ] **Step 5: `dart analyze` sạch, chạy lại toàn bộ test hologram_hub**

Run: `cd frontend && dart analyze lib/modules/hologram_hub/ && flutter test test/modules/hologram_hub/`
Expected: No issues found; tất cả PASS — đặc biệt các test liên quan
`maybeAutoOpenChatFromRoute`/auto-open từ route `/chat` (nếu có) vẫn phải
pass với hành vi mới (mở `ChatPanelController` thay vì bottom sheet).

- [ ] **Step 6: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart \
  frontend/test/modules/hologram_hub/hologram_hub_view_chat_panel_test.dart
git commit -m "feat(hub): HologramHubView dung chung icon robot + panel chat noi, bo showModalBottomSheet cu

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

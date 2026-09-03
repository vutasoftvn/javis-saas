# Icon robot mở khung chat kéo-thả (thay voice tạm thời)

**Ngày:** 2026-09-03
**Trạng thái:** Đã duyệt thiết kế, chờ viết plan
**Bối cảnh:** Sub-project 3/4 của đợt cải tiến UI lớn hơn (Work home — spec
`2026-09-03-work-overview-tab-design.md`, sidebar Hub — spec
`2026-09-03-hub-no-sidebar-design.md`, sub-project này, rà soát OKR/12WY/Task).

## 1. Vấn đề

Yêu cầu gốc "kéo-thả voice chuyển thành chat" đã được làm rõ qua trao đổi:
không phải kéo orb voice thả vào 1 vùng chat riêng, mà là **đổi hẳn vai trò**
của orb nổi hiện có — từ bật/tắt voice sang mở 1 khung chat nổi, kéo-thả đổi
vị trí được. Voice (ghi âm/STT thật) triển khai lại sau, không nằm trong
scope này.

### Hiện trạng đã xác nhận

- `FloatingVoiceHologram` (`frontend/lib/modules/dashboard/views/widgets/floating_voice_hologram.dart`)
  là orb nổi dùng chung trong `AppShell` (mọi module có sidebar), kéo được
  qua `GestureDetector.onPanUpdate` để đổi vị trí, `onTap` gọi `_toggleVoice`.
- Nội dung chat THẬT đã tồn tại: `HologramHubView._openChatBottomSheet`
  (dòng 915+) — mở `showModalBottomSheet` chứa transcript + input, nối vào
  `FounderCommandCenterController.chatInputController` thật, không mock. Gọi
  từ nút "Hỏi COSA" (`onAskCosa`) và tự mở khi vào route `/chat` (redirect cũ,
  qua `maybeAutoOpenChatFromRoute`).

## 2. Thiết kế

### 2.1 Tách nội dung chat thành widget dùng chung

Tách phần `Column` bên trong `_openChatBottomSheet`'s builder (dòng 929+:
header + transcript + input) thành 1 widget riêng `ChatPanelContent`
(thư mục `frontend/lib/modules/hologram_hub/widgets/`), nhận
`FounderCommandCenterController` qua constructor — logic/state bên trong
giữ nguyên 100%, chỉ đổi nơi chứa.

### 2.2 Panel chat nổi, kéo-thả được

Tạo 1 widget mới `DraggableChatPanel` — bọc `ChatPanelContent` trong 1
`Positioned` bên trong `Stack`, tự quản vị trí (`Offset`) qua
`GestureDetector.onPanUpdate` giống hệt cơ chế đang dùng ở
`FloatingVoiceHologram` (tái dùng logic tính toán vị trí/giới hạn màn hình,
không viết lại từ đầu). Có nút đóng (X) ở góc panel.

### 2.3 Đổi vai trò orb nổi

Trong `floating_voice_hologram.dart`:
- Đổi icon hiển thị của orb sang icon robot (`Icons.smart_toy` hoặc tương
  đương trong bộ icon đang dùng — xác nhận cụ thể khi viết plan).
- Đổi `onTap`: không còn gọi `_toggleVoice` — mở/đóng `DraggableChatPanel`
  (toggle hiện/ẩn).
- Giữ nguyên hoàn toàn cơ chế kéo-đổi-vị-trí của orb (`onPanUpdate`) — không
  đụng vào.
- Logic voice thật (ghi âm, STT, `hub_voice_mixin.dart`) **không xoá, không
  sửa** — chỉ tạm thời không còn được trigger từ icon này. Việc nối lại voice
  (vd nút mic bên trong `DraggableChatPanel`) là 1 spec/plan riêng sau này,
  không nằm trong scope hiện tại.

### 2.4 Thống nhất 1 điểm mở chat duy nhất

Mọi nơi hiện đang gọi `_openChatBottomSheet` (`onAskCosa`, auto-open từ route
`/chat` cũ) đổi sang mở `DraggableChatPanel` (qua cùng 1 hàm/controller dùng
chung) — không giữ song song 2 cách mở chat (bottom sheet cũ + panel nổi
mới) để tránh 2 trải nghiệm khác nhau cho cùng 1 tính năng.

### 2.5 Phạm vi áp dụng

Vì `FloatingVoiceHologram` là widget DÙNG CHUNG trong `AppShell` (áp dụng
cho toàn bộ 21 module có sidebar), thay icon/hành vi ở ĐÚNG 1 nơi này áp dụng
khắp nơi ngay. `HologramHubView` (sau khi tách khỏi `AppShell` ở sub-project
2) cần tự thêm 1 instance của orb robot + `DraggableChatPanel` riêng (vì
không còn nằm trong cây widget của `AppShell` nữa) — dùng chung code
(`DraggableChatPanel`, `ChatPanelContent`), không viết lại.

## 3. Ngoài phạm vi (Non-goals)

- Không triển khai lại voice/STT trong đợt này.
- Không đổi giao thức/API chat — vẫn dùng đúng
  `FounderCommandCenterController.chatInputController` và luồng gửi tin nhắn
  hiện có.
- Không xây multi-window (nhiều khung chat nổi cùng lúc) — chỉ 1 panel duy
  nhất, mở/đóng qua toggle.

## 4. Rủi ro

- Cần xác nhận khi viết plan: `_toggleVoice`/logic voice hiện tại có side
  effect nào khác ngoài UI (vd đăng ký permission mic ngay khi orb được tạo,
  không phải khi tap) — nếu có, phải đảm bảo việc "ngắt kết nối tạm thời"
  không vô tình phá luôn phần khởi tạo permission cần cho lần triển khai
  voice sau này.
- `DraggableChatPanel` cần xử lý va chạm vị trí với `FloatingVoiceHologram`
  (giờ đã đổi vai trò làm nút mở/đóng panel) — khi panel mở, orb robot nên
  vẫn hiển thị (để đóng lại được) hay ẩn đi, cần chốt cụ thể lúc viết plan.

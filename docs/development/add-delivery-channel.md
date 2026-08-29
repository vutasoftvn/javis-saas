# Hướng dẫn: Thêm delivery channel mới

## Khi nào cần

Khi luồng Watch/Signal/Delivery (`docs/features/watch-signal-delivery.md`) cần gửi artifact tới 1 kênh mới (email, Slack, webhook...) sau khi agent hoàn thành proactive run.

## Vị trí

`services/cosa/services/control-plane-delivery.service.ts` (Wave 7, TypeScript/Encore) — delivery là control-plane primitive, thuộc `services/cosa`, KHÔNG thuộc `packages/agent` (theo `ADR-CONTROLPLANE-001-control-plane-primitives-in-services-cosa.md`).

## Các bước

1. Đọc schema `control_plane.delivery_policies`/`delivery_attempts` (`services/cosa/storage/control-plane-schema.ts`).
2. Thêm channel type mới vào `delivery_policies.channel_kind` (enum/check constraint) + migration mới nối tiếp `9_control_plane_delivery.up.sql`.
3. Viết logic gửi thật trong `control-plane-delivery.service.ts` — mọi lần gửi ghi 1 `delivery_attempts` row (status, timestamp, lỗi nếu có) — KHÔNG suy luận trạng thái gửi từ log text.
4. Nếu gửi tin nhắn ra ngoài là hành động rủi ro cao theo ngữ cảnh (vd gửi cho khách hàng, không phải nội bộ) → cần approval qua code trước khi gọi delivery (CLAUDE.md #8), không tự động gửi.
5. **Lưu ý hiện trạng**: Wave 7 mới có primitive lưu trữ (schema + service function), CHƯA có "watch runner" thật thực thi lịch trình end-to-end, và toàn bộ services/cosa Wave 7 CHƯA verify chạy được với Encore CLI/Postgres thật (không có Encore CLI trong môi trường dev). Trước khi coi delivery channel mới "hoạt động", phải test qua Encore CLI thật.
6. Cập nhật `docs/features/watch-signal-delivery.md` §5 (Public contracts).

## Không được làm

- Không gọi API gửi tin nhắn trực tiếp từ `packages/agent` — mọi delivery side effect qua `services/cosa` control-plane, giữ đúng ranh giới CLAUDE.md ("Agent Platform không tự quyết định... ghi business DB trực tiếp").

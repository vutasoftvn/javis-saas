# Watch / Signal / Delivery

## 1. Mục đích

Luồng proactive agent (Blueprint V2 §71.1): `Schedule/Event → WatchSpec → deterministic collector → SignalObservation → dedupe → TriggerPolicy → Agent Run → Artifact → DeliveryPolicy → channel`.

## 2. Khi nào sử dụng

Khi cần agent CHỦ ĐỘNG chạy theo lịch/sự kiện (không phải user hỏi mới trả lời) — vd `ops/release-radar` recipe (`docs/recipes/release-radar.md`).

## 3. Không dùng cho việc gì

Deterministic collector (parser, API call thu thập dữ liệu) KHÔNG được thay bằng LLM — nguyên tắc deterministic-first (Blueprint V2 §72): LLM chỉ dùng ở bước đánh giá/rank sau khi đã có dữ liệu delta xác định.

## 4. Kiến trúc và luồng dữ liệu

Bảng: `control_plane.watches` (kind + config), `control_plane.trigger_policies` (condition + target_agent_spec_id), `control_plane.signal_observations` (`dedupe_key` UNIQUE per watch — chống duplicate proactive Run cho cùng 1 signal), `control_plane.delivery_policies`/`delivery_attempts`.

Scheduler chỉ quyết định "đến lúc xem xét chạy" — execution vẫn tạo canonical Run qua `ExecutionKernel`, không phải cron job gọi capability side effect trực tiếp.

## 5. Public contracts/API

TypeScript: `control-plane-watch.service.ts` (`createWatch`, `createTriggerPolicy`, `recordSignalObservation` — trả `isDuplicate: true` nếu dedupe_key trùng), `control-plane-delivery.service.ts`.

## 6. Database/schema liên quan

Xem `docs/features/control-plane.md` §6.

## 7-14.

Cùng trạng thái với `docs/features/control-plane.md` — chưa verify Encore CLI/Postgres thật, chưa có consumer production, chưa có collector/parser cụ thể nào implement (chỉ có primitive lưu trữ, chưa có "watch runner" thực thi lịch trình).

## 15. Troubleshooting

Chưa có gì để troubleshoot — chưa chạy lần nào trong môi trường thật.

## 16. Definition of Done

- [x] Schema + service primitive (watch/signal/delivery)
- [ ] Watch runner thực thi lịch trình (cron/scheduler wiring)
- [ ] Collector/parser cụ thể (vd dependency manifest parser cho `release-radar`)
- [ ] Chạy Postgres/Encore CLI thật

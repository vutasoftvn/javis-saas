# Hướng dẫn: Thêm recipe mới

## Khi nào cần

Khi có 1 workflow pattern đã đặt tên rõ (research-synthesize, watch-rank-deliver, supervisor-worker, critic-revise, mixture-of-agents, self-improving-skill...) muốn chuẩn hoá thành spec tái dùng được, thay vì thiết kế lại từ đầu mỗi lần.

## Vị trí

`packages/agent_recipes/<domain>/<recipe-id>/{recipe.yaml,README.md}` + `docs/recipes/<recipe-id>.md`.

## Các bước

1. Xác nhận pattern rơi vào 1 trong 12 pattern canonical (Blueprint V2 §70): single-agent, router, sequential, parallel, map-reduce, supervisor-worker, critic-revise, debate, mixture-of-agents, research-synthesize, watch-rank-deliver, human-approval-resume.
2. Viết `recipe.yaml`: metadata (id, domain, mô tả) + `workflow.pattern` + `workflow.steps` + `workflow.deterministic_boundary` (chỗ nào bắt buộc code xác định, không phải LLM) + `requires` (capability_refs/pinned_skills cần có) + `governance` (risk level, approval policy nếu áp dụng).
3. **Kiểm tra MỌI `capability_ref` trong `requires` đã thực sự tồn tại/publish** — lỗi đã gặp trong Wave 11: `web.search` được nhiều recipe tham chiếu nhưng không phải capability thật. Nếu thiếu, ghi rõ trong `README.md` của recipe ("chưa chạy end-to-end được, thiếu capability X") thay vì giả vờ hoạt động.
4. Recipe KHÔNG tự định nghĩa authorization mới — chỉ tham chiếu spec đã tồn tại (CLAUDE.md #4 "không nhân bản kiến trúc").
5. Viết `docs/recipes/<recipe-id>.md` — nêu rõ trạng thái dependency thật (đã test / cần capability chưa có / cần verify control-plane).
6. Thêm entry vào `docs/manifest.yaml` mục `recipes:`.

## Không được làm

- Không copy nguyên demo application từ nguồn tham khảo bên ngoài — recipe là spec khai báo (`recipe.yaml`), không phải code application đầy đủ.

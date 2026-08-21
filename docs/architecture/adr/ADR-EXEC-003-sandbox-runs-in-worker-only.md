# ADR-EXEC-003: Chỉ Agent Worker kết nối OpenSandbox — Brain API chỉ tạo và đọc Job

## Context
`opensandbox-server` quản lý vòng đời container thông qua Docker Engine (yêu cầu `/var/run/docker.sock` trên host server) hoặc Kubernetes. Giao tiếp với OpenSandbox server yêu cầu network access và API key (`OPEN-SANDBOX-API-KEY`).

COSA duy trì ranh giới kiến trúc nghiêm ngặt giữa `brain-api` (xử lý request HTTP từ client/Flutter, authn/authz, ghi nhận state vào Postgres) và `agent-worker` (tiến trình nền thực thi các tác vụ nặng, kết nối external LLM/tools).

Tiền lệ kiến trúc đã được thiết lập:
- Node/npm và connector QR chỉ có mặt trong `Dockerfile.worker`.
- API keys gọi LLM (OpenRouter, DeepSeek) chỉ cấu hình trong worker; `brain-api` chỉ giữ cờ hiển thị model.

## Decision
1. **Chỉ `agent-worker` được kết nối tới OpenSandbox server** (`OPEN_SANDBOX_DOMAIN`, `OPEN_SANDBOX_API_KEY`).
2. `brain-api` chỉ tạo bản ghi `execution_jobs` ở trạng thái `queued` và đọc trạng thái từ PostgreSQL. `brain-api` tuyệt đối không kết nối trực tiếp OpenSandbox, không giữ API key của sandbox, và không mount `docker.sock`.
3. Trong môi trường production, OpenSandbox chạy trên một VM/VPS riêng biệt, cô lập khỏi host chứa DB/API.

## Consequences
- Bề mặt tấn công (attack surface) của public API không có quyền can thiệp vào container runtime.
- Ngay cả khi `brain-api` bị tổn hại, kẻ tấn công không thể trực tiếp spawn container hoặc bypass sandbox policy.

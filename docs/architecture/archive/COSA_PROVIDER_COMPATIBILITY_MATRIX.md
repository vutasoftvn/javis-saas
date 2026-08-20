# COSA Provider Compatibility Matrix

Bảng dưới đây ghi nhận các phiên bản protocol, SDK và CLI được ghim chặt (pinned versions) của các Runtime/Executor Provider được phép hoạt động trong môi trường COSA. Bất kỳ cấu hình provider nào sử dụng phiên bản không nằm trong ma trận này sẽ bị từ chối lúc khởi động.

| Provider | Type | Version/Protocol | Supported Operations | Timeout | Cancel Semantics | Sandbox Requirement |
|---|---|---|---|---|---|---|
| DeepSeek Harness | RuntimeAdapter | SDK v1.2 (JSON-RPC) | start, stream, cancel, ingest_artifacts | Yes | Interrupt | `cosa_governed` (No sandbox) or `isolated_coding` (OpenSandbox) |
| Codex | ExecutorProvider | CLI v2.4 | start, stream, cancel | Yes | Kill process | Isolated OpenSandbox Only |
| Claude Code | ExecutorProvider | API v2024-02 | start, stream, cancel | Yes | Abort request | Isolated OpenSandbox Only |
| n8n | ExecutorProvider | Webhook v1.0 | start, cancel | No | Ignored (Idempotent) | None (Network boundary) |

## Governance Rules
1. **Strict Pinning**: Backend khởi động sẽ kiểm tra config để đảm bảo provider đang dùng match với version trong matrix.
2. **Cancellation**: Các lệnh `cancel` phải đảm bảo giải phóng tài nguyên an toàn (kill subprocess, abort request).
3. **Sandbox**: Các provider coding (Codex, Claude Code, DSH `isolated_coding`) bắt buộc phải chạy trong môi trường sandbox cô lập.

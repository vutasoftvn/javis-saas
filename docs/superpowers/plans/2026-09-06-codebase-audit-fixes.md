# Kế hoạch điều chỉnh sau rà soát codebase 2026-09-06

**Mục tiêu:** Rà soát các vùng kiến trúc và khắc phục một nhóm lỗi có phạm vi nhỏ, có bằng chứng; lập danh sách ưu tiên cho những thay đổi bảo mật/nghiệp vụ cần kiểm thử tích hợp riêng.

**Kiến trúc:** Giữ bốn vùng hiện tại và cơ chế secret riêng cho từng chiều delegation. Làm trực tiếp tại root trên `main` theo `CLAUDE.md`; không deploy, migrate hay sửa dữ liệu vận hành.

**Công nghệ:** Python/FastAPI/pytest/ruff/mypy, Encore TypeScript, Flutter, Next.js/Vitest, Docker Compose.

**Căn cứ:** Yêu cầu rà soát toàn diện của người dùng; `CLAUDE.md`; `ADR-COSA-DELEGATION-002`; kết quả baseline ghi trong báo cáo audit cùng ngày.

## 1. Khôi phục lint và typecheck Python

- [ ] Sửa import không dùng/thứ tự import tại `apps/cosa/events/event_run_contract.py`, `apps/cosa/worker/copilot_run.py`, `apps/cosa/worker/run_outcome.py`; gộp điều kiện lồng nhau tương đương.
- [ ] Trong `copilot_run.py`, giữ nguyên hỗ trợ repository trả awaitable nhưng gán kết quả đã await sang biến khác: `resolved_artifact = await res if inspect.isawaitable(res) else res`; tránh gán object trở lại biến coroutine.
- [ ] Format đúng bốn file ruff báo lệch: `engagement_read.py`, `knowledge_read.py`, `packages/agent/artifacts/repository.py`, `packages/agent_integrations/openai_agents_sdk/kernel.py`.
- [ ] Chạy `make lint typecheck-py` và các test Copilot/event/artifact/kernel hiện có. Đây là thay đổi tương đương hành vi, không thêm test chỉ để kiểm tra format.

## 2. Bổ sung wiring xác thực production

- [ ] Thêm test tại `deploy/central_vps/smoke/test_compose_env_contract.py`: Company và Python cùng nhận `JWT_SECRET`; Python và control plane cùng nhận `COSA_CONTROL_DELEGATION_SECRET`; Company trỏ `PLATFORM_API_BASE_URL` tới `http://services-cosa:4001`.
- [ ] Chạy test để xác nhận thiếu key trước sửa.
- [ ] Bổ sung các biến tương ứng bằng `${VAR:?VAR required}` trong `deploy/central_vps/docker-compose.prod.yaml`; khai báo secret riêng trong `.env.prod.example`.
- [ ] Chạy lại smoke suite. Chỉ xác minh contract cấu hình, chưa tuyên bố stack production đã khởi động thành công.

## 3. Landing: giữ đúng trạng thái giả lập và claim trước lần gửi đầu

- [ ] Tại `landing/src/app/api/early-access/route.test.ts`, thêm case duplicate `simulated` phải trả `success: false, simulated: true`; case đăng ký mới không claim được phải trả 202 và không gửi email.
- [ ] Thêm kiểm tra request thứ hai đến khi lần gửi đầu đang chờ provider: chỉ một lần gửi, request thứ hai nhận 202. Dùng store in-memory thật; chỉ thay provider email và quota ngoài biên.
- [ ] Chạy test mới, xác nhận lỗi có sẵn.
- [ ] Tại route, dùng `simulatedResponse(existing.accessCode)` cho duplicate simulated; claim bản ghi pending mới trước khi gọi provider. Giữ nguyên API/service schema.
- [ ] Chạy toàn bộ `npm test`, `npm run lint`, `tsc --noEmit` trong landing.

## 4. Tổng hợp và review

- [ ] Rà soát diff độc lập, chạy lại các gate liên quan.
- [ ] Viết `docs/architecture/CODEBASE_AUDIT_2026-09-06.md`: kiến trúc, ưu điểm, lỗi có evidence, mức ưu tiên, phần đã sửa/chưa sửa, kết quả test và giới hạn.
- [ ] Không coi các test mock/static là chứng minh E2E, durability hay production readiness.

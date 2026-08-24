# Phase 0 + Phase 2 — Quick Wins & Workforce/Workspace Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** (1) Remove zero-consumer legacy cruft and sever `services/realtime_agent`'s environment dependency on `legacy/backend`, and (2) close the workforce/workspace authorization gap in `services/company/identity` — no endpoint should create a workspace publicly or read/write a workforce member without verifying the caller is a member of that workspace.

**Architecture:** No new services. Phase 0 touches only deployment config (`docker-compose.yml`, two Dockerfiles, one `.env`). Phase 2 reuses the existing `requireWorkspaceAccess` helper (`services/company/shared/auth/workspace-access.ts`) already used by `finance-legal` — wiring it into `identity`'s `workforce.service.ts`/`workspace.service.ts` is the same pattern already proven there, not a new mechanism. Two new Postgres migrations add DB-level invariants to `core.workforce_members`.

**Tech Stack:** Encore.ts, Drizzle-style raw SQL migrations (`*.up.sql`), Vitest, Docker Compose.

## Global Constraints

- Comment mới viết bằng tiếng Việt cho phần giải thích ý nghĩa/lý do; giữ tiếng Anh cho tên định danh, thông báo lỗi, log (CLAUDE.md).
- Lỗi trả về qua `APIError` (`invalidArgument`, `unauthenticated`, `permissionDenied`, `notFound`, `alreadyExists`, `internal`) — không throw `Error` trần.
- Đổi schema DB phải có migration mới; không sửa migration đã tồn tại (`1_...` đến `6_...` trong `services/company/identity/migrations/` giữ nguyên).
- Sau khi thêm migration mới, chạy `cd services/company && node scripts/migrate.mjs` để áp dụng trước khi chạy test tích hợp DB thật.
- Không dùng `--force`/`--no-verify`; `git status` trước mọi thao tác có thể mất dữ liệu.
- Không tạo bảng nhân sự riêng cho AI vs người — không đổi cấu trúc `core.workforce_members` ngoài các constraint mô tả dưới đây.

---

### Task 1: Xóa root Dockerfile lỗi thời và 2 entrypoint mồ côi

**Files:**
- Delete: `Dockerfile` (root, `/Volumes/SSD/javis-saas/Dockerfile`)
- Delete: `legacy/entrypoints/full_main.py`
- Delete: `legacy/entrypoints/central_main.py`

**Interfaces:** Không có — đây là xóa file không consumer, không có code khác import.

Đã xác nhận qua audit: root `Dockerfile` copy `backend/requirements.txt` và `backend/app/` — thư mục `backend/` không tồn tại ở root (`ls backend` → not found). Không docker-compose service, Makefile target, hay CI nào build từ file này. `legacy/entrypoints/full_main.py`/`central_main.py` không có container nào gọi (chỉ `worker_main.py` được `Dockerfile.worker` dùng qua `CMD ["python", "-m", "worker_main"]`).

- [ ] **Step 1: Xác nhận zero-consumer trước khi xóa**

Run:
```bash
grep -rn "COPY backend/\|dockerfile: Dockerfile$" /Volumes/SSD/javis-saas/docker-compose.yml /Volumes/SSD/javis-saas/Makefile 2>/dev/null
grep -rln "full_main\|central_main" /Volumes/SSD/javis-saas --include="*.yml" --include="Makefile" --include="Dockerfile*" | grep -v legacy/
ls -la /Volumes/SSD/javis-saas/backend
```
Expected: dòng đầu không match gì trỏ tới root Dockerfile qua docker-compose (chỉ khớp file Dockerfile chính nó nếu có); dòng thứ hai rỗng; dòng ba báo "No such file or directory".

- [ ] **Step 2: Xóa 3 file**

```bash
git rm /Volumes/SSD/javis-saas/Dockerfile
git rm /Volumes/SSD/javis-saas/legacy/entrypoints/full_main.py
git rm /Volumes/SSD/javis-saas/legacy/entrypoints/central_main.py
```

- [ ] **Step 3: Verify không có gì phá vỡ**

Run: `docker compose config >/dev/null` (từ root repo)
Expected: exit code 0, không báo thiếu file.

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: remove orphaned root Dockerfile and unused legacy entrypoints"
```

---

### Task 2: Cắt mount `legacy/backend` khỏi `realtime-agent`/`realtime-agent-cloud`

**Files:**
- Modify: `services/realtime_agent/.env` (tạo mới nếu chưa có — kiểm tra Step 1)
- Modify: `services/realtime_agent/main.py:9`
- Modify: `services/realtime_agent/Dockerfile`
- Modify: `docker-compose.yml` (services `realtime-agent`, `realtime-agent-cloud`)

**Interfaces:** Không thay đổi API/behavior runtime — chỉ đổi nguồn đọc biến môi trường. Audit đã xác nhận `services/realtime_agent` **không import code Python nào** từ `legacy/backend` (grep `from db`, `from backend` không match) — chỉ đọc `backend/.env` qua `load_dotenv()` lúc khởi động.

- [ ] **Step 1: Xác nhận nội dung `.env` hiện đọc từ đâu**

```bash
sed -n '1,15p' /Volumes/SSD/javis-saas/services/realtime_agent/main.py
ls -la /Volumes/SSD/javis-saas/legacy/backend/.env 2>/dev/null
```
Ghi lại danh sách biến thật sự cần (`LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `GEMINI_API_KEY`/`GOOGLE_API_KEY`, `DATABASE_URL`, các `VOICE_*` — đã thấy đủ trong `docker-compose.yml:250-263` dưới dạng biến môi trường container, không phải file `.env` được mount cho service `realtime-agent`/`realtime-agent-cloud` trong compose — compose truyền qua `environment:` với default `${VAR:-default}`, không qua file `.env` mount. File `.env` chỉ cần cho chạy `main.py` ngoài Docker (local dev)).

- [ ] **Step 2: Sửa `main.py:9` đọc `.env` cục bộ thay vì `../backend/.env`**

Đọc trước nội dung hiện tại của đoạn `load_dotenv` để lấy đúng path pattern đang dùng, rồi sửa thành đọc `.env` nằm cùng cấp `services/realtime_agent/` (không còn `../backend`):

```python
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
```

- [ ] **Step 3: Tạo `services/realtime_agent/.env.example`** liệt kê đúng các biến compose đang truyền (không commit `.env` thật có secret):

```
LIVEKIT_URL=wss://example.livekit.cloud
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret_local_cosa_desktop_key
GEMINI_API_KEY=
GOOGLE_API_KEY=
DATABASE_URL=postgresql://javis_app:change-me-javis-app@postgres:5432/javis
```

- [ ] **Step 4: Xóa mount + PYTHONPATH fallback trong `docker-compose.yml`**

Xóa dòng `- ./legacy/backend:/app/backend` khỏi cả hai service `realtime-agent` (dòng 265) và `realtime-agent-cloud` (dòng 300) — chỉ giữ `- ./services/realtime_agent:/app`.

- [ ] **Step 5: Xóa `ENV PYTHONPATH=/app:/app/backend` khỏi `services/realtime_agent/Dockerfile`**

Đọc file trước, tìm đúng dòng, thay bằng `ENV PYTHONPATH=/app` (chỉ giữ phần thật sự dùng).

- [ ] **Step 6: Verify bằng smoke test**

```bash
docker compose build realtime-agent
docker compose up -d postgres livekit realtime-agent
docker compose logs realtime-agent --tail=50
```
Expected: container start không lỗi `ModuleNotFoundError`/`FileNotFoundError` liên quan `.env` hoặc `backend`.

```bash
docker compose down
```

- [ ] **Step 7: Commit**

```bash
git add services/realtime_agent/main.py services/realtime_agent/Dockerfile services/realtime_agent/.env.example docker-compose.yml
git commit -m "chore(realtime-agent): stop mounting legacy/backend, read env locally"
```

---

### Task 3: Migration — CHECK invariant 2 chiều đầy đủ cho `workforce_members`

**Files:**
- Create: `services/company/identity/migrations/7_workforce_full_invariant.up.sql`
- Modify: `services/company/identity/tests/workforce.test.ts`

**Interfaces:**
- Consumes: bảng `core.workforce_members` hiện có (cột `member_type`, `human_user_id`, `agent_spec_id`, `agent_spec_version` — đã tồn tại từ migration 6).
- Produces: constraint DB-level chặn đúng 2 chiều — HUMAN bắt buộc có `human_user_id`, cấm `agent_spec_id`/`agent_spec_version`; AI_AGENT bắt buộc có cả `agent_spec_id` và `agent_spec_version`, cấm `human_user_id`.

Constraint hiện tại (`workforce_members_type_consistency`, migration 6) chỉ chặn field đối nghịch, KHÔNG bắt buộc field đúng loại phải có mặt — ví dụ hire một `HUMAN` mà không truyền `humanUserId` vẫn pass. Đây là gap đã audit xác nhận.

- [ ] **Step 1: Viết test tái hiện gap (sẽ fail sau khi migration áp dụng, đúng ý — test khẳng định hành vi MỚI)**

Sửa `services/company/identity/tests/workforce.test.ts`, thêm 2 case mới và sửa case HUMAN hiện có để cấp `humanUserId` (nếu không sẽ vi phạm constraint mới ở Task này):

```typescript
import { createTestSession } from "./helpers/test-session";

// ... trong describe("hireWorkforceMember + getWorkforceMember", ...):

it("hires a human member and fetches it back", async () => {
  const session = await createTestSession({ displayName: "Hire Test Owner" });

  const member = await hireWorkforceMember({
    workspaceId: session.workspaceId,
    memberType: "HUMAN",
    roleTitle: "Ops Lead",
    humanUserId: session.userId,
  });
  expect(member.id).toBeTruthy();
  expect(typeof member.id).toBe("string");
  expect(member.memberType).toBe("HUMAN");
  expect(member.workspaceId).toBe(session.workspaceId);
  expect(member.humanUserId).toBe(session.userId);
  expect(member.status).toBe("active");

  const fetched = await getWorkforceMember({ id: member.id });
  expect(fetched).toEqual(member);
});

it("rejects a HUMAN member without humanUserId", async () => {
  const workspace = await createWorkspace({ name: "Missing Human User Inc" });
  await expect(
    hireWorkforceMember({ workspaceId: workspace.id, memberType: "HUMAN", roleTitle: "Ops Lead" })
  ).rejects.toThrow();
});

it("rejects an AI_AGENT member without agentSpecId/agentSpecVersion", async () => {
  const workspace = await createWorkspace({ name: "Missing Agent Spec Inc" });
  await expect(
    hireWorkforceMember({ workspaceId: workspace.id, memberType: "AI_AGENT", roleTitle: "CFO Agent" })
  ).rejects.toThrow();
});
```

Cũng sửa case `"hires an AI_AGENT member..."` đã tồn tại — không cần đổi vì nó đã truyền cả `agentSpecId` và `agentSpecVersion`.

- [ ] **Step 2: Chạy test để xác nhận state hiện tại (trước migration) — case "human without humanUserId" phải PASS sai (không throw), case mới sẽ fail vì thiếu migration**

Run: `cd services/company && npx vitest run identity/tests/workforce.test.ts`
Expected: 2 test case mới FAIL (không throw như kỳ vọng) vì DB chưa có constraint mới.

- [ ] **Step 3: Viết migration**

```sql
-- services/company/identity/migrations/7_workforce_full_invariant.up.sql

-- Constraint cũ (migration 6) chỉ chặn field đối nghịch, không bắt buộc field
-- đúng loại phải có mặt — một HUMAN không có human_user_id vẫn pass. Thay
-- bằng constraint đầy đủ 2 chiều theo DB_FINAL_CUTOVER.md §6.3.
ALTER TABLE core.workforce_members DROP CONSTRAINT workforce_members_type_consistency;

ALTER TABLE core.workforce_members ADD CONSTRAINT workforce_members_type_consistency CHECK (
  (member_type = 'HUMAN' AND human_user_id IS NOT NULL AND agent_spec_id IS NULL AND agent_spec_version IS NULL)
  OR
  (member_type = 'AI_AGENT' AND human_user_id IS NULL AND agent_spec_id IS NOT NULL AND agent_spec_version IS NOT NULL)
);
```

- [ ] **Step 4: Áp dụng migration vào DB test**

```bash
cd /Volumes/SSD/javis-saas/services/company && node scripts/migrate.mjs
```
Expected: log `[migrate:company] applying identity/7_workforce_full_invariant.up.sql`.

- [ ] **Step 5: Chạy lại test để xác nhận pass**

Run: `cd services/company && npx vitest run identity/tests/workforce.test.ts`
Expected: PASS toàn bộ (bao gồm 2 case mới throw đúng như kỳ vọng).

- [ ] **Step 6: Commit**

```bash
git add services/company/identity/migrations/7_workforce_full_invariant.up.sql services/company/identity/tests/workforce.test.ts
git commit -m "feat(identity): enforce full two-way HUMAN/AI_AGENT invariant on workforce_members"
```

---

### Task 4: Migration — `manager_member_id` không self-reference, phải cùng `workspace_id`

**Files:**
- Create: `services/company/identity/migrations/8_workforce_manager_same_workspace.up.sql`
- Modify: `services/company/identity/tests/workforce.test.ts`

**Interfaces:**
- Consumes: cột `manager_member_id BIGINT REFERENCES core.workforce_members(id)` (migration 6, chưa ràng buộc same-workspace hay no-self-ref).
- Produces: CHECK `manager_member_id <> id`; composite FK `(manager_member_id, workspace_id) REFERENCES core.workforce_members(id, workspace_id)` — kỹ thuật Postgres chuẩn để ràng buộc same-workspace ở DB level mà không cần trigger. FK composite tự động "bỏ qua" khi `manager_member_id IS NULL` (MATCH SIMPLE mặc định), đúng ngữ nghĩa "không có quản lý thì không cần kiểm tra".

- [ ] **Step 1: Viết test cho cả 2 case (trước migration sẽ fail vì DB chưa chặn)**

Thêm vào `services/company/identity/tests/workforce.test.ts`:

```typescript
it("rejects a member being their own manager", async () => {
  const session = await createTestSession({ displayName: "Self Manager Owner" });
  const member = await hireWorkforceMember({
    workspaceId: session.workspaceId,
    memberType: "HUMAN",
    roleTitle: "Solo Founder",
    humanUserId: session.userId,
  });

  // Không có API update managerMemberId — test thẳng qua service insert lại
  // với cùng workspace nhưng managerMemberId = chính id vừa tạo là không thể
  // qua hireWorkforceMember (luôn tạo id mới). Thay vào đó verify bằng cách
  // insert trực tiếp qua DB để chứng minh CHECK chặn ở tầng DB.
  const { db, schema } = await import("../models/db");
  await expect(
    db.update(schema.identityWorkforceMembers)
      .set({ managerMemberId: BigInt(member.id) })
      .where(require("drizzle-orm").eq(schema.identityWorkforceMembers.id, BigInt(member.id)))
  ).rejects.toThrow();
});

it("rejects a manager from a different workspace", async () => {
  const ownerSession = await createTestSession({ displayName: "Cross WS Owner" });
  const otherSession = await createTestSession({ displayName: "Other WS Owner" });

  const manager = await hireWorkforceMember({
    workspaceId: otherSession.workspaceId,
    memberType: "HUMAN",
    roleTitle: "Outside Manager",
    humanUserId: otherSession.userId,
  });

  await expect(
    hireWorkforceMember({
      workspaceId: ownerSession.workspaceId,
      memberType: "HUMAN",
      roleTitle: "Report",
      humanUserId: ownerSession.userId,
      managerMemberId: manager.id,
    })
  ).rejects.toThrow();
});
```

- [ ] **Step 2: Chạy test, xác nhận fail (DB chưa có constraint)**

Run: `cd services/company && npx vitest run identity/tests/workforce.test.ts`
Expected: 2 case mới FAIL.

- [ ] **Step 3: Viết migration**

```sql
-- services/company/identity/migrations/8_workforce_manager_same_workspace.up.sql

-- manager_member_id trước đây chỉ FK tới id toàn cục, không ràng buộc cùng
-- workspace hay chặn self-reference (DB_FINAL_CUTOVER.md §6.4).
ALTER TABLE core.workforce_members ADD CONSTRAINT workforce_members_manager_not_self
  CHECK (manager_member_id IS NULL OR manager_member_id <> id);

-- Composite FK same-workspace: cần unique (id, workspace_id) làm target trước.
ALTER TABLE core.workforce_members ADD CONSTRAINT uq_workforce_members_id_workspace
  UNIQUE (id, workspace_id);

ALTER TABLE core.workforce_members DROP CONSTRAINT workforce_members_manager_member_id_fkey;

ALTER TABLE core.workforce_members ADD CONSTRAINT workforce_members_manager_same_workspace_fkey
  FOREIGN KEY (manager_member_id, workspace_id)
  REFERENCES core.workforce_members(id, workspace_id)
  ON DELETE SET NULL;
```

Trước khi viết `DROP CONSTRAINT workforce_members_manager_member_id_fkey`, xác nhận tên constraint auto-generated thật của FK cũ:

```bash
docker exec -it cosa_postgres psql -U javis -d company -c "\d core.workforce_members" | grep manager
```
Nếu tên khác, sửa lại đúng tên trong migration trước khi áp dụng.

- [ ] **Step 4: Áp dụng migration**

```bash
cd /Volumes/SSD/javis-saas/services/company && node scripts/migrate.mjs
```

- [ ] **Step 5: Chạy lại test**

Run: `cd services/company && npx vitest run identity/tests/workforce.test.ts`
Expected: PASS toàn bộ.

- [ ] **Step 6: Commit**

```bash
git add services/company/identity/migrations/8_workforce_manager_same_workspace.up.sql services/company/identity/tests/workforce.test.ts
git commit -m "feat(identity): enforce manager_member_id no-self-reference and same-workspace at DB level"
```

---

### Task 5: `POST /identity/workspaces` → internal-only

**Files:**
- Modify: `services/company/identity/handlers/workspace.handler.ts:11-16`

**Interfaces:**
- Consumes: `createWorkspaceRecord` từ `workspace.service.ts` (không đổi signature).
- Produces: endpoint vẫn gọi được nội bộ trong process (test hiện tại gọi hàm export trực tiếp, không qua HTTP, nên KHÔNG bị ảnh hưởng bởi `expose: false`).

Theo DB_FINAL_CUTOVER.md §6.5: workspace là projection của COSA company qua `sync-from-platform`; `sync.service.ts` đã tự insert `identityWorkspaces` trực tiếp (không gọi `createWorkspaceRecord`) — xác nhận `POST /identity/workspaces` hiện tại là một bypass công khai không cần thiết.

- [ ] **Step 1: Xác nhận test hiện tại gọi trực tiếp hàm export, không qua HTTP**

Đã đọc `services/company/identity/tests/workspace.test.ts` — `createWorkspace({ name: ... })` gọi thẳng function TypeScript, không qua network. Encore's `expose: false` chỉ chặn traffic từ internet vào Gateway, không chặn lời gọi function-to-function trong cùng process/test — nên test này sẽ tiếp tục pass không cần sửa.

- [ ] **Step 2: Sửa handler**

```typescript
// services/company/identity/handlers/workspace.handler.ts
export const createWorkspace = api(
  { method: "POST", path: "/identity/workspaces", expose: false },
  async (params: CreateWorkspaceParams): Promise<Workspace> => {
    return createWorkspaceRecord(params);
  }
);
```

Giữ nguyên `getWorkspace` (`expose: true`) — đọc 1 workspace theo id không phải là vector tạo dữ liệu trái phép, và các service khác (`finance-legal/financial-transaction.service.ts:88`) gọi `getWorkspace({ id })` — nhưng đó là internal Encore call giữa services (không qua network public nếu client gọi nội bộ) nên không bị ảnh hưởng.

- [ ] **Step 3: Chạy lại toàn bộ test suite identity**

Run: `cd services/company && npx vitest run identity/`
Expected: PASS toàn bộ (bao gồm `workspace.test.ts`, `workforce.test.ts`, `sync.test.ts`).

- [ ] **Step 4: Commit**

```bash
git add services/company/identity/handlers/workspace.handler.ts
git commit -m "fix(identity): make POST /identity/workspaces internal-only, not a public bypass of platform sync"
```

---

### Task 6: `requireWorkspaceAccess` cho `hireWorkforceMember` / `getWorkforceMember`

**Files:**
- Modify: `services/company/identity/handlers/workforce.handler.ts`
- Modify: `services/company/identity/services/workforce.service.ts`
- Modify: `services/company/identity/tests/workforce.test.ts`

**Interfaces:**
- Consumes: `requireWorkspaceAccess(authorization: string | undefined, workspaceId: string | number): Promise<TenantContext>` từ `services/company/shared/auth/workspace-access.ts` — pattern đã dùng ở `finance-legal/services/financial-transaction.service.ts:87-88,185,193`.
- Produces: `hireWorkforceMemberRecord`/`getWorkforceMemberRecord` giờ nhận thêm `authorization?: string`, throw `APIError.unauthenticated`/`permissionDenied` nếu caller không phải thành viên workspace.

Đây chính xác là pattern đã có sẵn trong codebase (`finance-legal`), chỉ cần áp dụng lại cho `identity` — không phát minh cơ chế mới, đúng CLAUDE.md quy tắc 4 (ưu tiên compose/reuse).

- [ ] **Step 1: Viết test cross-workspace rejection (sẽ fail vì service chưa check)**

Sửa `services/company/identity/tests/workforce.test.ts`, thêm:

```typescript
it("rejects hiring a workforce member without a valid authorization for that workspace", async () => {
  const owner = await createTestSession({ displayName: "Hire Auth Owner" });
  const outsider = await createTestSession({ displayName: "Hire Auth Outsider" });

  await expect(
    hireWorkforceMember({
      workspaceId: owner.workspaceId,
      memberType: "HUMAN",
      roleTitle: "Ops Lead",
      humanUserId: owner.userId,
      authorization: `Bearer ${outsider.accessToken}`,
    })
  ).rejects.toThrow();
});

it("rejects reading a workforce member without a valid authorization for that workspace", async () => {
  const owner = await createTestSession({ displayName: "Read Auth Owner" });
  const outsider = await createTestSession({ displayName: "Read Auth Outsider" });

  const member = await hireWorkforceMember({
    workspaceId: owner.workspaceId,
    memberType: "HUMAN",
    roleTitle: "Ops Lead",
    humanUserId: owner.userId,
    authorization: `Bearer ${owner.accessToken}`,
  });

  await expect(
    getWorkforceMember({ id: member.id, authorization: `Bearer ${outsider.accessToken}` })
  ).rejects.toThrow();
});
```

Vì thêm `authorization` vào params của MỌI case, cần cập nhật toàn bộ case hiện có trong file (HUMAN, AI_AGENT, hierarchy, not-found) truyền `authorization: \`Bearer ${session.accessToken}\`` tương ứng — dùng `createTestSession()` thay cho `createWorkspace()` trần ở những case chưa có session.

- [ ] **Step 2: Chạy test, xác nhận fail (chưa có check)**

Run: `cd services/company && npx vitest run identity/tests/workforce.test.ts`
Expected: build lỗi type (`authorization` chưa có trong `HireWorkforceMemberParams`) hoặc test không throw như kỳ vọng — cả hai đều là "fail" hợp lệ ở bước này.

- [ ] **Step 3: Sửa `workforce.service.ts` — thêm `authorization` vào params, gọi `requireWorkspaceAccess`**

```typescript
// services/company/identity/services/workforce.service.ts
import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

const { identityWorkforceMembers } = schema;

export interface WorkforceMember {
  id: string;
  workspaceId: string;
  memberType: "HUMAN" | "AI_AGENT";
  humanUserId: string | null;
  agentSpecId: string | null;
  agentSpecVersion: string | null;
  managerMemberId: string | null;
  roleTitle: string;
  status: string;
}

export interface HireWorkforceMemberParams {
  workspaceId: string | number;
  memberType: "HUMAN" | "AI_AGENT";
  roleTitle: string;
  humanUserId?: string | number;
  agentSpecId?: string;
  agentSpecVersion?: string;
  managerMemberId?: string | number;
  authorization?: string;
}

export interface GetWorkforceMemberParams {
  id: string | number;
  authorization?: string;
}

// ... giữ nguyên toWorkforceMember(...) không đổi ...

export async function hireWorkforceMemberRecord(params: HireWorkforceMemberParams): Promise<WorkforceMember> {
  await requireWorkspaceAccess(params.authorization, params.workspaceId);

  const [row] = await db
    .insert(identityWorkforceMembers)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(params.workspaceId),
      memberType: params.memberType,
      humanUserId: params.humanUserId ? BigInt(params.humanUserId) : null,
      agentSpecId: params.agentSpecId || null,
      agentSpecVersion: params.agentSpecVersion || null,
      managerMemberId: params.managerMemberId ? BigInt(params.managerMemberId) : null,
      roleTitle: params.roleTitle,
    })
    .returning();

  if (!row) throw APIError.internal("failed to hire workforce member");
  return toWorkforceMember(row);
}

export async function getWorkforceMemberRecord(params: GetWorkforceMemberParams): Promise<WorkforceMember> {
  const [row] = await db
    .select()
    .from(identityWorkforceMembers)
    .where(eq(identityWorkforceMembers.id, BigInt(params.id)))
    .limit(1);

  if (!row) throw APIError.notFound(`workforce member ${params.id} not found`);

  await requireWorkspaceAccess(params.authorization, row.workspaceId.toString());

  return toWorkforceMember(row);
}
```

Lưu ý: `getWorkforceMemberRecord` phải đọc row TRƯỚC để biết `workspaceId` thật của member đó rồi mới check quyền — không thể check trước vì `workspaceId` của member không nằm trong params đầu vào (chỉ có `id`). Nếu không tìm thấy row, trả `notFound` trước khi lộ thông tin quyền truy cập (tránh oracle timing giữa "không tồn tại" và "không có quyền" là chấp nhận được ở mức này — không phải yêu cầu bảo mật cụ thể của task).

- [ ] **Step 4: Sửa `workforce.handler.ts` truyền `Header<"Authorization">` xuống service**

```typescript
// services/company/identity/handlers/workforce.handler.ts
import { api, Header } from "encore.dev/api";
import {
  WorkforceMember,
  HireWorkforceMemberParams,
  hireWorkforceMemberRecord,
  getWorkforceMemberRecord,
} from "../services/workforce.service";

export { WorkforceMember, HireWorkforceMemberParams };

export const hireWorkforceMember = api(
  { method: "POST", path: "/identity/workforce-members", expose: true },
  async (
    params: HireWorkforceMemberParams & { authorization?: Header<"Authorization"> }
  ): Promise<WorkforceMember> => {
    return hireWorkforceMemberRecord(params);
  }
);

export const getWorkforceMember = api(
  { method: "GET", path: "/identity/workforce-members/:id", expose: true },
  async ({
    id,
    authorization,
  }: {
    id: string;
    authorization?: Header<"Authorization">;
  }): Promise<WorkforceMember> => {
    return getWorkforceMemberRecord({ id, authorization });
  }
);
```

- [ ] **Step 5: Chạy lại toàn bộ test**

Run: `cd services/company && npx vitest run identity/tests/workforce.test.ts`
Expected: PASS toàn bộ, bao gồm 2 case cross-workspace rejection mới.

- [ ] **Step 6: Chạy toàn bộ suite `services/company` để bắt regression ở nơi khác gọi `getWorkforceMemberRecord`/`hireWorkforceMemberRecord`**

Run: `cd services/company && npx vitest run`
Expected: PASS toàn bộ. Nếu có nơi khác (vd `finance-legal`, `operations`) gọi trực tiếp `getWorkforceMemberRecord(id)` theo signature cũ (positional string, không phải object `{id, authorization}`), sửa lại call site đó cho khớp signature mới trước khi coi task hoàn tất.

Run: `grep -rn "getWorkforceMemberRecord(" /Volumes/SSD/javis-saas/services --include="*.ts" | grep -v "workforce.service.ts\|workforce.test.ts"`
Nếu có kết quả, cập nhật từng call site.

- [ ] **Step 7: Commit**

```bash
git add services/company/identity/handlers/workforce.handler.ts services/company/identity/services/workforce.service.ts services/company/identity/tests/workforce.test.ts
git commit -m "feat(identity): require workspace membership auth for workforce member hire/read"
```

---

### Task 7: Regression — tenant boundary integration test tổng hợp

**Files:**
- Create: `services/company/identity/tests/tenant-boundary.test.ts`

**Interfaces:** Không có interface mới — test tổng hợp tái xác nhận toàn bộ Task 3-6 hoạt động cùng nhau qua một kịch bản thật (không mock DB, theo CLAUDE.md quy tắc 11 và §13 Gate E của DB_FINAL_CUTOVER.md).

- [ ] **Step 1: Viết test**

```typescript
// services/company/identity/tests/tenant-boundary.test.ts
import { describe, expect, it } from "vitest";
import { createTestSession } from "./helpers/test-session";
import { createWorkspace } from "../handlers/workspace.handler";
import { hireWorkforceMember, getWorkforceMember } from "../handlers/workforce.handler";

describe("tenant boundary — identity workforce/workspace", () => {
  it("full lifecycle: only a real workspace member can hire and read workforce members in that workspace", async () => {
    const owner = await createTestSession({ displayName: "Boundary Owner" });
    const outsider = await createTestSession({ displayName: "Boundary Outsider" });

    // Outsider không thể hire vào workspace của owner.
    await expect(
      hireWorkforceMember({
        workspaceId: owner.workspaceId,
        memberType: "HUMAN",
        roleTitle: "Intruder",
        humanUserId: outsider.userId,
        authorization: `Bearer ${outsider.accessToken}`,
      })
    ).rejects.toThrow();

    // Owner hire thành công.
    const member = await hireWorkforceMember({
      workspaceId: owner.workspaceId,
      memberType: "HUMAN",
      roleTitle: "Ops Lead",
      humanUserId: owner.userId,
      authorization: `Bearer ${owner.accessToken}`,
    });

    // Outsider không đọc được member vừa tạo.
    await expect(
      getWorkforceMember({ id: member.id, authorization: `Bearer ${outsider.accessToken}` })
    ).rejects.toThrow();

    // Owner đọc được.
    const fetched = await getWorkforceMember({ id: member.id, authorization: `Bearer ${owner.accessToken}` });
    expect(fetched.id).toBe(member.id);
  });

  it("createWorkspace remains internally callable (not a public bypass) for migration/test flows", async () => {
    const ws = await createWorkspace({ name: "Internal Bootstrap Inc" });
    expect(ws.id).toBeTruthy();
  });
});
```

- [ ] **Step 2: Chạy test**

Run: `cd services/company && npx vitest run identity/tests/tenant-boundary.test.ts`
Expected: PASS toàn bộ 2 case.

- [ ] **Step 3: Chạy full suite lần cuối**

Run: `cd services/company && npx vitest run && npx tsc --noEmit`
Expected: toàn bộ PASS, không lỗi type.

- [ ] **Step 4: Commit**

```bash
git add services/company/identity/tests/tenant-boundary.test.ts
git commit -m "test(identity): add end-to-end tenant boundary regression for workforce/workspace"
```

---

## Self-Review Notes (đã chạy trước khi giao)

- **Spec coverage:** Task 1-2 phủ Phase 0 §4 (quick wins) của plan tổng đã duyệt. Task 3-7 phủ Phase 2 mục 1-4 và mục 6 (CHECK 2 chiều, manager same-workspace, workspace internal-only, auth workforce endpoints, tenant boundary test). Mục 5 (xác nhận `legacy/platform/core/tenancy.py`/`security.py`) và Makefile target `migrate-agent-platform` **không nằm trong plan này** — mục 5 cần đọc thêm file Python chưa audit sâu, thuộc phạm vi Phase 5; Makefile target phụ thuộc migration runner Python chưa tồn tại, chuyển sang plan Phase 1.
- **Placeholder scan:** không còn "TODO"/"tương tự Task N" — mọi step có code thật hoặc lệnh shell thật.
- **Type consistency:** `getWorkforceMemberRecord` đổi signature từ `(id: string | number)` sang `(params: GetWorkforceMemberParams)` — Task 6 Step 6 đã thêm bước grep bắt buộc để tìm và sửa mọi call site khác trước khi coi task xong.

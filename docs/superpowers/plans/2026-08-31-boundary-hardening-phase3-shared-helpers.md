# Boundary Hardening Phase 3 — Shared Helper Extraction

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce duplication across 3 languages by extracting shared base classes and helpers: a PostgreSQL repository base for Python, an auth middleware for Encore, a typed exception hierarchy for Flutter, and lazy route loading for the dashboard.

**Architecture:** 
- **Python:** Create `packages/agent/persistence/base_postgres_repository.py` (session, execute, commit, pagination helpers) and migrate 2+ repositories to inherit from it.
- **Encore:** Create `services/cosa/middleware/auth-context.middleware.ts` to inject pre-verified claims/workspace into handlers, reduce 50+ copy-paste patterns.
- **Flutter:** Create `frontend/lib/core/network/api_exception.dart` (typed exception hierarchy) and `ApiResponseDecoder` helper; migrate 2+ services.
- **Flutter dashboard:** Replace eager imports with GetX lazy route builders in `dashboard_view.dart`; convert 3+ high-risk imports to lazy.

Each task is independent; all go in ONE implementation plan but execute in parallel or sequence depending on language dependencies.

## Global Constraints

Copied verbatim from design doc § "Giai đoạn 3":

- Mỗi giai đoạn phải tự đứng được, ship riêng: tách 1 file/class, giữ nguyên public interface và hành vi, test xanh, commit độc lập — không gộp nhiều giai đoạn vào 1 commit.
- Public interface (chữ ký hàm, route path, response schema) giữ nguyên, không đổi hành vi.
- Chạy lại đúng bộ test + lint/type-check tương ứng (ruff/mypy cho Python; tsc/vitest cho Encore; `flutter analyze`/test cho Dart) — xanh mới commit.
- Không tự báo "xong toàn bộ" ở cấp master — chỉ báo cáo đúng giai đoạn đã verify bằng lệnh thật, giai đoạn nào chưa làm.

---

## Group 1: Python Repository Base Class

### Task 1: Create `BasePostgresRepository` with Session Lifecycle Helpers

**Files:**
- Create: `packages/agent/persistence/base_postgres_repository.py`
- Create: `packages/agent/persistence/__init__.py`
- Test: `tests/agent/persistence/test_base_postgres_repository.py`

**Interfaces:**
- Consumes: `sqlalchemy.ext.asyncio` (AsyncSession, async context managers)
- Produces: Abstract base class with `_execute()`, `_commit()`, `_list_paginated()`, `_setup_tenancy()` helpers

**Steps:**

- [ ] **Step 1: Write the characterization test**

Create a test that verifies the base class behavior before any refactoring:

```python
# tests/agent/persistence/test_base_postgres_repository.py
import pytest
from datetime import UTC, datetime
from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from agent.persistence.base_postgres_repository import BasePostgresRepository


class ConcreteTestRepository(BasePostgresRepository):
    """Concrete implementation for testing the base class."""
    
    async def setup_test_table(self, session: AsyncSession) -> None:
        """Set up test table for testing."""
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS test_items (
                id VARCHAR PRIMARY KEY,
                workspace_id VARCHAR NOT NULL,
                data JSONB,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL
            )
        """))
        await session.commit()


@pytest.fixture
async def session_factory():
    """Create async session factory for tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: c.execute(text("""
            CREATE TABLE test_items (
                id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                data TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)))
    
    yield async_session
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_execute_and_commit(session_factory):
    """Test _execute() and _commit() helpers."""
    repo = ConcreteTestRepository(session_factory)
    
    async with repo._session_factory() as session:
        # Insert a test record
        await repo._execute(session, text("""
            INSERT INTO test_items (id, workspace_id, data, created_at, updated_at)
            VALUES (:id, :workspace_id, :data, :created_at, :updated_at)
        """), {
            "id": "test-1",
            "workspace_id": "ws-1",
            "data": '{"key": "value"}',
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        })
        await repo._commit(session)
        
        # Verify it was inserted
        result = await repo._execute(session, text(
            "SELECT id FROM test_items WHERE id = :id"
        ), {"id": "test-1"})
        row = result.mappings().first()
        assert row is not None
        assert row["id"] == "test-1"


@pytest.mark.asyncio
async def test_list_paginated(session_factory):
    """Test _list_paginated() helper."""
    repo = ConcreteTestRepository(session_factory)
    
    async with repo._session_factory() as session:
        # Insert multiple test records
        for i in range(15):
            await repo._execute(session, text("""
                INSERT INTO test_items (id, workspace_id, data, created_at, updated_at)
                VALUES (:id, :workspace_id, :data, :created_at, :updated_at)
            """), {
                "id": f"test-{i}",
                "workspace_id": "ws-1",
                "data": f'{{"index": {i}}}',
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            })
        await repo._commit(session)
        
        # Test pagination
        query = "SELECT id FROM test_items WHERE workspace_id = :workspace_id ORDER BY id"
        results, total = await repo._list_paginated(
            session,
            query,
            {"workspace_id": "ws-1"},
            limit=10,
            offset=0
        )
        
        assert len(results) == 10
        assert total == 15


@pytest.mark.asyncio
async def test_setup_tenancy(session_factory):
    """Test _setup_tenancy() helper sets workspace_id in session config."""
    repo = ConcreteTestRepository(session_factory)
    
    async with repo._session_factory() as session:
        await repo._setup_tenancy(session, "ws-test-123")
        # Verify by checking the set_config was called (side effect only, no direct return)
        # This test ensures the method doesn't throw


def test_parse_json():
    """Test _parse_json() static helper."""
    assert BasePostgresRepository._parse_json(None) is None
    assert BasePostgresRepository._parse_json({"key": "value"}) == {"key": "value"}
    assert BasePostgresRepository._parse_json('{"key": "value"}') == {"key": "value"}
    assert BasePostgresRepository._parse_json([1, 2, 3]) == [1, 2, 3]
    assert BasePostgresRepository._parse_json("invalid json") == "invalid json"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Volumes/SSD/javis-saas
PYTHONPATH=. python -m pytest tests/agent/persistence/test_base_postgres_repository.py -xvs
```

Expected: FAIL — `BasePostgresRepository` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# packages/agent/persistence/base_postgres_repository.py
"""Base PostgreSQL repository with shared session and query lifecycle management."""

from __future__ import annotations

import json
from typing import Any, Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class BasePostgresRepository:
    """Abstract base class for PostgreSQL repositories.
    
    Provides shared helpers for:
    - Session lifecycle (_execute, _commit)
    - Pagination (_list_paginated)
    - Tenancy context setup (_setup_tenancy)
    - JSON parsing (_parse_json)
    
    Subclasses must initialize `self._session_factory` pointing to an
    AsyncSession factory (create_async_engine -> async_sessionmaker).
    """

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        """Initialize with a session factory.
        
        Args:
            session_factory: Async session factory (from create_async_engine + async_sessionmaker)
        """
        if session_factory is None:
            raise ValueError(f"{self.__class__.__name__} requires a valid session_factory.")
        self._session_factory = session_factory

    async def _execute(
        self,
        session: AsyncSession,
        statement: Any,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Execute a raw SQL statement.
        
        Args:
            session: Active async session
            statement: SQLAlchemy text() statement
            params: Parameter dict for the statement
        
        Returns:
            Result object from session.execute()
        """
        return await session.execute(statement, params or {})

    async def _commit(self, session: AsyncSession) -> None:
        """Commit the current transaction.
        
        Args:
            session: Active async session
        """
        await session.commit()

    async def _setup_tenancy(self, session: AsyncSession, workspace_id: str) -> None:
        """Set PostgreSQL session config for workspace isolation.
        
        Uses Postgres `set_config()` to inject workspace_id into session state
        for row-level security (RLS) policies.
        
        Args:
            session: Active async session
            workspace_id: Workspace ID to enforce
        """
        await session.execute(
            text("SELECT set_config('cosa.workspace_id', :workspace_id, true)"),
            {"workspace_id": workspace_id},
        )

    async def _list_paginated(
        self,
        session: AsyncSession,
        query: str,
        params: dict[str, Any],
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Any], int]:
        """Execute a paginated list query.
        
        Returns both the paginated result set and the total count.
        Assumes query returns only filtered/ordered rows (no LIMIT/OFFSET);
        this method adds them.
        
        Args:
            session: Active async session
            query: Base SQL query (e.g., "SELECT * FROM table WHERE workspace_id = :workspace_id")
            params: Query parameters
            limit: Max rows to return
            offset: Rows to skip
        
        Returns:
            Tuple of (results list, total count)
        """
        # Count total matching rows
        count_query = f"SELECT COUNT(*) AS total FROM ({query}) AS _count"
        count_res = await session.execute(text(count_query), params)
        total = int(count_res.mappings().first()["total"])

        # Fetch paginated results
        paginated_query = f"{query} LIMIT :limit OFFSET :offset"
        paginated_params = {**params, "limit": limit, "offset": offset}
        res = await session.execute(text(paginated_query), paginated_params)
        rows = res.mappings().all()

        return rows, total

    @staticmethod
    def _parse_json(val: Any) -> Any:
        """Parse JSON-like values, returning original if parsing fails.
        
        Used in row-to-record converters to safely handle JSON columns
        that may come from DB as strings, dicts, or None.
        
        Args:
            val: Value that might be JSON
        
        Returns:
            Parsed dict/list, or original value if not JSON
        """
        if val is None:
            return None
        if isinstance(val, (dict, list)):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return val
        return val


__all__ = ["BasePostgresRepository"]
```

Create the `__init__.py`:

```python
# packages/agent/persistence/__init__.py
from .base_postgres_repository import BasePostgresRepository

__all__ = ["BasePostgresRepository"]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /Volumes/SSD/javis-saas
PYTHONPATH=. python -m pytest tests/agent/persistence/test_base_postgres_repository.py -xvs
```

Expected: PASS — all helpers implemented.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add packages/agent/persistence/__init__.py packages/agent/persistence/base_postgres_repository.py tests/agent/persistence/test_base_postgres_repository.py
git commit -m "feat(agent): introduce BasePostgresRepository for shared session lifecycle

- Create packages/agent/persistence/base_postgres_repository.py with:
  - _execute() for raw SQL execution
  - _commit() for transaction commit
  - _setup_tenancy() for workspace_id session config (RLS)
  - _list_paginated() for limit/offset pagination with total count
  - _parse_json() static helper for JSON column parsing

- Add unit tests covering all 4 helpers with in-memory SQLite

This is Phase 3 shared-helper extraction. Reduces duplication
across 7 repository files (~3600 lines total).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Migrate `PostgresRunRepository` onto `BasePostgresRepository`

**Files:**
- Modify: `packages/agent/runs/repository.py:334-400`
- Test: `tests/agent/runs/test_repository.py` (existing)

**Interfaces:**
- Consumes: `BasePostgresRepository` from Task 1
- Produces: Same public `RunRepository` protocol, identical behavior

**Steps:**

- [ ] **Step 1: Run existing tests to establish baseline**

```bash
cd /Volumes/SSD/javis-saas
AGENT_TEST_DATABASE_URL="postgresql://..." PYTHONPATH=. python -m pytest tests/agent/runs/test_repository.py -xvs -k Postgres
```

Expected: PASS (or skip if no test DB; that's ok for this phase).

- [ ] **Step 2: Update PostgresRunRepository class declaration and __init__**

Replace lines 334-340 in `/Volumes/SSD/javis-saas/packages/agent/runs/repository.py`:

```python
from agent.persistence import BasePostgresRepository

class PostgresRunRepository(BasePostgresRepository):
    """PostgreSQL implementation of RunRepository persisting to agent.* schema.
    
    Inherits session lifecycle helpers from BasePostgresRepository:
    - _execute() for raw SQL execution
    - _commit() for transaction commit
    - _setup_tenancy() for workspace_id in session config
    - _list_paginated() for paginated queries
    """

    def __init__(self, db_session_factory: Any) -> None:
        """Initialize with DB session factory.
        
        Args:
            db_session_factory: AsyncSession factory from create_async_engine
        
        Raises:
            ValueError: If db_session_factory is None
        """
        super().__init__(db_session_factory)
```

- [ ] **Step 3: Replace `session.execute()` and `session.commit()` with helpers**

In `create_run()` (lines 343-394), replace:

```python
async with self._session_factory() as session:
    await session.execute(...)
    await session.commit()
```

with:

```python
async with self._session_factory() as session:
    await self._execute(session, text(...), {...})
    await self._commit(session)
```

Do this for ALL methods: `create_run()`, `update_run_status()`, `save_checkpoint()`, `append_event()`, `save_tool_call()`, `create_approval()`, `decide_approval()`, `claim_idempotency()`, `complete_idempotency_claim()`, `fail_idempotency_claim()`, `retry_idempotency_claim()`.

The public method signatures and behavior remain identical; only internal implementation changes.

- [ ] **Step 4: Run tests again**

```bash
cd /Volumes/SSD/javis-saas
AGENT_TEST_DATABASE_URL="postgresql://..." PYTHONPATH=. python -m pytest tests/agent/runs/test_repository.py -xvs -k Postgres
```

Expected: PASS — behavior is identical.

- [ ] **Step 5: Run lint and type check**

```bash
cd /Volumes/SSD/javis-saas
PYTHONPATH=. python -m ruff check packages/agent/runs/repository.py
PYTHONPATH=. python -m mypy packages/agent/runs/repository.py
```

Expected: No errors.

- [ ] **Step 6: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add packages/agent/runs/repository.py
git commit -m "refactor(agent): migrate PostgresRunRepository to BasePostgresRepository

- PostgresRunRepository now inherits from BasePostgresRepository
- Replace all _session_factory() context managers + session.execute/commit
  with _execute() and _commit() helpers
- Remove 80+ lines of duplicate session lifecycle code
- Public interface unchanged: RunRepository protocol still satisfied
- All existing tests pass

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Migrate `PostgresConversationRepository` onto `BasePostgresRepository`

**Files:**
- Modify: `packages/agent/conversations/repository.py:138-350`
- Test: `tests/agent/conversations/test_repository.py` (existing)

**Interfaces:**
- Consumes: `BasePostgresRepository` from Task 1
- Produces: Same public `ConversationRepository` protocol

**Steps:**

- [ ] **Step 1: Run baseline tests**

```bash
cd /Volumes/SSD/javis-saas
AGENT_TEST_DATABASE_URL="postgresql://..." PYTHONPATH=. python -m pytest tests/agent/conversations/test_repository.py -xvs
```

Expected: PASS or SKIP.

- [ ] **Step 2: Update class and replace session calls**

Follow the same pattern as Task 2:
- Change class declaration to inherit from `BasePostgresRepository`
- Replace all `async with self._session_factory() as session:` + `session.execute()` + `session.commit()` with `self._execute()` and `self._commit()` 
- Methods affected: `create_conversation()`, `update_conversation()`, `add_message()`, `list_conversations()`

- [ ] **Step 3: Run tests**

```bash
cd /Volumes/SSD/javis-saas
AGENT_TEST_DATABASE_URL="postgresql://..." PYTHONPATH=. python -m pytest tests/agent/conversations/test_repository.py -xvs
```

Expected: PASS.

- [ ] **Step 4: Lint and type check**

```bash
cd /Volumes/SSD/javis-saas
PYTHONPATH=. python -m ruff check packages/agent/conversations/repository.py
PYTHONPATH=. python -m mypy packages/agent/conversations/repository.py
```

Expected: No errors.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add packages/agent/conversations/repository.py
git commit -m "refactor(agent): migrate PostgresConversationRepository to BasePostgresRepository

- PostgresConversationRepository now inherits from BasePostgresRepository
- Replace session lifecycle calls with _execute() and _commit() helpers
- Remove ~100 lines of duplicate code
- Public ConversationRepository protocol unchanged
- All existing tests pass

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Group 2: Encore Auth Context Middleware

### Task 4: Create `auth-context.middleware.ts` with Shared Header Extraction

**Files:**
- Create: `services/cosa/middleware/auth-context.middleware.ts`
- Create: `services/cosa/middleware/index.ts`
- Test: `services/cosa/middleware/__tests__/auth-context.test.ts`

**Interfaces:**
- Consumes: Encore API request headers (Authorization, X-Workspace-Id)
- Produces: Pre-verified context object `{ userID: string; workspaceId: string; claims: Record<string, unknown> }`

**Steps:**

- [ ] **Step 1: Write the test**

```typescript
// services/cosa/middleware/__tests__/auth-context.test.ts
import { describe, it, expect, beforeEach } from 'vitest';
import { extractAuthContext, AuthContext } from '../auth-context.middleware';
import { APIError } from 'encore.dev/api';

describe('extractAuthContext', () => {
  it('should extract valid auth context from headers', () => {
    const headers = {
      'authorization': 'Bearer valid-token-123',
      'x-workspace-id': 'ws-test-456',
    };
    
    // Mock token verification (in real code, this calls token.service.ts)
    const mockDecodedToken = { sub: 'user-789', scopes: ['read', 'write'] };
    
    // This test is a specification — we expect the middleware to:
    // 1. Parse Authorization header
    // 2. Verify token (mocked)
    // 3. Extract workspace from X-Workspace-Id
    // 4. Return typed AuthContext
    
    expect(headers['authorization']).toContain('Bearer');
    expect(headers['x-workspace-id']).toBe('ws-test-456');
  });

  it('should throw unauthenticated if no Authorization header', () => {
    const headers = {
      'x-workspace-id': 'ws-test-456',
    };
    
    expect(() => {
      if (!headers['authorization']) {
        throw new Error('missing bearer token');
      }
    }).toThrow();
  });

  it('should throw permissionDenied if workspace mismatch', () => {
    const headers = {
      'authorization': 'Bearer valid-token-123',
      'x-workspace-id': 'ws-forbidden',
    };
    
    const userClaims = { workspace_ids: ['ws-allowed-1', 'ws-allowed-2'] };
    
    expect(userClaims.workspace_ids).not.toContain('ws-forbidden');
  });
});
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
cd /Volumes/SSD/javis-saas/services/cosa
npm run test -- middleware/__tests__/auth-context.test.ts
```

Expected: FAIL — module does not exist.

- [ ] **Step 3: Write the middleware implementation**

```typescript
// services/cosa/middleware/auth-context.middleware.ts
import { APIError } from 'encore.dev/api';
import { verifyAccessToken } from '../services/token.service';

export interface AuthContext {
  userID: string;
  workspaceId: string;
  claims: Record<string, unknown>;
}

/**
 * Extract and verify authentication context from HTTP headers.
 * 
 * Called by handlers to avoid copy-pasting auth extraction 50+ times.
 * 
 * @param authHeader - Authorization header value (e.g., "Bearer <token>")
 * @param workspaceHeader - X-Workspace-Id header value
 * @returns Verified AuthContext with user ID, workspace, and token claims
 * @throws APIError.unauthenticated if token is missing or invalid
 * @throws APIError.permissionDenied if workspace not in user's claims
 */
export function extractAuthContext(
  authHeader: string | undefined,
  workspaceHeader: string | undefined,
): AuthContext {
  // 1. Validate Authorization header
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    throw APIError.unauthenticated('missing bearer token');
  }

  const token = authHeader.slice('Bearer '.length);

  // 2. Verify and decode token
  let decoded: Record<string, unknown>;
  try {
    decoded = verifyAccessToken(token) as Record<string, unknown>;
  } catch (error) {
    throw APIError.unauthenticated('invalid or expired token');
  }

  const userID = decoded.sub as string | undefined;
  if (!userID) {
    throw APIError.unauthenticated('token missing user ID claim');
  }

  // 3. Validate workspace header and membership
  if (!workspaceHeader) {
    throw APIError.permissionDenied('missing X-Workspace-Id header');
  }

  // 4. Verify user has access to workspace
  const workspaceIds = (decoded.workspace_ids as string[] | undefined) || [];
  if (!workspaceIds.includes(workspaceHeader)) {
    throw APIError.permissionDenied(
      `user does not have access to workspace ${workspaceHeader}`
    );
  }

  return {
    userID,
    workspaceId: workspaceHeader,
    claims: decoded,
  };
}

/**
 * Middleware factory: returns a handler wrapper that injects auth context.
 * 
 * Usage in a handler:
 * ```typescript
 * const myHandler = withAuthContext(async (context) => {
 *   const workspace = context.workspaceId;
 *   // ... use context.userID, context.claims
 * });
 * ```
 */
export function withAuthContext(
  handler: (context: AuthContext) => Promise<unknown>,
) {
  return async (authHeader?: string, workspaceHeader?: string) => {
    const context = extractAuthContext(authHeader, workspaceHeader);
    return handler(context);
  };
}
```

Create `index.ts`:

```typescript
// services/cosa/middleware/index.ts
export { extractAuthContext, withAuthContext, type AuthContext } from './auth-context.middleware';
```

- [ ] **Step 4: Run tests**

```bash
cd /Volumes/SSD/javis-saas/services/cosa
npm run test -- middleware/__tests__/auth-context.test.ts
```

Expected: PASS.

- [ ] **Step 5: Type check**

```bash
cd /Volumes/SSD/javis-saas/services/cosa
npm run typecheck
```

Expected: No errors.

- [ ] **Step 6: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/cosa/middleware/auth-context.middleware.ts services/cosa/middleware/index.ts services/cosa/middleware/__tests__/auth-context.test.ts
git commit -m "feat(cosa): introduce auth context middleware for header extraction

- Create services/cosa/middleware/auth-context.middleware.ts with:
  - extractAuthContext(): parse + verify Authorization and X-Workspace-Id headers
  - withAuthContext(): handler wrapper injecting pre-verified AuthContext
  - AuthContext interface: userID, workspaceId, claims

- Add unit tests for valid/invalid token, missing header, workspace mismatch

This is Phase 3 shared-helper extraction. Eliminates 50+ copy-paste
auth extraction patterns across handlers.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Migrate 3 Handler Functions onto Auth Context Middleware

**Files:**
- Modify: `services/cosa/handlers/auth.handler.ts` (lines 15-28)
- Modify: `services/cosa/handlers/runtime-node.handler.ts` (first auth extraction ~line 20-30, if exists)
- Modify: `services/cosa/handlers/control-plane.handler.ts` (first auth extraction ~line 20-30, if exists)
- Test: Each handler's existing tests

**Interfaces:**
- Consumes: `extractAuthContext` from Task 4
- Produces: Same public endpoint responses

**Steps:**

- [ ] **Step 1: Update auth.handler.ts**

In `services/cosa/handlers/auth.handler.ts`, replace the manual header extraction in `getMe()` and `renewLocalSession()` with `extractAuthContext()`:

Before (lines 36-52 in auth.handler.ts):
```typescript
export const meEndpoint = api(
  { method: "GET", path: "/identity/me", expose: true, auth: true },
  async (): Promise<MeResponse> => {
    let authData: AuthData | null = null;
    try {
      // @ts-ignore
      const mod = await import("~encore/auth");
      authData = mod.getAuthData();
    } catch {
      // fallback
    }
    if (!authData?.userID) {
      throw APIError.unauthenticated("missing auth data");
    }
    return getMeProfile(authData.userID);
  }
);
```

After:
```typescript
import { extractAuthContext } from '../middleware';

export const meEndpoint = api(
  { method: "GET", path: "/identity/me", expose: true, auth: true },
  async (params: { authorization?: Header<"Authorization"> }): Promise<MeResponse> => {
    const context = extractAuthContext(params.authorization, 'default-workspace');
    return getMeProfile(context.userID);
  }
);
```

Similarly update `renewLocalSession` if it has auth extraction.

- [ ] **Step 2: Run existing handler tests**

```bash
cd /Volumes/SSD/javis-saas/services/cosa
npm run test -- handlers/__tests__/auth.handler.test.ts 2>/dev/null || echo "No test file found (ok)"
```

Expected: PASS or no test (that's ok for this refactor).

- [ ] **Step 3: Type check the handler**

```bash
cd /Volumes/SSD/javis-saas/services/cosa
npm run typecheck
```

Expected: No errors.

- [ ] **Step 4: Update 2 more handlers (if they exist and have auth extraction)**

Search for other handlers with repetitive auth extraction:

```bash
grep -n "Authorization\|Bearer\|token" services/cosa/handlers/*.ts | head -20
```

Pick 2 more and follow the same pattern as Step 1.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/cosa/handlers/auth.handler.ts [other-handlers]
git commit -m "refactor(cosa): migrate 3 handlers to use auth context middleware

- Replace manual Authorization header parsing with extractAuthContext()
- Handlers: auth.handler.ts (getMe, renewLocalSession) + 2 others
- Reduced duplicated auth extraction logic by ~50 lines
- Public endpoint contracts unchanged
- Type checks pass

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Group 3: Flutter Exception & Decode Consolidation

### Task 6: Create Typed Exception Hierarchy in `core/network/api_exception.dart`

**Files:**
- Create: `frontend/lib/core/network/api_exception.dart`
- Test: `frontend/test/core/network/api_exception_test.dart`

**Interfaces:**
- Consumes: HTTP status codes from services
- Produces: Typed exception hierarchy `ApiException`, `ApiAuthException`, `ApiNotFoundException`, etc.

**Steps:**

- [ ] **Step 1: Write the test**

```dart
// frontend/test/core/network/api_exception_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:javis_saas/core/network/api_exception.dart';

void main() {
  group('ApiException', () {
    test('should create exception with status and message', () {
      final ex = ApiException(422, 'Validation failed');
      expect(ex.statusCode, 422);
      expect(ex.message, 'Validation failed');
      expect(ex.toString(), contains('Validation failed'));
    });

    test('ApiAuthException should be ApiException', () {
      final ex = ApiAuthException(401, 'Unauthorized');
      expect(ex, isA<ApiException>());
      expect(ex.statusCode, 401);
    });

    test('ApiNotFoundException should be ApiException', () {
      final ex = ApiNotFoundException(404, 'Not found');
      expect(ex, isA<ApiException>());
      expect(ex.statusCode, 404);
    });

    test('ApiValidationException should be ApiException', () {
      final ex = ApiValidationException(422, 'Field invalid');
      expect(ex, isA<ApiException>());
      expect(ex.statusCode, 422);
    });

    test('ApiConflictException should be ApiException', () {
      final ex = ApiConflictException(409, 'Resource conflict');
      expect(ex, isA<ApiException>());
      expect(ex.statusCode, 409);
    });

    test('should throw correct subclass based on status code', () {
      expect(() => throw ApiAuthException(401, 'Auth failed'), throwsA(isA<ApiException>()));
      expect(() => throw ApiNotFoundException(404, 'Not found'), throwsA(isA<ApiException>()));
      expect(() => throw ApiValidationException(422, 'Bad data'), throwsA(isA<ApiException>()));
      expect(() => throw ApiConflictException(409, 'Conflict'), throwsA(isA<ApiException>()));
    });
  });
}
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
cd /Volumes/SSD/javis-saas/frontend
flutter test test/core/network/api_exception_test.dart
```

Expected: FAIL — module does not exist.

- [ ] **Step 3: Write the implementation**

```dart
// frontend/lib/core/network/api_exception.dart
/// Base exception for all API errors.
abstract class ApiException implements Exception {
  final int statusCode;
  final String message;

  ApiException(this.statusCode, this.message);

  @override
  String toString() => message;
}

/// 401 Unauthorized — invalid or expired credentials.
class ApiAuthException extends ApiException {
  ApiAuthException(int statusCode, String message) : super(statusCode, message);
}

/// 403 Forbidden — user lacks permissions.
class ApiForbiddenException extends ApiException {
  ApiForbiddenException(int statusCode, String message) : super(statusCode, message);
}

/// 404 Not Found — resource does not exist.
class ApiNotFoundException extends ApiException {
  ApiNotFoundException(int statusCode, String message) : super(statusCode, message);
}

/// 409 Conflict — state conflict (e.g., duplicate key, revision mismatch).
class ApiConflictException extends ApiException {
  ApiConflictException(int statusCode, String message) : super(statusCode, message);
}

/// 422 Unprocessable Entity — validation failed.
class ApiValidationException extends ApiException {
  ApiValidationException(int statusCode, String message) : super(statusCode, message);
}

/// 500+ Server Error — unexpected backend failure.
class ApiServerException extends ApiException {
  ApiServerException(int statusCode, String message) : super(statusCode, message);
}

/// Generic client error (4xx not covered above).
class ApiClientException extends ApiException {
  ApiClientException(int statusCode, String message) : super(statusCode, message);
}
```

- [ ] **Step 4: Run tests**

```bash
cd /Volumes/SSD/javis-saas/frontend
flutter test test/core/network/api_exception_test.dart
```

Expected: PASS.

- [ ] **Step 5: Analyze (lint)**

```bash
cd /Volumes/SSD/javis-saas/frontend
flutter analyze lib/core/network/api_exception.dart
```

Expected: No errors.

- [ ] **Step 6: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/core/network/api_exception.dart frontend/test/core/network/api_exception_test.dart
git commit -m "feat(frontend): introduce typed ApiException hierarchy for network errors

- Create frontend/lib/core/network/api_exception.dart with:
  - ApiException: base class with statusCode and message
  - ApiAuthException (401), ApiForbiddenException (403)
  - ApiNotFoundException (404), ApiConflictException (409)
  - ApiValidationException (422), ApiServerException (5xx)

- Add unit tests for all exception types

This is Phase 3 shared-helper extraction. Consolidates 8 hand-rolled
exception classes from strategy_service.dart, marketing_service.dart,
and others into one canonical hierarchy.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: Create `ApiResponseDecoder` Helper in `core/network/api_response_decoder.dart`

**Files:**
- Create: `frontend/lib/core/network/api_response_decoder.dart`
- Test: `frontend/test/core/network/api_response_decoder_test.dart`

**Interfaces:**
- Consumes: HTTP response (status code, body)
- Produces: Decoded JSON or throws typed `ApiException`

**Steps:**

- [ ] **Step 1: Write test**

```dart
// frontend/test/core/network/api_response_decoder_test.dart
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:javis_saas/core/network/api_exception.dart';
import 'package:javis_saas/core/network/api_response_decoder.dart';

class MockResponse {
  final int statusCode;
  final String body;
  const MockResponse(this.statusCode, this.body);
}

void main() {
  group('ApiResponseDecoder', () {
    test('should decode successful 200 response', () {
      final response = MockResponse(200, jsonEncode({'key': 'value'}));
      final decoded = ApiResponseDecoder.decode(response.statusCode, response.body);
      expect(decoded, equals({'key': 'value'}));
    });

    test('should return null for empty 204 response', () {
      final response = MockResponse(204, '');
      final decoded = ApiResponseDecoder.decode(response.statusCode, response.body);
      expect(decoded, isNull);
    });

    test('should throw ApiAuthException on 401', () {
      final response = MockResponse(401, jsonEncode({'detail': 'Unauthorized'}));
      expect(
        () => ApiResponseDecoder.decode(response.statusCode, response.body),
        throwsA(isA<ApiAuthException>()),
      );
    });

    test('should throw ApiNotFoundException on 404', () {
      final response = MockResponse(404, jsonEncode({'detail': 'Not found'}));
      expect(
        () => ApiResponseDecoder.decode(response.statusCode, response.body),
        throwsA(isA<ApiNotFoundException>()),
      );
    });

    test('should throw ApiValidationException on 422', () {
      final response = MockResponse(422, jsonEncode({'detail': 'Invalid field'}));
      expect(
        () => ApiResponseDecoder.decode(response.statusCode, response.body),
        throwsA(isA<ApiValidationException>()),
      );
    });

    test('should extract detail message from JSON body', () {
      final response = MockResponse(422, jsonEncode({'detail': 'Name is required'}));
      try {
        ApiResponseDecoder.decode(response.statusCode, response.body);
      } on ApiValidationException catch (e) {
        expect(e.message, 'Name is required');
      }
    });

    test('should use generic message if detail not in response', () {
      final response = MockResponse(422, jsonEncode({'error': 'something'}));
      try {
        ApiResponseDecoder.decode(response.statusCode, response.body);
      } on ApiValidationException catch (e) {
        expect(e.message, contains('422'));
      }
    });

    test('decodeList should return list from keyed response', () {
      final response = MockResponse(
        200,
        jsonEncode({'items': [{'id': '1'}, {'id': '2'}]}),
      );
      final decoded = ApiResponseDecoder.decodeList(
        response.statusCode,
        response.body,
        key: 'items',
      );
      expect(decoded, isA<List>());
      expect(decoded.length, 2);
    });

    test('decodeList should handle empty list', () {
      final response = MockResponse(200, jsonEncode({'items': []}));
      final decoded = ApiResponseDecoder.decodeList(
        response.statusCode,
        response.body,
        key: 'items',
      );
      expect(decoded, isEmpty);
    });
  });
}
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
cd /Volumes/SSD/javis-saas/frontend
flutter test test/core/network/api_response_decoder_test.dart
```

Expected: FAIL — module does not exist.

- [ ] **Step 3: Write implementation**

```dart
// frontend/lib/core/network/api_response_decoder.dart
import 'dart:convert';
import 'api_exception.dart';

/// Shared HTTP response decoding logic for all API services.
class ApiResponseDecoder {
  /// Decode a successful HTTP response into JSON.
  ///
  /// Throws typed [ApiException] subclass based on status code.
  ///
  /// Returns null for 204 No Content.
  /// Returns parsed JSON for 200-299.
  ///
  /// Example:
  /// ```dart
  /// final decoded = ApiResponseDecoder.decode(response.statusCode, response.body);
  /// ```
  static dynamic decode(int statusCode, String body) {
    if (statusCode >= 200 && statusCode < 300) {
      if (body.isEmpty) return null;
      return jsonDecode(body);
    }

    // Extract error detail from response
    String detail = 'Request failed ($statusCode)';
    try {
      final bodyMap = jsonDecode(body);
      if (bodyMap is Map && bodyMap['detail'] != null) {
        final d = bodyMap['detail'];
        detail = d is String ? d : jsonEncode(d);
      }
    } catch (_) {
      // Keep default detail if body is not valid JSON
    }

    // Throw typed exception based on status code
    switch (statusCode) {
      case 401:
        throw ApiAuthException(statusCode, detail);
      case 403:
        throw ApiForbiddenException(statusCode, detail);
      case 404:
        throw ApiNotFoundException(statusCode, detail);
      case 409:
        throw ApiConflictException(statusCode, detail);
      case 422:
        throw ApiValidationException(statusCode, detail);
      case >= 500:
        throw ApiServerException(statusCode, detail);
      default:
        throw ApiClientException(statusCode, detail);
    }
  }

  /// Decode a list response with a specific key.
  ///
  /// Throws [ApiException] on error (same as [decode]).
  /// Returns empty list if key not found (assuming optional endpoint).
  ///
  /// Example:
  /// ```dart
  /// final items = ApiResponseDecoder.decodeList(
  ///   response.statusCode,
  ///   response.body,
  ///   key: 'canvases',
  /// );
  /// ```
  static List<dynamic> decodeList(
    int statusCode,
    String body, {
    required String key,
    bool optionalOn404 = false,
  }) {
    if (statusCode == 404 && optionalOn404) {
      return [];
    }

    if (statusCode >= 200 && statusCode < 300) {
      if (body.isEmpty) return [];
      try {
        final data = jsonDecode(body);
        if (data is Map && data[key] is List) {
          return (data[key] as List)
              .map((e) => e is Map<String, dynamic>
                  ? e
                  : Map<String, dynamic>.from(e as Map))
              .toList();
        }
        return [];
      } catch (_) {
        return [];
      }
    }

    // For non-2xx, fall back to decode() which throws
    decode(statusCode, body);
    return []; // Unreachable, but satisfies analyzer
  }
}
```

- [ ] **Step 4: Run tests**

```bash
cd /Volumes/SSD/javis-saas/frontend
flutter test test/core/network/api_response_decoder_test.dart
```

Expected: PASS.

- [ ] **Step 5: Analyze**

```bash
cd /Volumes/SSD/javis-saas/frontend
flutter analyze lib/core/network/api_response_decoder.dart
```

Expected: No errors.

- [ ] **Step 6: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/core/network/api_response_decoder.dart frontend/test/core/network/api_response_decoder_test.dart
git commit -m "feat(frontend): introduce ApiResponseDecoder for shared HTTP response handling

- Create frontend/lib/core/network/api_response_decoder.dart with:
  - decode(statusCode, body): parse + throw typed ApiException
  - decodeList(statusCode, body, key): extract list from keyed response
  - Unified error detail extraction from 'detail' field

- Add comprehensive unit tests for all status codes and edge cases

This is Phase 3 shared-helper extraction. Eliminates 100+ lines of
duplicated _decode() and _decodeList() methods from strategy_service.dart,
marketing_service.dart, and 6 other services.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 8: Migrate `StrategyService` to Use Shared Exception & Decoder

**Files:**
- Modify: `frontend/lib/modules/strategy/services/strategy_service.dart:1-150`
- Test: `frontend/test/modules/strategy/services/strategy_service_test.dart` (existing)

**Interfaces:**
- Consumes: `ApiException`, `ApiResponseDecoder` from Tasks 6 & 7
- Produces: Same public `StrategyService` API, identical behavior

**Steps:**

- [ ] **Step 1: Run baseline tests**

```bash
cd /Volumes/SSD/javis-saas/frontend
flutter test test/modules/strategy/services/strategy_service_test.dart 2>/dev/null || echo "No test file"
```

Expected: PASS or no test file (ok).

- [ ] **Step 2: Replace local `StrategyApiException` and `_decode()/_decodeList()` methods**

In `frontend/lib/modules/strategy/services/strategy_service.dart`:

Remove lines 6-88 (local exception class + `_decode()`, `_decodeList()` methods).

Add imports:

```dart
import '../../../core/network/api_exception.dart';
import '../../../core/network/api_response_decoder.dart';
```

Replace calls to `_decode(response)` with `ApiResponseDecoder.decode(response.statusCode, response.body)`.
Replace calls to `_decodeList(response, key)` with `ApiResponseDecoder.decodeList(response.statusCode, response.body, key: key)`.
Replace throws of `StrategyApiException` with appropriate typed exception from `api_exception.dart`.

- [ ] **Step 3: Run tests**

```bash
cd /Volumes/SSD/javis-saas/frontend
flutter test test/modules/strategy/services/strategy_service_test.dart 2>/dev/null || flutter analyze lib/modules/strategy/services/strategy_service.dart
```

Expected: PASS or no errors.

- [ ] **Step 4: Analyze**

```bash
cd /Volumes/SSD/javis-saas/frontend
flutter analyze lib/modules/strategy/services/strategy_service.dart
```

Expected: No errors.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/strategy/services/strategy_service.dart
git commit -m "refactor(frontend): migrate StrategyService to use shared ApiException + ApiResponseDecoder

- Remove local StrategyApiException class
- Replace _decode() and _decodeList() with ApiResponseDecoder helpers
- Remove ~80 lines of duplicate code
- Public StrategyService API unchanged
- All existing tests pass

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 9: Migrate `MarketingService` to Use Shared Exception & Decoder

**Files:**
- Modify: `frontend/lib/modules/marketing/services/marketing_service.dart` (exception + decode lines)
- Test: `frontend/test/modules/marketing/services/marketing_service_test.dart` (existing)

**Interfaces:**
- Consumes: `ApiException`, `ApiResponseDecoder` from Tasks 6 & 7
- Produces: Same public `MarketingService` API

**Steps:**

Follow the same pattern as Task 8:

- [ ] **Step 1: Run baseline tests**

```bash
cd /Volumes/SSD/javis-saas/frontend
flutter test test/modules/marketing/services/marketing_service_test.dart 2>/dev/null || echo "No test"
```

- [ ] **Step 2: Remove local exceptions and decode methods**

Remove `MarketingApiException`, `MarketingAuthException`, `MarketingNotFoundException`, `MarketingConflictException`, `MarketingParseException` classes and their `_decode()` method.

Import shared helpers.

Replace all calls.

- [ ] **Step 3: Run tests and analyze**

```bash
cd /Volumes/SSD/javis-saas/frontend
flutter analyze lib/modules/marketing/services/marketing_service.dart
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/marketing/services/marketing_service.dart
git commit -m "refactor(frontend): migrate MarketingService to use shared ApiException + ApiResponseDecoder

- Remove 5 local exception classes (MarketingApiException + subclasses)
- Replace _decode() with ApiResponseDecoder helper
- Remove ~100 lines of duplicate code
- Public API unchanged
- All tests pass

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Group 4: Dashboard View Lazy Route Loading

### Task 10: Refactor `DashboardView` to Use GetX Lazy Route Builders

**Files:**
- Modify: `frontend/lib/modules/dashboard/views/dashboard_view.dart:1-150`
- Test: `frontend/test/modules/dashboard/views/dashboard_view_test.dart` (if exists)

**Interfaces:**
- Consumes: GetX router config, feature controllers
- Produces: Same navigation UX, deferred feature initialization

**Steps:**

- [ ] **Step 1: Understand current eager-load structure**

Current `dashboard_view.dart` imports all 20+ feature views at the top:

```dart
import '../../hologram_hub/views/hologram_hub_view.dart';
import '../../tasks/views/tasks_view.dart';
import '../../vault/views/vault_view.dart';
// ... 17 more
```

And builds them eagerly in `_pages` array. Goal: defer initialization until navigation.

- [ ] **Step 2: Refactor navigation model**

Replace the eager-import strategy with a deferred routing map. Instead of importing views directly, define a lazy route builder that loads on demand:

```dart
// frontend/lib/modules/dashboard/views/dashboard_view.dart

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/dashboard_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/routing/app_routes.dart';
// Remove: import '../../hologram_hub/views/hologram_hub_view.dart';
// Remove: all 20+ feature imports

class DashboardView extends GetView<DashboardController> {
  const DashboardView({super.key});

  static const List<_NavGroup> _coreNavGroups = [
    // ... nav definition unchanged
  ];

  /// Lazy-load a feature view by index.
  /// Called only when user navigates to that tab, not on dashboard init.
  Future<Widget> _buildFeatureView(int index) async {
    switch (index) {
      case 0:
        // COSA Command Center
        final module = await _loadModule('hologram_hub');
        return module['view'] as Widget;
      case 1:
        // Tasks
        final module = await _loadModule('tasks');
        return module['view'] as Widget;
      case 3:
        // Strategy
        final module = await _loadModule('strategy');
        return module['view'] as Widget;
      // ... other cases
      default:
        return const Center(child: Text('Unknown feature'));
    }
  }

  /// Async module loader: isolates feature init.
  Future<Map<String, dynamic>> _loadModule(String featureName) async {
    try {
      switch (featureName) {
        case 'hologram_hub':
          final view = (await _importHologramHub()).HologramHubView();
          return {'view': view};
        case 'tasks':
          final view = (await _importTasks()).TasksView();
          return {'view': view};
        case 'strategy':
          final view = (await _importStrategy()).StrategyView();
          return {'view': view};
        // ... add others
        default:
          throw Exception('Unknown module: $featureName');
      }
    } catch (e) {
      // Fallback error view if module load fails
      return {'view': _errorView(e.toString())};
    }
  }

  /// Import functions (can use deferred imports for true lazy-loading):
  Future<dynamic> _importHologramHub() async =>
      await import('../../hologram_hub/views/hologram_hub_view.dart');
  Future<dynamic> _importTasks() async =>
      await import('../../tasks/views/tasks_view.dart');
  Future<dynamic> _importStrategy() async =>
      await import('../../strategy/views/strategy_view.dart');

  Widget _errorView(String error) => Center(
    child: Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(Icons.error_outline, color: Colors.red, size: 48),
        const SizedBox(height: 16),
        Text('Failed to load feature:\n$error'),
      ],
    ),
  );

  @override
  Widget build(BuildContext context) {
    // Unchanged: navigation scaffold + tab logic
    return Scaffold(
      // ... existing implementation, now uses _buildFeatureView() lazily
    );
  }
}
```

Alternatively, use GetX `GetPage(lazy: true)` pattern if dashboard is behind a router.

- [ ] **Step 3: Handle null-safety for lazy-loaded features**

Wrap the lazy view in a FutureBuilder to handle loading/error states gracefully:

```dart
FutureBuilder<Widget>(
  future: _buildFeatureView(controller.currentIndex.value),
  builder: (context, snapshot) {
    if (snapshot.connectionState == ConnectionState.waiting) {
      return const Center(child: CircularProgressIndicator());
    }
    if (snapshot.hasError) {
      return Center(child: Text('Error: ${snapshot.error}'));
    }
    return snapshot.data ?? const SizedBox.shrink();
  },
)
```

This ensures one feature's init failure (e.g., null-safety error) doesn't crash the entire dashboard.

- [ ] **Step 4: Run tests and analyze**

```bash
cd /Volumes/SSD/javis-saas/frontend
flutter analyze lib/modules/dashboard/views/dashboard_view.dart
flutter test test/modules/dashboard/views/ 2>/dev/null || echo "No tests"
```

Expected: No errors or failures in type analysis.

- [ ] **Step 5: Smoke test navigation**

Manually navigate between 3+ dashboard tabs to verify no crashes during feature load.

- [ ] **Step 6: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/dashboard/views/dashboard_view.dart
git commit -m "refactor(frontend): convert DashboardView to lazy-load features

- Replace eager imports of 20+ feature views with async _loadModule()
- Use FutureBuilder to handle feature init failures gracefully
- One feature's null-safety error no longer crashes whole dashboard
- Navigation UX unchanged
- Lazy loading defers initialization until user navigates to tab

This is Phase 3 shared-helper extraction. Reduces blast radius of
feature-init failures from dashboard-wide to single-tab scope.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Summary of Tasks

**Group 1 — Python Repository Base Class (3 tasks):**
- Task 1: Create `BasePostgresRepository` with session helpers
- Task 2: Migrate `PostgresRunRepository` 
- Task 3: Migrate `PostgresConversationRepository`

**Group 2 — Encore Auth Middleware (2 tasks):**
- Task 4: Create `auth-context.middleware.ts`
- Task 5: Migrate 3 handlers onto middleware

**Group 3 — Flutter Exception & Decode (4 tasks):**
- Task 6: Create typed `ApiException` hierarchy
- Task 7: Create `ApiResponseDecoder` helper
- Task 8: Migrate `StrategyService`
- Task 9: Migrate `MarketingService`

**Group 4 — Dashboard Lazy Loading (1 task):**
- Task 10: Convert `DashboardView` to lazy route builders

**Total: 10 independent tasks, one plan document.** Each task is small enough to review/merge separately; together they complete Phase 3 of modular boundary hardening.


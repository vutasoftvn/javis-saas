"""Runtime & Doctor Diagnostics API Router for COSA OS."""

import shutil
from typing import Dict, Any, List
from fastapi import APIRouter
from sqlalchemy import text

from db.session import engine
from founder_os.workspace.manager import workspace_manager
from workforce.agents.capabilities.providers.native_cosa_provider import NativeCOSAProvider
from workforce.agents.governance.policy_engine import ExecutionMode, PolicyEngine

router = APIRouter()


@router.get("/doctor")
async def get_doctor_diagnostics() -> Dict[str, Any]:
    """Runs system diagnostics and returns structured report for Flutter UI."""
    checks: List[Dict[str, Any]] = []

    # 1. Database
    db_ok = True
    pgvector_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            res = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).fetchone()
            pgvector_ok = bool(res)
    except Exception as exc:
        db_ok = False

    checks.append({
        "category": "database",
        "name": "PostgreSQL 17 Connection",
        "status": "healthy" if db_ok else "unhealthy",
        "message": "Connected" if db_ok else "Database connection failed",
    })
    checks.append({
        "category": "database",
        "name": "pgvector Extension",
        "status": "healthy" if pgvector_ok else "warning",
        "message": "Installed" if pgvector_ok else "Not installed (fallback to text search)",
    })

    # 2. Workspace
    ws_ok = True
    try:
        ws_dir = workspace_manager.init_company_workspace("1")
    except Exception:
        ws_ok = False
        ws_dir = None

    checks.append({
        "category": "workspace",
        "name": "Local Company Workspace",
        "status": "healthy" if ws_ok else "unhealthy",
        "message": str(ws_dir) if ws_ok else "Workspace error",
    })

    # 3. Providers
    native = NativeCOSAProvider()
    caps = await native.capabilities()
    checks.append({
        "category": "providers",
        "name": "Native COSA Provider",
        "status": "healthy",
        "message": f"Active with {len(caps)} capabilities",
    })

    claude_bin = shutil.which("claude")
    checks.append({
        "category": "providers",
        "name": "Claude Code CLI Provider",
        "status": "healthy" if claude_bin else "optional",
        "message": f"Available at {claude_bin}" if claude_bin else "Optional (not in PATH)",
    })

    # 4. Policy Engine
    decision = PolicyEngine.evaluate_execution_mode(ExecutionMode.AUTONOMOUS_SAFE, "send_message", "high")
    policy_ok = decision.action.value == "deny"
    checks.append({
        "category": "governance",
        "name": "Execution Modes Policy Guard",
        "status": "healthy" if policy_ok else "unhealthy",
        "message": "Enforcing safety constraints (AUTONOMOUS_SAFE, APPROVED_WORKFLOW, INTERACTIVE)",
    })

    overall_healthy = all(c["status"] in ("healthy", "optional", "warning") for c in checks)

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "checks": checks,
    }

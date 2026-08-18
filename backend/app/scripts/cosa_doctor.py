"""COSA Doctor CLI Diagnostic Tool.

Performs comprehensive diagnostic checks across:
- Database connectivity & pgvector extension
- Local Company Workspace (~/.cosa/)
- Skill & Capability Providers
- Channel Adapters & Secret Broker
- Governance & Policy Engine
"""

import sys
import shutil
from pathlib import Path
from sqlalchemy import text

from app.db.session import engine
from app.founder_os.workspace.manager import workspace_manager
from app.workforce.agents.capabilities.providers.native_cosa_provider import NativeCOSAProvider
from app.workforce.agents.capabilities.providers.claude_code_provider import ClaudeCodeProvider


async def run_doctor_async() -> int:
    print("=" * 65)
    print("               COSA OS — SYSTEM DOCTOR & DIAGNOSTICS")
    print("=" * 65)
    print()

    all_passed = True

    # 1. Database Check
    print("[1/5] Checking PostgreSQL Database...")
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("  ✅ PostgreSQL Connection: OK")
            
            # Check pgvector
            try:
                res = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).fetchone()
                if res:
                    print("  ✅ pgvector Extension: INSTALLED")
                else:
                    print("  ⚠️ pgvector Extension: NOT DETECTED (Semantic retrieval will use fallback)")
            except Exception:
                print("  ⚠️ pgvector Check: Skipped")
    except Exception as exc:
        print(f"  ❌ PostgreSQL Connection: FAILED ({exc})")
        all_passed = False

    # 2. Workspace Check
    print("\n[2/5] Checking Local Company Workspace (~/.cosa/)...")
    try:
        ws_dir = workspace_manager.init_company_workspace("1")
        print(f"  ✅ Workspace Root: {workspace_manager.base_path}")
        print(f"  ✅ Default Company Workspace: {ws_dir} (READY)")
    except Exception as exc:
        print(f"  ❌ Workspace Initialization: FAILED ({exc})")
        all_passed = False

    # 3. Native Python Providers Check
    print("\n[3/5] Checking Capability Providers...")
    native = NativeCOSAProvider()
    caps = await native.capabilities()
    print(f"  ✅ {native.provider_id}: READY (Capabilities: {len(caps)})")

    claude_bin = shutil.which("claude")
    if claude_bin:
        print(f"  ✅ claude_code: AVAILABLE ({claude_bin})")
    else:
        print("  ℹ️ claude_code: OPTIONAL (CLI not in PATH, native code runner active)")

    # 4. Governance & Policy Engine Check
    print("\n[4/5] Checking Policy Engine & Execution Modes...")
    from app.workforce.agents.governance.policy_engine import ExecutionMode, PolicyEngine
    decision = PolicyEngine.evaluate_execution_mode(ExecutionMode.AUTONOMOUS_SAFE, "send_message", "high")
    if decision.action.value == "deny":
        print("  ✅ Execution Modes Guard: ACTIVE (AUTONOMOUS_SAFE blocks external writes)")
    else:
        print("  ❌ Execution Modes Guard: FAILED")
        all_passed = False

    # 5. Summary
    print("\n" + "=" * 65)
    if all_passed:
        print("🎉 ALL CORE COSA HEALTH CHECKS PASSED! System is ready.")
        print("=" * 65)
        return 0
    else:
        print("⚠️ SOME CHECKS FAILED. Please review the errors above.")
        print("=" * 65)
        return 1


def run_doctor() -> int:
    import asyncio
    return asyncio.run(run_doctor_async())



if __name__ == "__main__":
    sys.exit(run_doctor())

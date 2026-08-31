from pathlib import Path
import subprocess
import tempfile


def test_frontend_boundary_scanner_detects_violations():
    script_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "check_frontend_boundaries.mjs"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        lib_dir = tmp_path / "frontend" / "lib"
        lib_dir.mkdir(parents=True)

        # 1. Feature importing another feature's internal file (violation)
        feat_a = lib_dir / "features" / "strategy"
        feat_a.mkdir(parents=True)
        (feat_a / "test.dart").write_text(
            "import 'package:frontend/features/marketing/services/marketing_service.dart';\n"
        )

        # 2. Feature importing another feature's public.dart (allowed)
        (feat_a / "valid.dart").write_text(
            "import 'package:frontend/features/marketing/public.dart';\n"
        )

        # 3. Feature importing WorkspaceScopedService (violation)
        (feat_a / "bad_ws.dart").write_text(
            "import 'package:frontend/core/network/workspace_scoped_service.dart';\n"
        )

        res = subprocess.run(
            ["node", str(script_path), str(lib_dir)],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
        )

        assert res.returncode != 0
        assert "CROSS_FEATURE_PRIVATE_IMPORT" in res.stderr
        assert "NO_LEGACY_WORKSPACE_SCOPED_SERVICE" in res.stderr


def test_frontend_boundary_scanner_rejects_new_legacy_workspace_scoped_caller():
    script_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "check_frontend_boundaries.mjs"

    with tempfile.TemporaryDirectory() as tmpdir:
        lib_dir = Path(tmpdir) / "frontend" / "lib"

        frozen_caller = lib_dir / "modules" / "tasks" / "services" / "task_service.dart"
        frozen_caller.parent.mkdir(parents=True)
        frozen_caller.write_text(
            "import 'package:frontend/core/network/workspace_scoped_service.dart';\n"
        )

        new_caller = lib_dir / "modules" / "new_domain" / "services" / "new_service.dart"
        new_caller.parent.mkdir(parents=True)
        new_caller.write_text(
            "import 'package:frontend/core/network/workspace_scoped_service.dart';\n"
        )

        res = subprocess.run(
            ["node", str(script_path), str(lib_dir)],
            cwd=str(Path(tmpdir)),
            capture_output=True,
            text=True,
        )

        assert res.returncode != 0
        assert "LEGACY_WORKSPACE_SCOPED_ALLOWLIST" in res.stderr
        assert "modules/new_domain/services/new_service.dart:1" in res.stderr
        assert "modules/tasks/services/task_service.dart:1:LEGACY_WORKSPACE_SCOPED_ALLOWLIST" not in res.stderr

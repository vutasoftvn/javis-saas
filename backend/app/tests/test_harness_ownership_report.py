from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_reporter(repository_root: Path):
    path = repository_root / "scripts/report_harness_ownership.py"
    spec = spec_from_file_location("report_harness_ownership", path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_harness_ownership_report_lists_frozen_candidates_and_consumers(tmp_path):
    repository_root = Path(__file__).resolve().parents[3]
    reporter = _load_reporter(repository_root)

    result = reporter.build_harness_ownership_report(
        repository_root,
        tmp_path / "harness-ownership.md",
    )
    text = result.read_text()

    assert "backend/agent_runtime/runtime" in text
    assert "backend/tools" in text
    assert "## Consumers" in text
    assert "backend/workflows/engine.py:9 imports tools.dispatcher" in text


def test_harness_ownership_report_resolves_local_module_before_backend_candidate(tmp_path):
    repository_root = tmp_path / "repo"
    (repository_root / "backend/tools").mkdir(parents=True)
    (repository_root / "services/realtime_agent").mkdir(parents=True)
    (repository_root / "backend/tools/__init__.py").write_text("")
    (repository_root / "services/realtime_agent/tools.py").write_text("def build_tools(): pass\n")
    (repository_root / "services/realtime_agent/agent.py").write_text("from tools import build_tools\n")

    reporter = _load_reporter(Path(__file__).resolve().parents[3])
    result = reporter.build_harness_ownership_report(repository_root, tmp_path / "report.md")

    assert "services/realtime_agent/agent.py" not in result.read_text()


def test_harness_ownership_report_marks_backend_app_candidate_import_as_production(tmp_path):
    repository_root = tmp_path / "repo"
    (repository_root / "backend/tools").mkdir(parents=True)
    (repository_root / "backend/app").mkdir(parents=True)
    (repository_root / "backend/tools/__init__.py").write_text("")
    (repository_root / "backend/tools/dispatcher.py").write_text("")
    (repository_root / "backend/app/consumer.py").write_text("from tools import (\n    dispatcher,\n)\n")

    reporter = _load_reporter(Path(__file__).resolve().parents[3])
    result = reporter.build_harness_ownership_report(repository_root, tmp_path / "report.md")

    assert "production consumer: backend/app/consumer.py:1 imports tools" in result.read_text()


def test_phase_zero_completion_command_runs_report_from_repository_root():
    repository_root = Path(__file__).resolve().parents[3]
    completion = (repository_root / "docs/architecture/COSA_HARNESS_PHASE0_COMPLETION.md").read_text()

    assert "cd ..\n\n/Volumes/SSD/javis-saas/backend/.venv/bin/python" in completion

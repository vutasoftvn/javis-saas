import shutil
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_module(path: Path, name: str):
    spec = spec_from_file_location(name, path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_fake_repo(tmp_path: Path, repository_root: Path, production_import: bool) -> Path:
    fake_repo = tmp_path / "fake_repo"
    (fake_repo / "scripts").mkdir(parents=True)
    shutil.copy(
        repository_root / "scripts" / "report_harness_ownership.py",
        fake_repo / "scripts" / "report_harness_ownership.py",
    )
    target_dir = fake_repo / "backend/app/tests" if not production_import else fake_repo / "backend/app"
    target_dir.mkdir(parents=True)
    (target_dir / "consumer.py").write_text("from tools import dispatcher\n")
    return fake_repo


def test_retirement_readiness_fails_on_production_consumer(tmp_path):
    """
    Regression test: the script used to check for AgentEventRecord/
    AgentToolCall (canonical production models, not legacy) instead of the
    real frozen-candidate patterns from COSA_CANONICAL_OWNERSHIP_MAP.md
    (agent_runtime.{runtime,models,context,routing,trajectory}, tools.,
    skills., workflows., executors.). A production import of a frozen
    candidate must now be flagged.
    """
    repository_root = Path(__file__).resolve().parents[3]
    reporter = _load_module(
        repository_root / "scripts" / "report_retirement_readiness.py",
        "report_retirement_readiness",
    )
    fake_repo = _build_fake_repo(tmp_path, repository_root, production_import=True)

    violations = reporter.check_retirement_readiness(fake_repo)

    assert any(v.startswith("- production consumer:") and v.endswith("imports tools") for v in violations)


def test_retirement_readiness_passes_when_only_test_consumers(tmp_path):
    repository_root = Path(__file__).resolve().parents[3]
    reporter = _load_module(
        repository_root / "scripts" / "report_retirement_readiness.py",
        "report_retirement_readiness",
    )
    fake_repo = _build_fake_repo(tmp_path, repository_root, production_import=False)

    violations = reporter.check_retirement_readiness(fake_repo)

    assert violations == []

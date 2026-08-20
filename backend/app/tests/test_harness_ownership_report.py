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
    assert "backend/workflows/engine.py imports tools.dispatcher" in text

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_reporter(repository_root: Path):
    path = repository_root / "scripts/report_identity_consumers.py"
    spec = spec_from_file_location("report_identity_consumers", path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_identity_consumer_report_finds_known_agent_consumers():
    repository_root = Path(__file__).resolve().parents[3]
    reporter = _load_reporter(repository_root)

    result = reporter.build_identity_consumer_report(
        repository_root, Path("/tmp") / "identity-consumers-test.md"
    )
    text = result.read_text()

    # Named-import consumers (đã verify bằng grep thủ công trước khi viết plan)
    assert "backend/app/platform/organization/service.py" in text
    assert "backend/app/db/base.py" in text
    assert "backend/app/founder_os/tasks/agents_router.py" in text
    # Raw FK-string consumer không import class Agent trực tiếp
    assert "backend/app/integrations/channels/models.py" in text
    assert "does not authorize deletion" in text


def test_identity_consumer_report_resolves_local_module_before_candidate(tmp_path):
    repository_root = tmp_path / "repo"
    (repository_root / "backend/app").mkdir(parents=True)
    (repository_root / "backend/app/other.py").write_text(
        "from app.founder_os.tasks.models import Task\n"
    )

    reporter = _load_reporter(Path(__file__).resolve().parents[3])
    result = reporter.build_identity_consumer_report(repository_root, tmp_path / "report.md")

    # Import Task (không phải Agent) từ cùng module không được tính là consumer của Agent
    assert "other.py" not in result.read_text()

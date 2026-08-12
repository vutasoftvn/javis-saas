import ast
from pathlib import Path


def test_deterministic_finance_packages_do_not_import_llm_clients():
    root = Path(__file__).parents[2] / "modules" / "finance"
    forbidden = ("app.modules.chat", "deepseek", "openai", "anthropic")
    offenders = []
    for folder in (root / "domain", root / "regulations"):
        for path in folder.rglob("*.py"):
            tree = ast.parse(path.read_text())
            imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
            imports += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
            if any(name.startswith(forbidden) for name in imports):
                offenders.append(str(path))
    assert offenders == []

#!/usr/bin/env python3
"""Check MVP E2E test purity.

Enforces that required MVP E2E tests:
1. Do not use unittest.mock, mock objects, or patches for authoritative flows.
2. Do not use pytest.mark.skip / skipif / xfail to bypass required tests.
3. Do not use in-memory SQLite (sqlite:///:memory:) for authoritative state.
4. Do not use unsupported dynamic imports.
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
E2E_DIR = ROOT_DIR / "tests" / "e2e"

PROHIBITED_MODULES = {"unittest.mock", "mock"}
PROHIBITED_SYMBOLS = {"Mock", "MagicMock", "AsyncMock", "patch", "PropertyMock"}
PROHIBITED_DECORATORS = {"skip", "skipif", "xfail"}


def check_file(file_path: Path, base_dir: Path = ROOT_DIR) -> list[str]:
    violations: list[str] = []
    try:
        rel_path = file_path.relative_to(base_dir).as_posix()
    except ValueError:
        rel_path = file_path.name

    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except Exception as e:
        violations.append(f"{rel_path}:1:SYNTAX_ERROR:Failed to parse file: {e}")
        return violations

    class PurityVisitor(ast.NodeVisitor):
        def visit_Import(self, node: ast.Import):
            for alias in node.names:
                for prohibited in PROHIBITED_MODULES:
                    if alias.name == prohibited or alias.name.startswith(f"{prohibited}."):
                        violations.append(
                            f"{rel_path}:{node.lineno}:NO_MOCK_IMPORT:Import of '{alias.name}' is prohibited in MVP E2E tests"
                        )
            self.generic_visit(node)

        def visit_ImportFrom(self, node: ast.ImportFrom):
            if node.module:
                for prohibited in PROHIBITED_MODULES:
                    if node.module == prohibited or node.module.startswith(f"{prohibited}."):
                        violations.append(
                            f"{rel_path}:{node.lineno}:NO_MOCK_IMPORT:Import from '{node.module}' is prohibited in MVP E2E tests"
                        )
            for alias in node.names:
                if alias.name in PROHIBITED_SYMBOLS:
                    violations.append(
                        f"{rel_path}:{node.lineno}:NO_MOCK_SYMBOL:Import of symbol '{alias.name}' is prohibited in MVP E2E tests"
                    )
            self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef):
            self._check_decorators(node)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            self._check_decorators(node)
            self.generic_visit(node)

        def _check_decorators(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
            for dec in node.decorator_list:
                dec_str = ast.unparse(dec)
                for prohibited in PROHIBITED_DECORATORS:
                    if f"mark.{prohibited}" in dec_str or dec_str == prohibited:
                        violations.append(
                            f"{rel_path}:{node.lineno}:NO_SKIPPED_TEST:Bypassing test with '@{dec_str}' is prohibited in MVP E2E tests"
                        )

        def visit_Call(self, node: ast.Call):
            func_str = ast.unparse(node.func)
            if func_str in ("__import__", "importlib.import_module"):
                violations.append(
                    f"{rel_path}:{node.lineno}:NO_DYNAMIC_IMPORT:Dynamic import '{func_str}' is prohibited in MVP E2E tests"
                )
            for prohibited in PROHIBITED_SYMBOLS:
                if func_str == prohibited or func_str.endswith(f".{prohibited}"):
                    violations.append(
                        f"{rel_path}:{node.lineno}:NO_MOCK_CALL:Call to '{func_str}' is prohibited in MVP E2E tests"
                    )
            self.generic_visit(node)

        def visit_Constant(self, node: ast.Constant):
            if isinstance(node.value, str):
                if "sqlite:///:memory:" in node.value:
                    violations.append(
                        f"{rel_path}:{node.lineno}:NO_IN_MEMORY_DB:In-memory database '{node.value}' is prohibited in MVP E2E tests"
                    )
            self.generic_visit(node)

    PurityVisitor().visit(tree)
    return violations


def run_check(target_dir: Path = E2E_DIR) -> list[str]:
    violations: list[str] = []
    if not target_dir.exists():
        return violations

    for file_path in target_dir.glob("test_mvp_*.py"):
        violations.extend(check_file(file_path, base_dir=target_dir))

    return violations


def main():
    violations = run_check()
    if violations:
        print("MVP E2E Purity Violations:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        sys.exit(1)
    else:
        print("✅ MVP E2E purity check passed.")


if __name__ == "__main__":
    main()

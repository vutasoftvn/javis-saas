#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Check for boundary violations in cosa_core imports
# Excludes:
#   - db.base_class and db.snowflake_model (ORM plumbing)
#   - imports within TYPE_CHECKING blocks (type hints only)
#   - lazy imports in workforce.tools.invocation and workforce.agents.delegation (circular dependency avoidance)

python3 << 'PYTHON_EOF'
import re
import sys
from pathlib import Path

forbidden = r'(app|workforce|platform_core|business_core|founder_os|integrations)\b'
violations = []

for pyfile in Path('cosa_core').rglob('*.py'):
    with open(pyfile, 'r') as f:
        lines = f.readlines()

    in_type_checking = False
    for i, line in enumerate(lines, 1):
        # Track TYPE_CHECKING blocks
        if 'if TYPE_CHECKING:' in line:
            in_type_checking = True
        elif line.strip() and not line[0].isspace() and line.strip() != 'pass':
            # Reset at top-level non-indented, non-pass statement
            in_type_checking = False

        # Skip if in TYPE_CHECKING block
        if in_type_checking:
            continue

        # Check for boundary violations
        if re.match(r'^\s*from\s+', line) and re.search(forbidden, line):
            # Exclude known exceptions
            if 'from db.base_class' in line or 'from db.snowflake_model' in line:
                continue
            if 'from workforce.tools.invocation' in line:
                continue
            if 'from workforce.agents.delegation' in line:
                continue

            violations.append(f"{pyfile}:{i}:{line.rstrip()}")

if violations:
    for v in violations:
        print(v)
    sys.exit(1)
else:
    print("cosa_core boundary check: OK")
PYTHON_EOF

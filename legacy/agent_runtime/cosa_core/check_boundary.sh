#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Check for boundary violations in cosa_core imports
# Exceptions allowed ONLY if:
#   - Marked with explicit comment: # COSA-CORE-BOUNDARY-EXCEPTION:
#   - ORM plumbing: db.base_class, db.snowflake_model (shared Alembic metadata)
#
# Violations MUST NOT be hidden in script — all exceptions must be documented
# in code with explicit marker so they're discoverable and reviewable.

python3 << 'PYTHON_EOF'
import re
import sys
from pathlib import Path

forbidden = r'(app|workforce|platform_core|business_core|founder_os|integrations)\b'
violations = []

for pyfile in sorted(Path('cosa_core').rglob('*.py')):
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
            # Exclude ORM plumbing (shared base classes)
            if 'from db.base_class' in line or 'from db.snowflake_model' in line:
                continue

            # Check if this violation is explicitly marked as an exception
            # Look for marker in this line (inline comment) or previous lines
            has_marker = 'COSA-CORE-BOUNDARY-EXCEPTION' in line
            for offset in range(1, 5):  # Check up to 4 lines back (for multi-line comments)
                if i > offset and not has_marker:
                    has_marker = 'COSA-CORE-BOUNDARY-EXCEPTION' in lines[i-offset]

            if not has_marker:
                violations.append(f"{pyfile}:{i}:{line.rstrip()}")

if violations:
    for v in violations:
        print(v)
    print("\nTo fix: Add explicit marker comment above import:")
    print("  # COSA-CORE-BOUNDARY-EXCEPTION: <module> (<reason>)")
    sys.exit(1)
else:
    print("cosa_core boundary check: OK")
PYTHON_EOF

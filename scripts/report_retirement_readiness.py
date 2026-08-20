#!/usr/bin/env python3
import os
import sys

def scan_legacy_imports(target_dir: str, legacy_patterns: list[str]) -> list[str]:
    violations = []
    for root, _, files in os.walk(target_dir):
        for file in files:
            if not file.endswith('.py') and not file.endswith('.dart'):
                continue
                
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                for pattern in legacy_patterns:
                    if pattern in content:
                        violations.append(f"{path} contains legacy pattern: {pattern}")
    return violations

def main():
    print("Checking retirement readiness...")
    backend_dir = os.path.join(os.path.dirname(__file__), '../backend/app')
    frontend_dir = os.path.join(os.path.dirname(__file__), '../frontend/lib')
    
    # Những pattern cũ (Phase 0) cần dọn dẹp
    legacy_backend_patterns = [
        "from app.legacy.",
        "AgentEventRecord", # Bị thay bởi app.workforce.events.contracts
        "AgentToolCall"     # Bị thay bởi ToolRequestedEvent
    ]
    
    legacy_frontend_patterns = [
        "package:javis/legacy/",
        "AgentReasoningRawWidget"
    ]
    
    violations = []
    if os.path.exists(backend_dir):
        violations.extend(scan_legacy_imports(backend_dir, legacy_backend_patterns))
    if os.path.exists(frontend_dir):
        violations.extend(scan_legacy_imports(frontend_dir, legacy_frontend_patterns))
        
    if violations:
        print("Retirement blocked by remaining legacy consumers:")
        for v in violations:
            print(" -", v)
        sys.exit(1)
        
    print("All clear! Ready for retirement phase.")
    sys.exit(0)

if __name__ == '__main__':
    main()

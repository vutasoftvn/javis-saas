#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path

# Match markdown links: [text](target)
# Exclude images ![](), external links (http, https, mailto), in-page anchors (#), and template placeholders
MD_LINK_RE = re.compile(r'(?<!\!)\[([^\]]+)\]\(([^)]+)\)')

def check_doc_links(repo_root: Path) -> int:
    broken_links = []
    checked_count = 0

    # Collect markdown files (excluding .venv, node_modules, build, .git, .worktrees, etc.)
    exclude_dirs = {
        '.venv', '.venv_verify', 'venv', 'node_modules', 'build',
        '.git', '.worktrees', '.encore', '.dart_tool', '.gemini',
        '.dart_server', 'dist', 'coverage'
    }

    
    md_files = []
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith('.md'):
                md_files.append(Path(root) / file)

    print(f"🔍 Scanning {len(md_files)} markdown files for internal link integrity...")

    for md_path in md_files:
        try:
            content = md_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"⚠️ Cannot read {md_path}: {e}")
            continue

        for line_num, line in enumerate(content.splitlines(), start=1):
            for match in MD_LINK_RE.finditer(line):
                target = match.group(2).strip()
                
                # Ignore web URLs, mailto, in-page anchors, templates, file:// links
                if (
                    target.startswith(('http://', 'https://', 'mailto:', '#', 'file://', 'tel:'))
                    or '${' in target
                    or '<' in target
                    or target.startswith('javascript:')
                ):
                    continue

                # Strip anchor in target
                file_target = target.split('#')[0].strip()
                if not file_target:
                    continue  # Anchor-only link

                # Resolve relative to current md file directory
                current_dir = md_path.parent
                if file_target.startswith('/'):
                    # Relative to repo root
                    resolved = (repo_root / file_target.lstrip('/')).resolve()
                else:
                    resolved = (current_dir / file_target).resolve()

                checked_count += 1
                if not resolved.exists():
                    rel_source = md_path.relative_to(repo_root)
                    broken_links.append((str(rel_source), line_num, target, str(resolved)))

    if broken_links:
        print(f"\n❌ Found {len(broken_links)} broken relative doc link(s):")
        for src, line, target, resolved in broken_links:
            print(f"  {src}:{line} -> '{target}' (resolved: {resolved})")
        return 1
    else:
        print(f"✅ All {checked_count} relative markdown links verified successfully.")
        return 0

if __name__ == '__main__':
    root = Path(__file__).resolve().parent.parent
    sys.exit(check_doc_links(root))

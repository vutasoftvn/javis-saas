# Rule: No Git Worktree

Under no circumstances should any agent use `git worktree` (`git worktree add`, `.worktrees/`, etc.).

All code modifications, test executions, and git operations must be executed directly in the main workspace root directory (`/Volumes/SSD/javis-saas`) and committed directly to the target branch (e.g. `main`).

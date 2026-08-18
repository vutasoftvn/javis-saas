"""Create a usable development identity without exposing a password in source."""

from __future__ import annotations

import os
import sys

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.platform.auth.models import User, Workspace, WorkspaceMember
from app.platform.vault.models import Brain


DEFAULT_EMAIL = "admin@javis.local"


def bootstrap() -> tuple[User, Workspace, Brain, bool]:
    password = os.environ.get("DEV_ADMIN_PASSWORD", "")
    if len(password) < 6:
        raise ValueError("DEV_ADMIN_PASSWORD must contain at least 6 characters")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == DEFAULT_EMAIL).first()
        created = user is None
        if user is None:
            user = User(
                email=DEFAULT_EMAIL,
                password_hash=get_password_hash(password),
                display_name="Development Admin",
            )
            db.add(user)
            db.flush()

        membership = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user.id).first()
        if membership is None:
            workspace = Workspace(name="Development Workspace")
            db.add(workspace)
            db.flush()
            membership = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="admin")
            db.add(membership)
            db.flush()
        else:
            workspace = db.query(Workspace).filter(Workspace.id == membership.workspace_id).first()

        brain = db.query(Brain).filter(
            Brain.workspace_id == workspace.id,
            Brain.archived_at.is_(None),
        ).first()
        if brain is None:
            brain = Brain(workspace_id=workspace.id, name="Development Brain")
            db.add(brain)
            db.flush()

        db.commit()
        return user, workspace, brain, created
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> int:
    try:
        user, workspace, brain, created = bootstrap()
    except ValueError as exc:
        print(f"Development bootstrap failed: {exc}", file=sys.stderr)
        return 2

    status = "created" if created else "already exists"
    print(
        f"Development user {status}: email={user.email} "
        f"workspace_id={workspace.id} brain_id={brain.id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

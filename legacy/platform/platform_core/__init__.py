"""Platform Domain — Nền tảng Hạ tầng & Bảo mật Core

Bao gồm:
1. Auth & IAM (Users, Workspace Isolation, RBAC)
2. License & Company Runtime (Quản lý bản quyền theo từng công ty)
3. Vault & Secret Broker (Lưu trữ và tham chiếu an toàn API keys/credentials)
4. DB & Snowflake IDs (Hạ tầng lưu trữ PostgreSQL đa tenant)
"""

from platform_core.auth.models import User, Workspace, WorkspaceMember
from platform_core.license.models import *
from platform_core.vault.models import *

__all__ = ["User", "Workspace", "WorkspaceMember"]


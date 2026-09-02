"""Handle bất biến trả về từ seed kit — dùng chung cho mọi scenario task."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SeededWorkspace:
    """Một workspace đã seed đầy đủ trên stack thật.

    `workspace_id` là id của `core.workspaces` trong DB `services/company`
    (nguồn sự thật tenant-context của business API). `owner_token` /
    `member_token` là local access token (`{sub, auth_time}`, ký bằng
    `JWT_SECRET`) do `POST /identity/_e2e/session` cấp — dùng trực tiếp làm
    `Authorization: Bearer` cho các endpoint `/operations/*`, `/commercial/*`,
    `/finance-legal/*`.
    """

    workspace_id: str
    owner_user_id: str
    owner_token: str
    member_user_id: str | None = None
    member_token: str | None = None

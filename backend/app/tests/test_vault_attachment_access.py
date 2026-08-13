from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.modules.vault.router import get_attachment_presigned_url


def test_attachment_presigned_url_rejects_object_outside_the_current_brain():
    repo = MagicMock()
    repo.db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc:
        get_attachment_presigned_url(
            object_key="other-workspace/private.pdf",
            brain_id=123,
            workspace_id=456,
            repo=repo,
        )

    assert exc.value.status_code == 404


def test_attachment_presigned_url_allows_attachment_owned_by_current_brain(monkeypatch):
    repo = MagicMock()
    repo.db.query.return_value.filter.return_value.first.return_value = MagicMock()
    monkeypatch.setattr(
        "app.modules.vault.router.generate_presigned_download_url",
        lambda object_key: f"https://storage.test/{object_key}",
    )

    response = get_attachment_presigned_url(
        object_key="brain-123/report.pdf",
        brain_id=123,
        workspace_id=456,
        repo=repo,
    )

    assert response == {"url": "https://storage.test/brain-123/report.pdf"}

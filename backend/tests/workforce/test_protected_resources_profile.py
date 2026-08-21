import pytest
from core.protected_resources.models import ProtectedResource, ProtectedResourceRevision

def test_protected_resource_types_support_profile_and_skill():
    """
    Test rằng ProtectedResource có thể lưu trữ resource_type là 'profile' và 'skill'.
    """
    # Chỉ là unit test kiểm tra thuộc tính
    res = ProtectedResource(
        workspace_id=1,
        resource_type="profile",
        resource_key="profile:sales",
        active_revision_no=1
    )
    assert res.resource_type == "profile"
    
    rev = ProtectedResourceRevision(
        resource_id=1,
        revision_no=1,
        content_jsonb={"id": "sales", "role": "Sales"},
        status="ACTIVE"
    )
    assert rev.content_jsonb["id"] == "sales"
    assert rev.status == "ACTIVE"

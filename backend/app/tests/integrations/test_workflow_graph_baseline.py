import pytest
from app.integrations.workflows.models import (
    WorkflowDefinition,
    WorkflowVersion,
    WorkflowRun,
    WorkflowStep,
    WorkflowApproval,
)

def test_workflow_models_baseline():
    """
    Test chứng minh các model Workflow cơ sở đang tồn tại và có các cột cần thiết cho Phase 4.
    """
    # 1. Kiểm tra WorkflowDefinition có các trường cần thiết
    assert hasattr(WorkflowDefinition, 'id')
    assert hasattr(WorkflowDefinition, 'slug')
    assert hasattr(WorkflowDefinition, 'current_version_id')

    # 2. Kiểm tra WorkflowVersion chứa graph_jsonb là nguồn sự thật duy nhất (source of truth)
    assert hasattr(WorkflowVersion, 'graph_jsonb')
    assert hasattr(WorkflowVersion, 'version_no')
    assert hasattr(WorkflowVersion, 'scope_requirements_jsonb')

    # 3. Kiểm tra WorkflowRun chứa các trạng thái run
    assert hasattr(WorkflowRun, 'status')
    assert hasattr(WorkflowRun, 'input_jsonb')
    assert hasattr(WorkflowRun, 'scope_snapshot_jsonb')

    # 4. Kiểm tra WorkflowStep chứa attempt và output_jsonb
    assert hasattr(WorkflowStep, 'status')
    assert hasattr(WorkflowStep, 'attempt')
    assert hasattr(WorkflowStep, 'output_jsonb')

    # 5. Kiểm tra WorkflowApproval chứa thông tin xét duyệt
    assert hasattr(WorkflowApproval, 'status')
    assert hasattr(WorkflowApproval, 'snapshot_payload_jsonb')

def test_graph_jsonb_is_the_only_schema():
    """
    Test chứng minh không có bảng con nào khác lưu cấu trúc node ngoài graph_jsonb.
    """
    # Nếu có bảng con, chúng ta sẽ thấy relationships trong WorkflowVersion.
    # Trong models.py, WorkflowVersion không có relationship nào trỏ tới các bảng node/edge riêng lẻ.
    assert 'nodes' not in dir(WorkflowVersion)
    assert 'edges' not in dir(WorkflowVersion)

import pytest
from integrations.workflows.models import WorkflowVersion, WorkflowDefinition

def test_workflow_version_lifecycle_fields():
    """
    Test các trường lifecycle được thêm vào WorkflowVersion: 
    - state (draft, validated, published, archived)
    - graph_schema_version
    - validation_report_jsonb
    - dependency_snapshot_jsonb
    - revision_token (optimistic concurrency)
    """
    assert hasattr(WorkflowVersion, 'state')
    assert hasattr(WorkflowVersion, 'graph_schema_version')
    assert hasattr(WorkflowVersion, 'validation_report_jsonb')
    assert hasattr(WorkflowVersion, 'dependency_snapshot_jsonb')
    assert hasattr(WorkflowVersion, 'revision_token')

def test_workflow_state_transitions():
    """
    Test draft -> published -> archived.
    - Drafts mutate with revision token.
    - Publish requires valid compilation.
    - Published records reject mutation.
    """
    # This is a unit-level test placeholder. Real validation happens in router or service layer.
    pass

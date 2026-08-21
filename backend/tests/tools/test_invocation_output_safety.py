import pytest
from datetime import datetime, timezone
from pydantic import BaseModel
from dataclasses import dataclass

from workforce.tools.invocation.output_safety import format_output
from core.tool_registry import ToolSpec
from workforce.tools.invocation.contracts import ToolInvocationResult

class MyPydantic(BaseModel):
    name: str

@dataclass
class MyDataclass:
    age: int

def sample_tool():
    pass

def test_format_output_primitive():
    spec = ToolSpec(namespace="test", name="tool", callable=sample_tool)
    result = format_output(spec, "hello world", "corr_1", datetime.now(timezone.utc), datetime.now(timezone.utc))
    assert isinstance(result, ToolInvocationResult)
    assert result.output == "hello world"

def test_format_output_pydantic():
    spec = ToolSpec(namespace="test", name="tool", callable=sample_tool)
    obj = MyPydantic(name="test")
    result = format_output(spec, obj, "corr_1", datetime.now(timezone.utc), datetime.now(timezone.utc))
    assert result.output == {"name": "test"}

def test_format_output_dataclass():
    spec = ToolSpec(namespace="test", name="tool", callable=sample_tool)
    obj = MyDataclass(age=42)
    result = format_output(spec, obj, "corr_1", datetime.now(timezone.utc), datetime.now(timezone.utc))
    assert result.output == {"age": 42}

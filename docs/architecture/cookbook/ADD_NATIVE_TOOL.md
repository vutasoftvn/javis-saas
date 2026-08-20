# How to add a Native Tool

A "Native Tool" is a Python-based utility that executes locally within the COSA environment. It must adhere to strict governance boundaries.

## Steps

1. **Define the Schema**: Create a Pydantic model for input and output in `backend/app/workforce/extensions/schemas/`.
2. **Implement the Logic**: Create the tool implementation in `backend/app/workforce/extensions/native_tools/`.
   - The tool class *must* inherit from `BaseNativeTool`.
   - It *must* accept an `ExecutionScope` as its first parameter.
3. **Register the Tool**: Add the tool to the `ExtensionRegistry` in `backend/app/workforce/extensions/registry.py`.
4. **Emit Events**: Use the injected `WorkflowRunner` from the `ExecutionScope` to emit `ToolRequestedEvent` and `ToolCompletedEvent`.
5. **Write Tests**: Write unit tests asserting that the tool fails gracefully when provided an invalid `ExecutionScope`.

## Example

```python
from app.workforce.extensions.base import BaseNativeTool
from app.workforce.execution.scope import ExecutionScope

class MyCustomTool(BaseNativeTool):
    async def execute(self, scope: ExecutionScope, inputs: dict) -> dict:
        # 1. Authorize
        scope.assert_capability("ext.my_custom_tool")
        
        # 2. Emit Start Event
        await scope.runner.emit_tool_requested("ext.my_custom_tool", inputs)
        
        # 3. Execute Logic
        result = {"status": "success"}
        
        # 4. Emit Completion Event
        await scope.runner.emit_tool_completed("ext.my_custom_tool", result)
        
        return result
```

import uuid
import json
from app.workforce.agents.runtime.execution_scope import ExecutionScope
from app.workforce.extensions.seams import DiscoveredCapability, ConnectorProvider

class CapabilityBridge:
    async def invoke(self, scope: ExecutionScope, capability: DiscoveredCapability, arguments: dict, kernel, provider: ConnectorProvider):
        # 1. Evaluate policy via GovernanceKernel
        # We assume kernel.evaluate_and_audit_tool_call returns an object with a .status
        decision = await kernel.evaluate_and_audit_tool_call(scope, capability, arguments)
        
        if decision.status == "denied":
            class Result:
                status = "denied"
            return Result()
            
        if decision.status == "approval_required":
            class Result:
                status = "approval_required"
            return Result()
            
        # 2. Invoke provider if allowed
        return await provider.invoke(scope, capability.capability_id, arguments)

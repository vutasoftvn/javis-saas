import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class PluginExecutionRemovedError(Exception):
    pass

class PluginHost:
    def __init__(self, workspace_id: int):
        self.workspace_id = workspace_id
        
    async def load_plugins(self, db) -> List[Dict[str, Any]]:
        """
        Load active plugins for the workspace via extension registry.
        """
        from app.workforce.extensions.registry import ExtensionRegistry
        registry = ExtensionRegistry()
        registrations = registry.get_all(db, self.workspace_id)
        
        results = []
        for reg in registrations:
            results.append({
                "extension_id": reg.extension_id,
                "version": reg.version,
                "status": reg.status,
                "capabilities": reg.manifest_jsonb.get("capabilities", []),
                "health_summary": reg.health_jsonb,
                "disabled_reason": reg.disabled_reason
            })
        return results
        
    async def execute_plugin(self, plugin_slug: str, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a plugin action.
        """
        raise PluginExecutionRemovedError("Use registered capability dispatch")

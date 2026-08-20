"""
COSA Tools Registry & Capabilities Package
"""
from tools.base import BasePresenter, BaseTool, RiskLevel, ToolResult
from tools.crm import CreateLeadTool, SearchLeadsTool
from tools.dispatcher import ToolDispatcher
from tools.filesystem import ListDirectoryTool, ReadFileTool, WriteFileTool
from tools.finance import CalculateRunwayTool, QueryPnLTool
from tools.hostinger import DeployProductionTool, DeployStagingTool
from tools.knowledge import KnowledgeSearchTool
from tools.n8n import N8nTriggerTool
from tools.registry import ToolRegistry, tool_registry
from tools.shell import SandboxedShellTool
from tools.web import WebFetchTool, WebSearchTool

# Tự động nạp toàn bộ standard tools vào registry mặc định
def register_all_standard_tools(registry: ToolRegistry = tool_registry) -> None:
    tools_to_register = [
        WebSearchTool(),
        WebFetchTool(),
        ReadFileTool(),
        WriteFileTool(),
        ListDirectoryTool(),
        SearchLeadsTool(),
        CreateLeadTool(),
        QueryPnLTool(),
        CalculateRunwayTool(),
        KnowledgeSearchTool(),
        SandboxedShellTool(),
        N8nTriggerTool(),
        DeployStagingTool(),
        DeployProductionTool(),
    ]
    for t in tools_to_register:
        registry.register(t)

# Khởi tạo mặc định
register_all_standard_tools()

__all__ = [
    "BasePresenter",
    "BaseTool",
    "CalculateRunwayTool",
    "CreateLeadTool",
    "DeployProductionTool",
    "DeployStagingTool",
    "KnowledgeSearchTool",
    "ListDirectoryTool",
    "N8nTriggerTool",
    "QueryPnLTool",
    "ReadFileTool",
    "RiskLevel",
    "SandboxedShellTool",
    "SearchLeadsTool",
    "ToolDispatcher",
    "ToolRegistry",
    "ToolResult",
    "WebFetchTool",
    "WebSearchTool",
    "WriteFileTool",
    "register_all_standard_tools",
    "tool_registry",
]

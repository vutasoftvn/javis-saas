import re
import os

with open('backend/app/db/models.py', 'r') as f:
    content = f.read()

imports = """from datetime import datetime
import uuid
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.db.base_class import Base

"""

domains = {
    'iam': ['User', 'Workspace', 'WorkspaceMember'],
    'vault': ['Brain', 'VaultDocument', 'VaultRevision', 'Attachment', 'DocumentChunk', 'ChunkingJob'],
    'chat': ['ChatSession', 'ChatMessage', 'AIRun'],
    'tasks': ['Task', 'TaskDependency', 'TaskSchedule', 'Agent'],
    'workflows': ['TaskWorkflowBinding', 'WorkflowRun', 'WorkflowDefinition', 'WorkflowVersion', 'WorkflowStep', 'WorkflowApproval'],
    'strategy': [
        'StrategyCanvas', 'StrategyRevision', 'StrategyFoundation', 'CoreValue', 'EvidenceItem', 'ContextPack',
        'ContextPackSource', 'StrategyAnalysis', 'PestelItem', 'SwotItem', 'TowsOption', 'StrategicDecision',
        'Metric', 'MetricCheckin', 'BscScorecard', 'StrategicObjective', 'StrategicObjectiveLink',
        'OkrCycle', 'OkrObjective', 'KeyResult', 'OkrLink', 'Project', 'Initiative', 'InitiativeKeyResultLink',
        'TwelveWeekCycle', 'WeeklyPlan', 'WeeklyCommitment'
    ],
    'integrations': ['MCPConnection', 'WorkspaceSecret', 'Chatbot', 'ChatbotConversation', 'Plugin', 'WorkspacePlugin', 'Outbox'],
    'platform': ['WorkspaceDomain', 'AuditLog']
}

class_pattern = re.compile(r'class\s+([A-Za-z0-9_]+)\(Base\):.*?(?=\nclass\s+[A-Za-z0-9_]+\(Base\):|\Z)', re.DOTALL)

classes = {}
for match in class_pattern.finditer(content):
    cls_name = match.group(1)
    classes[cls_name] = match.group(0).strip() + "\n\n"

for domain, cls_names in domains.items():
    os.makedirs(f'backend/app/modules/{domain}', exist_ok=True)
    domain_content = imports
    for cls in cls_names:
        if cls in classes:
            domain_content += classes[cls]
    
    with open(f'backend/app/modules/{domain}/models.py', 'w') as f:
        f.write(domain_content)

print("Split complete.")

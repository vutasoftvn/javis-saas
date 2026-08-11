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
    'vault': ['Brain', 'VaultDocument', 'VaultRevision', 'Attachment'],
    'chat': ['ChatSession', 'ChatMessage'],
    'tasks': ['Task', 'TaskDependency', 'TaskSchedule', 'Agent'],
    'workflows': ['TaskWorkflowBinding', 'WorkflowRun'],
    'strategy': ['StrategyCanvas', 'StrategyRevision', 'StrategyFoundation', 'Goal', 'StrategyTactic', 'WeeklyCommitment', 'Metric', 'Initiative'],
    'integrations': ['MCPConnection', 'WorkspaceSecret', 'Chatbot', 'ChatbotConversation'],
    'platform': ['WorkspaceDomain', 'AuditLog']
}

class_pattern = re.compile(r'class\s+([A-Za-z0-9_]+)\(Base\):.*?(?=\nclass\s+[A-Za-z0-9_]+\(Base\):|\Z)', re.DOTALL)

classes = {}
for match in class_pattern.finditer(content):
    cls_name = match.group(1)
    # The regex might capture extra whitespace or comments at the end, but that's fine
    classes[cls_name] = match.group(0).strip() + "\n"

# Extra classes that don't inherit from Base directly or are aliases
# Actually AIRun was not in my domain list. Let's find AIRun
if 'AIRun' in classes:
    domains['chat'].append('AIRun')
if 'Agent' in classes and 'Agent' not in domains['tasks']:
    domains['tasks'].append('Agent')
    
for domain, cls_names in domains.items():
    domain_content = imports
    for cls in cls_names:
        if cls in classes:
            domain_content += classes[cls] + "\n"
    
    with open(f'backend/app/modules/{domain}/models.py', 'w') as f:
        f.write(domain_content)

print("Split complete")

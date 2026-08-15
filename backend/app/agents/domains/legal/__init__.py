from app.agents.domains.legal.data import LegalDataCapability
from app.agents.domains.legal.reasoning import LegalReasoningCapability, LEGAL_DISCLAIMER
from app.agents.domains.legal.research import LegalResearchCapability
from app.agents.domains.legal.communication import LegalCommunicationCapability
from app.agents.domains.legal.action import LegalActionCapability
from app.agents.domains.legal.evaluation import LegalEvaluationCapability

__all__ = [
    "LegalDataCapability",
    "LegalReasoningCapability",
    "LegalResearchCapability",
    "LegalCommunicationCapability",
    "LegalActionCapability",
    "LegalEvaluationCapability",
    "LEGAL_DISCLAIMER",
]

"""Technology Radar Service for COSA Operating System (Spec §104, §P5)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.modules.tech_radar.models import TechnologyRadarItem

# Standard seed technologies from Spec §104
DEFAULT_RADAR_ITEMS = [
    {
        "name": "PostgreSQL LISTEN/NOTIFY",
        "category": "Runtime",
        "status": "ADOPT",
        "maturity": "production",
        "potential": "high",
        "cosa_use": "direct",
        "integration": "yes",
        "description": "Cross-process event broker and realtime bus for multi-worker backend.",
    },
    {
        "name": "DSPy",
        "category": "Evaluation",
        "status": "ADOPT",
        "maturity": "production",
        "potential": "high",
        "cosa_use": "direct",
        "integration": "yes",
        "description": "Declarative self-optimizing prompt signatures and offline evaluation harness.",
    },
    {
        "name": "LiteLLM",
        "category": "Runtime",
        "status": "ADOPT",
        "maturity": "production",
        "potential": "high",
        "cosa_use": "direct",
        "integration": "yes",
        "description": "Unified LLM provider proxy with cost tracking and fallback routing.",
    },
    {
        "name": "Docker Sandbox",
        "category": "Security",
        "status": "ADOPT",
        "maturity": "production",
        "potential": "high",
        "cosa_use": "direct",
        "integration": "yes",
        "description": "Isolated container execution environment with zero-LAN and strict resource caps.",
    },
    {
        "name": "MinIO S3",
        "category": "Runtime",
        "status": "ADOPT",
        "maturity": "production",
        "potential": "high",
        "cosa_use": "direct",
        "integration": "yes",
        "description": "Object store for immutable outcome artifacts and evaluation traces.",
    },
    {
        "name": "AgentSkeptic",
        "category": "Governance",
        "status": "WATCH",
        "maturity": "experimental",
        "potential": "high",
        "cosa_use": "pattern",
        "integration": "no",
        "description": "Adversarial verification pattern for agent hallucination and outcome auditing.",
    },
    {
        "name": "n8n Workflow Engine",
        "category": "Orchestration",
        "status": "TRIAL",
        "maturity": "production",
        "potential": "high",
        "cosa_use": "direct",
        "integration": "partial",
        "description": "Automation worker and multi-app integration adapter under Governance Kernel.",
    },
    {
        "name": "DeepSeek Harness",
        "category": "Evaluation",
        "status": "TRIAL",
        "maturity": "beta",
        "potential": "high",
        "cosa_use": "pattern",
        "integration": "partial",
        "description": "Fast reasoning and code verification benchmarking engine.",
    },
    {
        "name": "Playwright / Stagehand",
        "category": "Browser",
        "status": "TRIAL",
        "maturity": "beta",
        "potential": "high",
        "cosa_use": "direct",
        "integration": "partial",
        "description": "Headless browser driver for external data gathering and DOM testing.",
    },
    {
        "name": "Mem0 / Zep",
        "category": "Memory",
        "status": "ASSESS",
        "maturity": "beta",
        "potential": "medium",
        "cosa_use": "evaluated",
        "integration": "no",
        "description": "Episodic memory extraction compared against 5-layer COSA memory engine.",
    },
]


class TechRadarService:
    """Manages Technology Radar registry, categorization, and ring status."""

    @classmethod
    def list_items(
        cls,
        db: Session,
        workspace_id: int,
        category: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[TechnologyRadarItem]:
        query = db.query(TechnologyRadarItem).filter(TechnologyRadarItem.workspace_id == workspace_id)
        if category:
            query = query.filter(TechnologyRadarItem.category.ilike(category))
        if status:
            query = query.filter(TechnologyRadarItem.status == status.upper())
        return query.order_by(TechnologyRadarItem.category.asc(), TechnologyRadarItem.name.asc()).all()

    @classmethod
    def get_item(cls, db: Session, item_id: int) -> Optional[TechnologyRadarItem]:
        return db.query(TechnologyRadarItem).filter(TechnologyRadarItem.id == item_id).first()

    @classmethod
    def create_item(
        cls,
        db: Session,
        workspace_id: int,
        name: str,
        category: str,
        status: str = "WATCH",
        maturity: str = "experimental",
        potential: str = "high",
        cosa_use: str = "pattern",
        integration: str = "no",
        description: Optional[str] = None,
        last_reviewed: Optional[str] = None,
    ) -> TechnologyRadarItem:
        item = TechnologyRadarItem(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            name=name,
            category=category,
            status=status.upper(),
            maturity=maturity,
            potential=potential,
            cosa_use=cosa_use,
            integration=integration,
            description=description,
            last_reviewed=last_reviewed or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @classmethod
    def update_item(
        cls,
        db: Session,
        item_id: int,
        status: Optional[str] = None,
        maturity: Optional[str] = None,
        potential: Optional[str] = None,
        cosa_use: Optional[str] = None,
        integration: Optional[str] = None,
        description: Optional[str] = None,
        last_reviewed: Optional[str] = None,
    ) -> TechnologyRadarItem:
        item = cls.get_item(db, item_id)
        if not item:
            raise KeyError(f"Radar item {item_id} not found")

        if status is not None:
            item.status = status.upper()
        if maturity is not None:
            item.maturity = maturity
        if potential is not None:
            item.potential = potential
        if cosa_use is not None:
            item.cosa_use = cosa_use
        if integration is not None:
            item.integration = integration
        if description is not None:
            item.description = description
        if last_reviewed is not None:
            item.last_reviewed = last_reviewed

        item.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(item)
        return item

    @classmethod
    def seed_defaults(cls, db: Session, workspace_id: int) -> List[TechnologyRadarItem]:
        """Seed default technologies from Spec §104 if not already present."""
        created = []
        for def_item in DEFAULT_RADAR_ITEMS:
            existing = (
                db.query(TechnologyRadarItem)
                .filter(
                    TechnologyRadarItem.workspace_id == workspace_id,
                    TechnologyRadarItem.name == def_item["name"],
                )
                .first()
            )
            if not existing:
                item = cls.create_item(
                    db=db,
                    workspace_id=workspace_id,
                    name=def_item["name"],
                    category=def_item["category"],
                    status=def_item["status"],
                    maturity=def_item["maturity"],
                    potential=def_item["potential"],
                    cosa_use=def_item["cosa_use"],
                    integration=def_item["integration"],
                    description=def_item["description"],
                )
                created.append(item)
        return created

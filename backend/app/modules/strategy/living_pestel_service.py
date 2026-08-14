import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.snowflake import generate_snowflake_id
from app.modules.strategy.models import (

    PestelSignal,
    ModelRunAudit,
    ProjectPestelImpact,
    NextActionCandidate,
    PestelItem,
    ModelProfileOverride,
)
from app.modules.strategy.next_best_action_service import NextBestActionService
from app.modules.chat.model_profiles import STRATEGY_PROFILES, list_profile_mappings

logger = logging.getLogger(__name__)


class LivingPestelService:
    """Living PESTEL Signal Ingestion, Material-Change Flow & AI Model Run Audit (Spec §48 & Sprint 10).

    Tự động đối chiếu biến động vĩ mô với danh mục dự án active và sinh CEO Exception Task khi có tín hiệu trọng yếu.
    """

    def __init__(self, db: Session, workspace_id: int, user_id: int):
        self.db = db
        self.workspace_id = workspace_id
        self.user_id = user_id

    def ingest_signal(
        self,
        signal_title: str,
        pestel_category: str,
        magnitude: str,
        signal_summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Tiếp nhận tín hiệu Living PESTEL và kiểm tra Material Change (Spec §48)."""
        is_material = magnitude.upper() in ["HIGH", "CRITICAL"]

        signal = PestelSignal(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            signal_title=signal_title,
            signal_summary=signal_summary,
            pestel_category=pestel_category.upper(),
            magnitude=magnitude.upper(),
            is_material_change=is_material,
            created_at=datetime.utcnow(),
        )
        self.db.add(signal)

        ceo_exception_created = False
        if is_material:
            # Tìm các dự án có tác động PESTEL tiêu cực cùng danh mục (factor) với tín hiệu
            matching_impacts = (
                self.db.query(ProjectPestelImpact)
                .join(PestelItem, ProjectPestelImpact.pestel_item_id == PestelItem.id)
                .filter(
                    ProjectPestelImpact.workspace_id == self.workspace_id,
                    ProjectPestelImpact.impact_type == "NEGATIVE",
                    PestelItem.factor == pestel_category.upper(),
                )
                .all()
            )

            # Tự động tạo CEO Exception Task (NextActionCandidate)
            for imp in matching_impacts:
                cand = NextActionCandidate(
                    id=generate_snowflake_id(),
                    workspace_id=self.workspace_id,
                    project_id=imp.project_id,
                    title=f"[CEO EXCEPTION §48] {signal_title}",
                    description=f"Tín hiệu PESTEL vĩ mô biến động trọng yếu ({magnitude}): {signal_summary or signal_title}",
                    category="PESTEL_MITIGATION",
                    urgency_score=0.9,
                    impact_score=0.95,
                    effort_score=0.4,
                    r0_score=NextBestActionService.compute_r0_score(0.9, 0.95, 0.4),
                    status="proposed",
                    created_at=datetime.utcnow(),
                )
                self.db.add(cand)
                ceo_exception_created = True

        self.db.commit()
        self.db.refresh(signal)

        return {
            "signal": self._serialize_signal(signal),
            "is_material_change": is_material,
            "ceo_exception_created": ceo_exception_created,
        }

    def get_pestel_signals(self) -> List[Dict[str, Any]]:
        signals = (
            self.db.query(PestelSignal)
            .filter(PestelSignal.workspace_id == self.workspace_id)
            .order_by(PestelSignal.created_at.desc())
            .all()
        )
        return [self._serialize_signal(s) for s in signals]

    def record_model_run(
        self,
        model_profile: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
        status_val: str = "success",
    ) -> Dict[str, Any]:
        audit = ModelRunAudit(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            model_profile=model_profile,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            status=status_val,
            created_at=datetime.utcnow(),
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(audit)
        return self._serialize_audit(audit)

    def get_model_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        audits = (
            self.db.query(ModelRunAudit)
            .filter(ModelRunAudit.workspace_id == self.workspace_id)
            .order_by(ModelRunAudit.created_at.desc())
            .limit(limit)
            .all()
        )
        return [self._serialize_audit(a) for a in audits]

    def list_model_profiles(self) -> List[Dict[str, Any]]:
        """Danh sách Model Profile logic (Terra/DeepSeek/Claude routing, Spec §56) kèm override theo workspace."""
        overrides = {
            o.profile_key: o
            for o in self.db.query(ModelProfileOverride)
            .filter(ModelProfileOverride.workspace_id == self.workspace_id)
            .all()
        }
        mappings = list_profile_mappings()
        result = []
        for key in STRATEGY_PROFILES:
            base = mappings[key]
            override = overrides.get(key)
            result.append({
                "profile": key,
                "provider": base["provider"],
                "model": base["model"],
                "configured": base["configured"],
                "display_name": override.display_name if override else key,
                "temperature": override.temperature if override else None,
                "is_active": override.is_active if override else True,
            })
        return result

    def update_model_profile(
        self,
        profile_key: str,
        display_name: Optional[str] = None,
        temperature: Optional[float] = None,
        is_active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Cập nhật override admin (display_name/temperature/is_active) cho một Model Profile."""
        normalized_key = profile_key.upper().strip()
        if normalized_key not in STRATEGY_PROFILES:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown model profile '{profile_key}'")

        override = (
            self.db.query(ModelProfileOverride)
            .filter(
                ModelProfileOverride.workspace_id == self.workspace_id,
                ModelProfileOverride.profile_key == normalized_key,
            )
            .first()
        )
        if override is None:
            override = ModelProfileOverride(
                id=generate_snowflake_id(),
                workspace_id=self.workspace_id,
                profile_key=normalized_key,
                is_active=True,
                created_at=datetime.utcnow(),
            )
            self.db.add(override)

        if display_name is not None:
            override.display_name = display_name
        if temperature is not None:
            override.temperature = temperature
        if is_active is not None:
            override.is_active = is_active
        override.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(override)
        return {
            "profile": normalized_key,
            "display_name": override.display_name,
            "temperature": override.temperature,
            "is_active": override.is_active,
        }

    def _serialize_signal(self, s: PestelSignal) -> Dict[str, Any]:
        return {
            "id": str(s.id),
            "signal_title": s.signal_title,
            "signal_summary": s.signal_summary,
            "pestel_category": s.pestel_category,
            "magnitude": s.magnitude,
            "is_material_change": s.is_material_change,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }

    def _serialize_audit(self, a: ModelRunAudit) -> Dict[str, Any]:
        return {
            "id": str(a.id),
            "model_profile": a.model_profile,
            "prompt_tokens": a.prompt_tokens,
            "completion_tokens": a.completion_tokens,
            "latency_ms": a.latency_ms,
            "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }

"""Skill Lifecycle Service for COSA Operating System (Spec §61, §62, §P5).

Manages end-to-end skill lifecycle:
Trajectory Analysis -> PII/Secret Scan -> Skill Candidate -> Evaluation -> Founder/Admin Approval -> Active -> Deprecated.
Enforces Invariant: NO AGENT SELF-PROMOTION OF PROMPTS/SKILLS.
"""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.workforce.skills.models import SkillRegistryItem, SkillTrajectoryCandidate


# Secret / PII detection patterns
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"(?:api_key|apikey|secret_key|access_token|password|bearer\s+[a-zA-Z0-9_\-\.]{20,})", re.IGNORECASE),
    re.compile(r"sk-[a-zA-Z0-9]{32,}", re.IGNORECASE),
]

PII_PATTERNS = [
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),  # Email
    re.compile(r"\b(?:\+?84|0)(?:3|5|7|8|9)[0-9]{8}\b"),  # VN Phone
    re.compile(r"\b[0-9]{9,12}\b"),  # ID Card / Passport digits
]


class SkillSafetyScanner:
    """Scans proposed SOP and skill manifests for leaked secrets or PII."""

    @classmethod
    def scan_content(cls, content: str) -> Tuple[bool, bool, List[str]]:
        """Returns (pii_passed, secret_passed, issues)."""
        issues = []
        secret_passed = True
        pii_passed = True

        for pat in SECRET_PATTERNS:
            if pat.search(content):
                secret_passed = False
                issues.append("Secret / credential pattern detected in skill content.")
                break

        for pat in PII_PATTERNS:
            if pat.search(content):
                pii_passed = False
                issues.append("Unmasked PII (email/phone/citizen-id) detected in skill content.")
                break

        return pii_passed, secret_passed, issues


class SkillLifecycleService:
    """Orchestrates candidate extraction, evaluation, safety gating, and governed promotion."""

    @classmethod
    def create_candidate_from_trajectory(
        cls,
        db: Session,
        workspace_id: int,
        domain: str,
        proposed_name: str,
        extracted_sop: str,
        mission_id: Optional[str] = None,
        run_id: Optional[int] = None,
        tools_used: Optional[List[str]] = None,
    ) -> SkillTrajectoryCandidate:
        """Extract a learning candidate from trajectory and perform initial safety scan."""
        pii_passed, secret_passed, issues = SkillSafetyScanner.scan_content(extracted_sop)

        candidate = SkillTrajectoryCandidate(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            mission_id=mission_id,
            run_id=run_id,
            domain=domain,
            proposed_name=proposed_name,
            extracted_sop=extracted_sop,
            tools_used=tools_used or [],
            pii_scan_passed=pii_passed,
            secret_scan_passed=secret_passed,
            safety_notes="; ".join(issues) if issues else "Safety check passed",
            status="scanned" if (pii_passed and secret_passed) else "rejected",
            created_at=datetime.now(timezone.utc),
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        return candidate

    @classmethod
    def register_skill_candidate(
        cls,
        db: Session,
        workspace_id: int,
        name: str,
        domain: str,
        instructions: str,
        description: str = "",
        scope: Optional[List[str]] = None,
        tool_permissions: Optional[List[str]] = None,
        required_context: Optional[List[str]] = None,
        created_by_agent: Optional[str] = None,
    ) -> SkillRegistryItem:
        """Register a new skill in 'candidate' status."""
        pii_passed, secret_passed, issues = SkillSafetyScanner.scan_content(instructions)
        if not (pii_passed and secret_passed):
            raise ValueError(f"Skill candidate rejected by Safety Scanner: {'; '.join(issues)}")

        item = SkillRegistryItem(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            name=name,
            domain=domain,
            version="1.0.0",
            status="candidate",
            description=description,
            instructions=instructions,
            scope=scope or [],
            tool_permissions=tool_permissions or [],
            required_context=required_context or [],
            created_by_agent=created_by_agent,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @classmethod
    def seed_platform_skill(
        cls,
        db: Session,
        workspace_id: int,
        name: str,
        domain: str,
        instructions: str,
        description: str = "",
        scope: Optional[List[str]] = None,
        tool_permissions: Optional[List[str]] = None,
        required_context: Optional[List[str]] = None,
    ) -> SkillRegistryItem:
        """Seed a platform-shipped built-in skill (from SKILL.md on disk) directly to
        'active', `is_system=True`, no `approved_by_user_id`.

        Distinct from `promote_skill()` on purpose: this is not a human clicking
        approve, it's the platform's own bundled content, so recording a fake
        approver (e.g. whichever user happened to be the first to open the skills
        list) would misattribute an approval nobody actually made. The "NO AGENT
        SELF-PROMOTION" invariant in `promote_skill()` is about untrusted,
        agent-generated content and still applies unchanged to everything else -
        candidates, trajectory-derived skills, markdown uploads all still require an
        explicit human `approved_by_user_id`.
        """
        pii_passed, secret_passed, issues = SkillSafetyScanner.scan_content(instructions)
        if not (pii_passed and secret_passed):
            raise ValueError(f"Platform skill rejected by Safety Scanner: {'; '.join(issues)}")

        now = datetime.now(timezone.utc)
        item = SkillRegistryItem(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            name=name,
            domain=domain,
            version="1.0.0",
            status="active",
            is_system=True,
            description=description,
            instructions=instructions,
            scope=scope or [],
            tool_permissions=tool_permissions or [],
            required_context=required_context or [],
            created_by_agent=None,
            created_at=now,
            updated_at=now,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @classmethod
    def evaluate_skill(
        cls,
        db: Session,
        skill_id: int,
        eval_score: float,
        eval_details: Optional[Dict[str, Any]] = None,
    ) -> SkillRegistryItem:
        """Evaluate a skill candidate and move to pending_approval if score is sufficient."""
        item = db.query(SkillRegistryItem).filter(SkillRegistryItem.id == skill_id).first()
        if not item:
            raise KeyError(f"Skill {skill_id} not found")

        item.success_rate = max(0.0, min(1.0, eval_score))
        if eval_details:
            manifest = dict(item.manifest_jsonb or {})
            manifest["eval_details"] = eval_details
            item.manifest_jsonb = manifest

        # If evaluation passes threshold (>= 0.70), move to pending_approval
        if eval_score >= 0.70:
            item.status = "pending_approval"
        else:
            item.status = "evaluation"

        item.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(item)
        return item

    @classmethod
    def promote_skill(
        cls,
        db: Session,
        skill_id: int,
        approved_by_user_id: Optional[int],
        target_status: str = "active",
    ) -> SkillRegistryItem:
        """Promote a skill to 'active' (or 'experimental') production status.

        INVARIANT ENFORCEMENT:
        NO AGENT SELF-PROMOTION OF PROMPTS/SKILLS.
        Promotion MUST have an explicit human admin/founder user ID.
        """
        if target_status not in ("active", "experimental"):
            raise ValueError(f"Invalid promotion target_status: {target_status!r} (expected 'active' or 'experimental')")

        if approved_by_user_id is None:
            raise PermissionError(
                "Invariant Violation: NO AGENT SELF-PROMOTION OF PROMPTS/SKILLS. "
                "Skill promotion requires explicit human admin/founder approval."
            )

        item = db.query(SkillRegistryItem).filter(SkillRegistryItem.id == skill_id).first()
        if not item:
            raise KeyError(f"Skill {skill_id} not found")

        now = datetime.now(timezone.utc)
        item.status = target_status
        item.approved_by_user_id = approved_by_user_id
        item.approved_at = now
        item.updated_at = now

        db.commit()
        db.refresh(item)
        return item

    @classmethod
    def deprecate_skill(
        cls,
        db: Session,
        skill_id: int,
        user_id: int,
        reason: Optional[str] = None,
    ) -> SkillRegistryItem:
        """Deprecate an existing skill (soft retirement - discouraged, may still run)."""
        item = db.query(SkillRegistryItem).filter(SkillRegistryItem.id == skill_id).first()
        if not item:
            raise KeyError(f"Skill {skill_id} not found")

        item.status = "deprecated"
        if reason:
            item.rejection_reason = reason
        item.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(item)
        return item

    @classmethod
    def archive_skill(
        cls,
        db: Session,
        skill_id: int,
        user_id: int,
        reason: Optional[str] = None,
    ) -> SkillRegistryItem:
        """Archive a skill - terminal retirement, excluded from normal listing/use,
        kept for history. Usually follows `deprecated`, but reachable from any status."""
        item = db.query(SkillRegistryItem).filter(SkillRegistryItem.id == skill_id).first()
        if not item:
            raise KeyError(f"Skill {skill_id} not found")

        item.status = "archived"
        if reason:
            item.rejection_reason = reason
        item.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(item)
        return item

    @classmethod
    def block_skill(
        cls,
        db: Session,
        skill_id: int,
        user_id: int,
        reason: str,
    ) -> SkillRegistryItem:
        """Forcibly disable a skill regardless of its prior status - an emergency
        kill-switch (e.g. a security review fails on an already-active skill).
        `reason` is required, unlike deprecate/archive, since this overrides
        whatever state the skill was in without going through the normal flow."""
        if not reason or not reason.strip():
            raise ValueError("block_skill requires a non-empty reason")

        item = db.query(SkillRegistryItem).filter(SkillRegistryItem.id == skill_id).first()
        if not item:
            raise KeyError(f"Skill {skill_id} not found")

        item.status = "blocked"
        item.rejection_reason = reason
        item.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(item)
        return item

    @classmethod
    def record_usage(
        cls,
        db: Session,
        skill_id: int,
        success: bool,
        rating: Optional[int] = None,
    ) -> SkillRegistryItem:
        """Record usage and update success_rate and feedback metrics."""
        item = db.query(SkillRegistryItem).filter(SkillRegistryItem.id == skill_id).first()
        if not item:
            raise KeyError(f"Skill {skill_id} not found")

        item.usage_count = (item.usage_count or 0) + 1
        item.positive_feedback = item.positive_feedback or 0
        item.negative_feedback = item.negative_feedback or 0
        current_success_rate = item.success_rate if item.success_rate is not None else 1.0

        if rating is not None:
            if rating >= 4:
                item.positive_feedback += 1
            elif rating <= 2:
                item.negative_feedback += 1

        # Recompute moving average success rate
        total_runs = item.usage_count
        prev_successes = current_success_rate * (total_runs - 1)
        new_successes = prev_successes + (1.0 if success else 0.0)
        item.success_rate = round(new_successes / total_runs, 4)
        item.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(item)
        return item

    @classmethod
    def update_skill(
        cls,
        db: Session,
        skill_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        tool_permissions: Optional[List[str]] = None,
        domain: Optional[str] = None,
        version: Optional[str] = None,
    ) -> SkillRegistryItem:
        """Update existing skill attributes with safety gating on instructions."""
        item = db.query(SkillRegistryItem).filter(SkillRegistryItem.id == skill_id).first()
        if not item:
            raise KeyError(f"Skill {skill_id} not found")

        if item.is_system:
            raise PermissionError(
                f"Skill {skill_id} is platform-shipped (is_system=True) and immutable. "
                "Register a new workspace-authored skill instead of editing this one in place."
            )

        if name is not None:
            item.name = name
        if description is not None:
            item.description = description
        if instructions is not None:
            pii_passed, secret_passed, issues = SkillSafetyScanner.scan_content(instructions)
            if not (pii_passed and secret_passed):
                raise ValueError(f"Skill instructions rejected by Safety Scanner: {'; '.join(issues)}")
            item.instructions = instructions
        if tool_permissions is not None:
            item.tool_permissions = tool_permissions
        if domain is not None:
            item.domain = domain
        if version is not None:
            item.version = version

        item.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(item)
        return item

    @classmethod
    def list_skills(
        cls,
        db: Session,
        workspace_id: int,
        domain: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[SkillRegistryItem]:
        """List skills for workspace with optional filtering."""
        query = db.query(SkillRegistryItem).filter(SkillRegistryItem.workspace_id == workspace_id)
        if domain:
            query = query.filter(SkillRegistryItem.domain == domain)
        if status:
            query = query.filter(SkillRegistryItem.status == status)
        return query.order_by(SkillRegistryItem.created_at.desc()).all()

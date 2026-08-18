from typing import Optional, Tuple


class QualificationService:
    @staticmethod
    def qualify(
        fit: Optional[str] = None,
        need: Optional[str] = None,
        urgency: Optional[str] = None,
        authority: Optional[str] = None,
        ability_to_pay: Optional[str] = None,
    ) -> Tuple[str, Optional[str]]:
        """Evaluates FIT, NEED, URGENCY, AUTHORITY, ABILITY_TO_PAY.

        Returns (qualification_status, disqualification_reason).
        Status is one of: QUALIFIED, DISQUALIFIED, NEEDS_DISCOVERY.
        """
        # Hard fail check
        if ability_to_pay and ability_to_pay.upper() in {"NO", "FALSE", "NONE", "ZERO"}:
            return "DISQUALIFIED", "Ability to pay confirmed as NO / insufficient budget"

        if fit and fit.upper() in {"NO", "FALSE", "BAD_FIT"}:
            return "DISQUALIFIED", "Fit score / segment confirmed as BAD_FIT"

        # Check if all 5 dimensions are present and passing
        dims = {"fit": fit, "need": need, "urgency": urgency, "authority": authority, "ability_to_pay": ability_to_pay}
        missing = [k for k, v in dims.items() if not v]

        if missing:
            return "NEEDS_DISCOVERY", f"Missing discovery dimensions: {', '.join(missing)}"

        return "QUALIFIED", None

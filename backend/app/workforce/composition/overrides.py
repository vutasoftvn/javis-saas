from app.workforce.composition.contracts import ResolvedProfile, SessionOverride
from copy import deepcopy

def apply_session_override(profile: ResolvedProfile, override: SessionOverride) -> ResolvedProfile:
    """
    Áp dụng các ghi đè session. Đảm bảo chỉ cắt giảm (subtractive), không mở rộng quyền.
    """
    result = deepcopy(profile)
    
    # 1. Loại bỏ tool
    if override.remove_tool_ids:
        result.visible_tool_ids = [
            t for t in result.visible_tool_ids 
            if t not in override.remove_tool_ids
        ]
        
    # 2. Loại bỏ skill
    if override.disable_skill_ids:
        for s in override.disable_skill_ids:
            result.active_skill_versions.pop(s, None)
            
    # 3. Thu hẹp scope (restrict_scope phải là tập con của scope_ceiling)
    if override.restrict_scope and "grants" in override.restrict_scope:
        base_grants = set(result.scope_ceiling.get("grants", []))
        requested_grants = set(override.restrict_scope["grants"])
        
        # Chỉ giữ lại những grant nào có trong base_grants (subtractive)
        allowed_grants = base_grants.intersection(requested_grants)
        result.scope_ceiling["grants"] = list(allowed_grants)
        
    return result

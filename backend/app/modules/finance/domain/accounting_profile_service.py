SUPPORTED_MODE = "TT58_MODE_1"


def activate_profile(profile, confirmed_by: int | None):
    if profile.mode != SUPPORTED_MODE:
        raise ValueError("Only TT58 Mode 1 is production-ready")
    if not confirmed_by:
        raise ValueError("Accounting profile activation requires human confirmation")
    if profile.status != "PENDING_CONFIRMATION":
        raise ValueError("Profile must be pending confirmation")
    profile.confirmed_by = confirmed_by
    profile.status = "ACTIVE"
    return profile

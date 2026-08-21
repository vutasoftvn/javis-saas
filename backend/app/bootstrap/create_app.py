"""COSA FastAPI application factory (Quyết định 3 - self-host + central
control-plane role split).

`create_app(role)` build 1 FastAPI app mà việc IMPORT router phụ thuộc điều
kiện vào `role`, không chỉ việc `include_router()` - import
`app.founder_os.router` (v.v.) có chi phí thật (kéo theo toàn bộ dependency
tầng service/tool của domain đó) ngay cả khi router object không được mount,
nên 1 role không cần domain nào thì tuyệt đối không được import domain đó.
"""
import os

FULL_ROLE = "full"
CENTRAL_CONTROL_PLANE_ROLE = "central_control_plane"
_VALID_ROLES = (FULL_ROLE, CENTRAL_CONTROL_PLANE_ROLE)


def resolve_app_role(environment: "os._Environ[str] | dict | None" = None) -> str:
    """Resolve APP_ROLE từ environment. Mặc định "full" khi unset/rỗng - giữ
    đúng hành vi hiện tại (trước Quyết định 3), không được tự ý thu hẹp phạm
    vi. Giá trị không hợp lệ (vd gõ nhầm "central") phải raise ngay thay vì
    âm thầm fallback về "full" - fallback êm sẽ khiến 1 deployment central
    gõ sai APP_ROLE lại mount lại nguyên con monolith mà Quyết định 3 đang
    vá, chỉ khác là không còn ai biết để verify nữa.
    """
    environment = environment if environment is not None else os.environ
    raw = environment.get("APP_ROLE")
    if raw is None or raw.strip() == "":
        return FULL_ROLE
    role = raw.strip().lower()
    if role not in _VALID_ROLES:
        raise ValueError(
            f"Unknown APP_ROLE={raw!r}; must be unset (defaults to {FULL_ROLE!r}) "
            f"or one of {_VALID_ROLES!r}."
        )
    return role

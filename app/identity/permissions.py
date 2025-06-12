from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Callable, Tuple

from app.db import SessionLocal
from .models import User, UserRole, RolePermission, Permission, PermissionAuditLog
from .auth import decode_jwt, http_bearer


def permission_required(resource: str, action: str) -> Callable:
    """Decorator to mark endpoints with required permission."""

    def decorator(func: Callable) -> Callable:
        setattr(func, "required_permission", (resource, action))
        return func

    return decorator


class PermissionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        """Collect routes decorated with ``permission_required`` at startup."""
        super().__init__(app)
        self.permission_routes: list[tuple[object, tuple[str, str]]] = []
        base_app = app
        while not hasattr(base_app, "routes") and hasattr(base_app, "app"):
            base_app = base_app.app
        routes = getattr(base_app, "routes", [])
        for route in routes:
            if hasattr(route, "endpoint") and hasattr(route.endpoint, "required_permission"):
                self.permission_routes.append((route, getattr(route.endpoint, "required_permission")))

    async def dispatch(self, request: Request, call_next):
        from starlette.routing import Match
        perm: Tuple[str, str] | None = None
        for route, required in self.permission_routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                perm = required
                break
        if not perm:
            return await call_next(request)

        # Authenticate user via bearer token
        credentials = await http_bearer(request)
        user_id = decode_jwt(credentials.credentials)
        if not user_id:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})

        db: Session = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return JSONResponse(status_code=401, content={"detail": "User not found"})

            resource, action = perm
            role_ids = [ur.role_id for ur in db.query(UserRole)
                        .filter(UserRole.user_id == user.id, UserRole.is_active == True)
                        .all()]
            allowed = False
            if role_ids:
                allowed = (
                    db.query(RolePermission)
                    .join(Permission, RolePermission.permission_id == Permission.id)
                    .filter(
                        RolePermission.role_id.in_(role_ids),
                        Permission.resource == resource,
                        Permission.action == action,
                    )
                    .count()
                    > 0
                )
            log = PermissionAuditLog(
                user_id=user.id,
                action=action,
                resource=resource,
                permission_checked=f"{resource}:{action}",
                access_granted=allowed,
                role_context={"roles": role_ids},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            )
            db.add(log)
            db.commit()
            if not allowed:
                return JSONResponse(status_code=403, content={"detail": "Insufficient permissions"})
        finally:
            db.close()

        return await call_next(request)

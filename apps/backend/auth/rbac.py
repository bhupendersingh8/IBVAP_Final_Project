"""
RBAC — Role-Based Access Control
=================================
Defines roles, permissions, and a permission-check helper.
Roles: VIEWER, OPERATOR, SUPERVISOR, ADMIN, SYSTEM.
"""
from enum import Enum
from typing import Set, Dict


class Role(str, Enum):
    VIEWER = "VIEWER"                 # Read-only dashboard access
    OPERATOR = "OPERATOR"             # Acknowledge/manage incidents, submit feedback
    SUPERVISOR = "SUPERVISOR"         # Manage incidents, audit evidence, view all telemetry
    ADMIN = "ADMIN"                   # Full management (cameras, zones, configuration, users)
    SYSTEM = "SYSTEM"                 # Internal service-to-service calls


class Permission(str, Enum):
    VIEW_INCIDENTS = "VIEW_INCIDENTS"
    ACKNOWLEDGE_INCIDENTS = "ACKNOWLEDGE_INCIDENTS"
    MANAGE_INCIDENTS = "MANAGE_INCIDENTS"
    VIEW_CAMERAS = "VIEW_CAMERAS"
    MANAGE_CAMERAS = "MANAGE_CAMERAS"
    VIEW_ZONES = "VIEW_ZONES"
    MANAGE_ZONES = "MANAGE_ZONES"
    VIEW_EVIDENCE = "VIEW_EVIDENCE"
    VERIFY_EVIDENCE = "VERIFY_EVIDENCE"
    VIEW_ANPR = "VIEW_ANPR"
    VIEW_METRICS = "VIEW_METRICS"
    ADMIN_ALL = "ADMIN_ALL"


ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.VIEWER: {
        Permission.VIEW_INCIDENTS,
        Permission.VIEW_CAMERAS,
        Permission.VIEW_ZONES,
        Permission.VIEW_EVIDENCE,
        Permission.VIEW_ANPR,
        Permission.VIEW_METRICS,
    },
    Role.OPERATOR: {
        Permission.VIEW_INCIDENTS,
        Permission.ACKNOWLEDGE_INCIDENTS,
        Permission.MANAGE_INCIDENTS,
        Permission.VIEW_CAMERAS,
        Permission.VIEW_ZONES,
        Permission.VIEW_EVIDENCE,
        Permission.VERIFY_EVIDENCE,
        Permission.VIEW_ANPR,
        Permission.VIEW_METRICS,
    },
    Role.SUPERVISOR: {
        Permission.VIEW_INCIDENTS,
        Permission.ACKNOWLEDGE_INCIDENTS,
        Permission.MANAGE_INCIDENTS,
        Permission.VIEW_CAMERAS,
        Permission.VIEW_ZONES,
        Permission.VIEW_EVIDENCE,
        Permission.VERIFY_EVIDENCE,
        Permission.VIEW_ANPR,
        Permission.VIEW_METRICS,
    },
    Role.ADMIN: {p for p in Permission},   # all permissions
    Role.SYSTEM: {p for p in Permission},  # all permissions (internal)
}


def check_permission(role: Role, permission: Permission) -> bool:
    """Return True if the given role has the specified permission."""
    return permission in ROLE_PERMISSIONS.get(role, set())


def get_permissions(role: Role) -> Set[Permission]:
    """Return all permissions for a role."""
    return ROLE_PERMISSIONS.get(role, set())

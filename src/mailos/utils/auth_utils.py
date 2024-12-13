"""Authentication utilities for MailOS."""

import os
from functools import wraps

from pywebio.exceptions import SessionClosedException, SessionException
from pywebio.input import input, input_group
from pywebio.output import toast
from pywebio.session import info as session_info

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"


def get_auth_config():
    """Get authentication configuration from environment variables."""
    return {
        "enabled": os.environ.get("MAILOS_AUTH_ENABLED", "").lower() == "true",
        "username": os.environ.get("MAILOS_AUTH_USERNAME", DEFAULT_USERNAME),
        "password": os.environ.get("MAILOS_AUTH_PASSWORD", DEFAULT_PASSWORD),
    }


def authenticate():
    """Authenticate user with username and password."""
    auth_config = get_auth_config()

    if not auth_config["enabled"]:
        return True

    try:
        credentials = input_group(
            "Authentication Required",
            [
                input("Username", name="username", required=True),
                input("Password", name="password", type="password", required=True),
            ],
        )

        if (
            credentials["username"] == auth_config["username"]
            and credentials["password"] == auth_config["password"]
        ):
            return True

        toast("Invalid credentials", color="error")
        return False
    except (SessionClosedException, SessionException):
        # Handle PyWebIO session-related exceptions
        return False


def require_auth(func):
    """Require authentication for a route."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_config = get_auth_config()

        if not auth_config["enabled"]:
            return func(*args, **kwargs)

        # Check if already authenticated in this session
        if session_info.user_ip in getattr(wrapper, "_authenticated_ips", set()):
            return func(*args, **kwargs)

        if authenticate():
            # Store authentication state
            if not hasattr(wrapper, "_authenticated_ips"):
                wrapper._authenticated_ips = set()
            wrapper._authenticated_ips.add(session_info.user_ip)
            return func(*args, **kwargs)

        return authenticate()

    return wrapper

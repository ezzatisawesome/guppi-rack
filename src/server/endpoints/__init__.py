"""API endpoints for the server."""

from .manual import register_manual_endpoints
from .tests import register_test_endpoints

__all__ = ["register_manual_endpoints", "register_test_endpoints"]

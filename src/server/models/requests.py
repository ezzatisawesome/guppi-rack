"""Pydantic request models for API endpoints."""

from pydantic import BaseModel


class SetVoltageRequest(BaseModel):
    """Request model for setting voltage."""
    voltage: float


class SetCurrentRequest(BaseModel):
    """Request model for setting current limit."""
    current: float


class SetOutputRequest(BaseModel):
    """Request model for setting output state."""
    enabled: bool

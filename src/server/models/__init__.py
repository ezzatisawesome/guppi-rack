"""Pydantic models for API request bodies."""

from .requests import (
    SetCurrentRequest,
    SetOutputRequest,
    SetVoltageRequest,
)

__all__ = [
    "SetVoltageRequest",
    "SetCurrentRequest",
    "SetOutputRequest",
]

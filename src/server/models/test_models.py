"""Pydantic request/response models for test execution endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ScriptResponse(BaseModel):
    """Response model for GET /tests/script."""
    
    code: str
    updated_at: Optional[datetime] = None


class ExecuteTestRequest(BaseModel):
    """Request model for POST /tests/execute."""
    
    code: Optional[str] = None
    dut_serial: Optional[str] = None


class ExecuteTestResponse(BaseModel):
    """Response model for POST /tests/execute."""
    
    execution_id: str
    status: str
    error: Optional[str] = None


class TestStatusResponse(BaseModel):
    """Response model for GET /tests/status."""

    status: str  # "idle", "running"
    execution_id: Optional[str] = None
    started_at: Optional[datetime] = None
    test_running: bool = False
    test_id: Optional[str] = None
    manual_mode: Optional[bool] = None

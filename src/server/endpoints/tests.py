"""Test execution endpoints."""

import logging
import threading
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from sequencer import TestExecutor

from ..models.test_models import (
    ExecuteTestRequest,
    ExecuteTestResponse,
    ScriptResponse,
    TestStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tests", tags=["tests"])

# Global test executor instance (set by app initialization)
test_executor: Optional[TestExecutor] = None


def register_test_endpoints(app, executor: TestExecutor):
    """Register test execution endpoints with the FastAPI app.

    Args:
        app: FastAPI application instance.
        executor: TestExecutor instance.
    """
    global test_executor
    test_executor = executor

    app.include_router(router)


@router.get("/script", response_model=ScriptResponse)
async def get_script(
    script_path: str = Query(
        ...,
        description="Supabase Storage path, e.g. 'projects/<id>/scripts/test.py'",
    ),
):
    """Fetch a test script from Supabase Storage by path."""
    if test_executor is None:
        raise HTTPException(
            status_code=503, detail="Test executor not initialized"
        )

    script_code = test_executor.fetch_script_from_storage(script_path)

    if script_code is None:
        raise HTTPException(
            status_code=404,
            detail=f"Script not found in storage: {script_path}",
        )

    return ScriptResponse(code=script_code, script_path=script_path)


@router.post("/execute", response_model=ExecuteTestResponse)
async def execute_test(request: ExecuteTestRequest):
    """Execute a test script.

    If ``code`` is provided, uses it directly.
    Otherwise, fetches the script from Supabase Storage using ``script_path``.
    At least one of ``code`` or ``script_path`` must be provided.
    """
    if test_executor is None:
        raise HTTPException(
            status_code=503, detail="Test executor not initialized"
        )

    # Check if already executing
    if test_executor.is_executing():
        current = test_executor.get_current_execution()
        return ExecuteTestResponse(
            execution_id=(
                current.get("execution_id", "unknown") if current else "unknown"
            ),
            status="error",
            error="Another test is currently running",
        )

    # Resolve script code
    script_code = request.code
    if not script_code:
        if not request.script_path:
            raise HTTPException(
                status_code=400,
                detail="Either 'code' or 'script_path' must be provided",
            )

        script_code = test_executor.fetch_script_from_storage(
            request.script_path
        )
        if script_code is None:
            raise HTTPException(
                status_code=404,
                detail=f"Script not found in storage: {request.script_path}",
            )

    # Execute in background thread
    def run_test():
        try:
            result = test_executor.execute_test(
                script_code=script_code,
                dut_serial=request.dut_serial,
            )
            logger.info("Test execution completed: %s", result)
        except Exception as e:
            logger.error(
                "Error in background test execution: %s", e, exc_info=True
            )

    thread = threading.Thread(target=run_test, daemon=True)
    thread.start()

    # Wait briefly for execution to start and get execution_id
    for _ in range(20):  # Try up to 2 seconds
        if test_executor.is_executing():
            current = test_executor.get_current_execution()
            if current and current.get("execution_id"):
                return ExecuteTestResponse(
                    execution_id=current["execution_id"],
                    status=current["status"],
                )
        time.sleep(0.1)

    # If we get here, execution didn't start properly
    return ExecuteTestResponse(
        execution_id="unknown",
        status="error",
        error="Failed to start test execution - check server logs",
    )


@router.get("/status", response_model=TestStatusResponse)
async def get_test_status(request: Request):
    """Check if a test is currently running."""
    if test_executor is None:
        raise HTTPException(
            status_code=503, detail="Test executor not initialized"
        )

    # Read manual mode from shared save policy if available
    policy = getattr(request.app.state, "data_save_policy", None)
    manual_mode = (
        bool(getattr(policy, "manual_mode", False))
        if policy is not None
        else None
    )

    if test_executor.is_executing():
        current = test_executor.get_current_execution() or {}
        execution_id = current.get("execution_id")
        started_at = current.get("started_at")
        return TestStatusResponse(
            status="running",
            execution_id=execution_id,
            started_at=started_at,
            test_running=True,
            test_id=execution_id,
            manual_mode=manual_mode,
        )

    return TestStatusResponse(
        status="idle",
        execution_id=None,
        started_at=None,
        test_running=False,
        test_id=None,
        manual_mode=manual_mode,
    )

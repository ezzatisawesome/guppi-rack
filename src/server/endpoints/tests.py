"""Test execution endpoints."""

import logging
import threading
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse

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
async def get_script():
    """Fetch the current stored test script from Supabase."""
    if test_executor is None:
        raise HTTPException(
            status_code=503,
            detail="Test executor not initialized"
        )
    
    try:
        script_code = test_executor.fetch_script_from_db()
        
        if script_code is None:
            raise HTTPException(
                status_code=404,
                detail="No test script found in database"
            )
        
        # Note: updated_at would need to be fetched from DB if needed
        return ScriptResponse(code=script_code)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching script: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch script: {str(e)}"
        )


@router.post("/execute", response_model=ExecuteTestResponse)
async def execute_test(
    request: ExecuteTestRequest,
    background_tasks: BackgroundTasks,
):
    """Execute a test script.
    
    If `code` is provided, uses it directly. Otherwise, fetches script from Supabase.
    """
    if test_executor is None:
        raise HTTPException(
            status_code=503,
            detail="Test executor not initialized"
        )
    
    # Check if already executing
    if test_executor.is_executing():
        current = test_executor.get_current_execution()
        return ExecuteTestResponse(
            execution_id=current.get("execution_id", "unknown") if current else "unknown",
            status="error",
            error="Another test is currently running",
        )
    
    # Get script code
    script_code = request.code
    if not script_code:
        # Fetch from database
        script_code = test_executor.fetch_script_from_db()
        if script_code is None:
            raise HTTPException(
                status_code=404,
                detail="No test script found in database and no inline code provided"
            )
    
    # Execute in background thread
    def run_test():
        try:
            result = test_executor.execute_test(
                script_code=script_code,
                dut_serial=request.dut_serial,
            )
            logger.info(f"Test execution completed: {result}")
        except Exception as e:
            logger.error(f"Error in background test execution: {e}", exc_info=True)
    
    # Start execution in background
    import threading
    thread = threading.Thread(target=run_test, daemon=True)
    thread.start()
    
    # Wait briefly for execution to start and get execution_id
    import time
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
            status_code=503,
            detail="Test executor not initialized",
        )

    # Read manual mode from shared save policy if available
    policy = getattr(request.app.state, "data_save_policy", None)
    manual_mode = bool(getattr(policy, "manual_mode", False)) if policy is not None else None

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

"""FastAPI application for instrument control and telemetry management."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from server.endpoints import register_manual_endpoints
from server.endpoints.tests import register_test_endpoints
from sequencer import TestExecutor
from telemetry import TelemetryManager

logger = logging.getLogger(__name__)

class DataSavePolicy:
    """Holds shared state for controlling when telemetry data should be saved."""

    def __init__(self) -> None:
        self.manual_mode: bool = False
        self.test_executor: Optional[TestExecutor] = None


# Global telemetry manager instance
telemetry_manager: Optional[TelemetryManager] = None

# Global test executor instance
test_executor: Optional[TestExecutor] = None


def create_app(
    rig_config: dict,
    db_connection_pool,
    measurement_interval: float = 1.0,
    batch_size: int = 100,
    queue_maxsize: int = 10000,
    queue_behavior: str = "drop_oldest",
    table_name: str = "telemetry",
) -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Args:
        rig_config: Configuration dict containing instrument definitions.
        db_connection_pool: PostgreSQL connection pool (psycopg2.pool.ThreadedConnectionPool).
        measurement_interval: Time between measurements in seconds.
        batch_size: Number of measurements to batch before uploading.
        queue_maxsize: Maximum size of the measurement queue.
        queue_behavior: Behavior when queue is full ('drop_oldest', 'drop_new', 'block').
        table_name: Name of the database table (default: 'telemetry').
    
    Returns:
        Configured FastAPI application.
    """

    # Shared policy used to decide when telemetry measurements should be saved
    save_policy = DataSavePolicy()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Lifespan context manager for startup and shutdown events."""
        global telemetry_manager, test_executor
        
        # Startup
        logger.info("Starting application...")
        
        # Initialize telemetry manager
        telemetry_manager = TelemetryManager(
            rig_config=rig_config,
            db_connection_pool=db_connection_pool,
            measurement_interval=measurement_interval,
            batch_size=batch_size,
            queue_maxsize=queue_maxsize,
            queue_behavior=queue_behavior,
            table_name=table_name,
            get_should_save_data=lambda: (
                save_policy.manual_mode
                or (
                    save_policy.test_executor is not None
                    and save_policy.test_executor.is_executing()
                )
            ),
            get_test_id=lambda: (
                (save_policy.test_executor.get_current_execution() or {}).get("execution_id")
                if save_policy.test_executor is not None
                and save_policy.test_executor.is_executing()
                else None
            ),
        )
        
        # Start telemetry collection
        telemetry_manager.start()
        
        # Initialize test executor
        test_executor = TestExecutor(
            rig_config=rig_config,
            db_connection_pool=db_connection_pool,
        )
        save_policy.test_executor = test_executor

        # Store executor and policy in app state and update global in endpoints module
        app.state.test_executor = test_executor
        app.state.data_save_policy = save_policy
        from server.endpoints import tests as tests_module
        tests_module.test_executor = test_executor
        
        logger.info("Application started")
        
        yield
        
        # Shutdown
        logger.info("Shutting down application...")
        
        if telemetry_manager is not None:
            telemetry_manager.stop()
            telemetry_manager = None
        
        # Test executor cleanup (if needed)
        test_executor = None
        
        # Close database connection pool
        try:
            db_connection_pool.closeall()
            logger.info("Database connection pool closed")
        except Exception as e:
            logger.warning(f"Error closing connection pool: {e}")
        
        logger.info("Application shut down")
    
    app = FastAPI(
        title="Orbis Rack API",
        description="API for instrument control and telemetry",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    )
    
    # Store connection pool in app state for reference
    app.state.db_connection_pool = db_connection_pool
    
    # Register test execution endpoints (executor will be set in app.state during lifespan)
    register_test_endpoints(app, None)  # Executor will be available via app.state
    
    # Initialize instrument registry in app state
    app.state.instruments: dict[str, dict[str, Any]] = {}
    instruments_list = rig_config.get("instruments", [])
    for inst in instruments_list:
        instrument_id = inst.get("id")
        if instrument_id:
            app.state.instruments[instrument_id] = inst
    
    # Load raw YAML config for rig info (name, description, etc.)
    # Use same logic as rig_config_loader
    config_path = os.getenv("RIG_CONFIG_PATH", "rig_config.yml")
    if not os.path.isabs(config_path):
        # If relative path, look in current directory (project root when running from main.py)
        config_file = Path(config_path)
    else:
        config_file = Path(config_path)
    
    raw_rig_config = {}
    if config_file.exists():
        with open(config_file, "r") as f:
            raw_config = yaml.safe_load(f)
            raw_rig_config = raw_config.get("rig", {})
    
    # Store raw rig config in app state
    app.state.raw_rig_config = raw_rig_config
    
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {"message": "Orbis Rack API", "status": "running"}
    
    @app.get("/health")
    async def health():
        """Health check endpoint."""
        telemetry_running = False
        if telemetry_manager is not None:
            # Check if threads are running
            measurement_running = (
                telemetry_manager._measurement_thread is not None
                and telemetry_manager._measurement_thread.is_alive()
            )
            uploader_running = (
                telemetry_manager._uploader_thread is not None
                and telemetry_manager._uploader_thread.is_alive()
            )
        
        return {
            "status": "healthy",
            "measurement_running": measurement_running,
            "uploader_running": uploader_running,
        }
    
    @app.get("/telemetry/stats")
    async def get_telemetry_stats():
        """Get telemetry statistics."""
        if telemetry_manager is None:
            return JSONResponse(
                status_code=503,
                content={"error": "Telemetry manager not initialized"}
            )
        
        stats = telemetry_manager.get_stats()
        return stats
    
    @app.post("/telemetry/start")
    async def start_telemetry():
        """Manually start telemetry (if not already running)."""
        global telemetry_manager
        
        if telemetry_manager is None:
            return JSONResponse(
                status_code=503,
                content={"error": "Telemetry manager not initialized"}
            )
        
        if telemetry_manager._measurement_thread is not None and telemetry_manager._measurement_thread.is_alive():
            return {"message": "Telemetry already running"}
        
        telemetry_manager.start()
        return {"message": "Telemetry started"}
    
    @app.post("/telemetry/stop")
    async def stop_telemetry():
        """Manually stop telemetry."""
        global telemetry_manager
        
        if telemetry_manager is None:
            return JSONResponse(
                status_code=503,
                content={"error": "Telemetry manager not initialized"}
            )
        
        telemetry_manager.stop()
        return {"message": "Telemetry stopped"}
    
    # Rig information endpoint
    @app.get("/rig")
    async def get_rig_info():
        """Get rig information including all instruments."""
        raw_config = app.state.raw_rig_config
        instruments_list = rig_config.get("instruments", [])
        
        # Build API instrument list
        api_instruments = []
        for inst in instruments_list:
            instrument_id = inst.get("id")
            if not instrument_id:
                continue
            
            # Extract channels from driver
            driver = inst.get("driver")
            if driver and hasattr(driver, "num_channels"):
                channels = list(range(1, driver.num_channels + 1))
            else:
                # Fallback: extract from signals if driver not available
                channels = sorted(set(
                    signal.channel for signal in inst.get("signals", [])
                ))
            
            # Get connection info from raw config
            connection_info = None
            raw_inst_config = None
            raw_instruments = raw_config.get("instruments", [])
            for raw_inst in raw_instruments:
                if raw_inst.get("id") == instrument_id:
                    raw_inst_config = raw_inst
                    conn_config = raw_inst.get("connection", {})
                    connection_info = {
                        "type": conn_config.get("type", ""),
                        "address": conn_config.get("address", ""),
                        "timeout": conn_config.get("timeout", 10.0),
                        "connected": inst.get("driver") is not None,
                    }
                    break
            
            # Try to get identification from driver
            identification = None
            driver = inst.get("driver")
            if driver:
                try:
                    identification = driver.identify()
                except Exception:
                    pass
            
            api_instruments.append({
                "id": instrument_id,
                "name": inst.get("name", ""),
                "type": raw_inst_config.get("type", "") if raw_inst_config else "",
                "enabled": raw_inst_config.get("enabled", True) if raw_inst_config else True,
                "channels": channels,
                "num_channels": raw_inst_config.get("num_channels") if raw_inst_config else None,
                "connection": connection_info or {
                    "type": "",
                    "address": "",
                    "timeout": 10.0,
                    "connected": False,
                },
                "identification": identification,
            })
        
        return {
            "id": rig_config.get("rig_id", raw_config.get("id", "")),
            "name": raw_config.get("name"),
            "description": raw_config.get("description"),
            "telemetry": {
                "measurement_interval": rig_config.get("telemetry", {}).get("measurement_interval"),
                "enabled": rig_config.get("telemetry", {}).get("enabled"),
            },
            "instruments": api_instruments,
            "total_instruments": len(api_instruments),
        }
    
    # Register manual control endpoints
    register_manual_endpoints(app, rig_config)
    
    # ── Rig Manifest (Phase 23, D-07, D-11) ──────────────────────────
    # Returns all addressable instrument paths from the boot configuration.
    # Used by the frontend widget editor for auto-complete dropdowns.
    
    @app.get("/manifest")
    async def get_manifest():
        """Get the rig manifest — all addressable instrument paths and their types.
        
        Phase 23 (D-11): Statically reflects the instrument capabilities 
        defined in the boot configuration file. No real-time hardware pinging.
        """
        instruments_list = rig_config.get("instruments", [])
        paths = []
        
        for inst in instruments_list:
            instrument_id = inst.get("id")
            if not instrument_id:
                continue
            
            driver = inst.get("driver")
            signals = inst.get("signals", [])
            
            for signal in signals:
                # Build flat path from signal config
                path = f"{instrument_id}.ch{signal.channel}.{signal.signal_type}"
                
                # Determine unit from signal type
                if signal.signal_type == "voltage":
                    data_type = "float"
                    unit = "V"
                elif signal.signal_type == "current":
                    data_type = "float"
                    unit = "A"
                else:
                    data_type = "float"
                    unit = ""
                
                paths.append({
                    "path": path,
                    "type": data_type,
                    "unit": unit,
                })
        
        # Add system meta paths
        paths.append({"path": "system.test_running", "type": "bool", "unit": "bool"})
        paths.append({"path": "system.test_id", "type": "string", "unit": "id"})
        
        return {"paths": paths}
    
    # Initialize test executor (will be set in lifespan, but router registration happens here)
    # The executor will be available when endpoints are called
    test_executor_instance = None
    
    return app


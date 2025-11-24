"""FastAPI application for instrument control and telemetry management."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from telemetry import TelemetryManager

logger = logging.getLogger(__name__)

# Global telemetry manager instance
telemetry_manager: Optional[TelemetryManager] = None


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
    
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Lifespan context manager for startup and shutdown events."""
        global telemetry_manager
        
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
        )
        
        # Start telemetry collection
        telemetry_manager.start()
        
        logger.info("Application started")
        
        yield
        
        # Shutdown
        logger.info("Shutting down application...")
        
        if telemetry_manager is not None:
            telemetry_manager.stop()
            telemetry_manager = None
        
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
    
    # Store connection pool in app state for reference
    app.state.db_connection_pool = db_connection_pool
    
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
    
    return app


"""Main entry point for running the FastAPI server."""

import logging
import sys
from pathlib import Path

import uvicorn

# Add src directory to path to allow absolute imports
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from config import load_rig_config
from server.app import create_app
from server.config import get_db_connection_pool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the server."""
    # Setup database connection pool
    try:
        db_connection_pool = get_db_connection_pool(
            min_conn=1,
            max_conn=5,
        )
        logger.info("Database connection pool initialized")
    except ValueError as e:
        error_msg = str(e)
        if "DATABASE_URL environment variable must be set" in error_msg:
            logger.error("DATABASE_URL environment variable is not set")
            logger.error("Please set DATABASE_URL in your .env file or environment")
        else:
            logger.error(f"Failed to initialize database connection pool: {e}")
            logger.error("This may be a configuration or authentication issue.")
        sys.exit(1)
    except ConnectionError as e:
        logger.error(f"Failed to connect to database: {e}")
        logger.error("This is a network connectivity issue. Please check:")
        logger.error("  - Your internet connection")
        logger.error("  - Firewall settings (port 5432)")
        logger.error("  - Database server accessibility")
        logger.error("  - IPv6 connectivity (if your connection URL uses IPv6)")
        logger.error("  - Try using IPv4 address if IPv6 is not available")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to initialize database connection pool: {e}")
        logger.error("Unexpected error occurred. Please check your configuration.")
        sys.exit(1)
    
    # Load rig configuration from YAML
    try:
        rig_config = load_rig_config()
        logger.info("Rig configuration loaded successfully")
    except FileNotFoundError as e:
        logger.error(f"Rig configuration file not found: {e}")
        logger.error("Please create rig_config.yml (see rig_config.yml.example)")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Invalid rig configuration: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to load rig configuration: {e}", exc_info=True)
        sys.exit(1)
    
    # Get telemetry settings from config (with defaults)
    telemetry_config = rig_config.get("telemetry", {})
    measurement_interval = telemetry_config.get("measurement_interval", 1.0)
    
    # Create FastAPI app
    app = create_app(
        rig_config=rig_config,
        db_connection_pool=db_connection_pool,
        measurement_interval=measurement_interval,
        batch_size=100,  # Upload in batches of 100
        queue_maxsize=10000,  # Max 10000 measurements in queue
        queue_behavior="drop_oldest",  # Drop oldest when queue is full
        table_name="telemetry",  # Database table name
    )
    
    # Run server
    logger.info("Starting server on http://0.0.0.0:8000")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )


if __name__ == "__main__":
    main()


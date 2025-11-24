"""YAML-based rig configuration loader."""

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from devices.core.connection import ConnectionType, create_connection
from devices.core.thread_safe_connection import ThreadSafeConnection
from devices.psu import BK9130, BK9200
from telemetry.models import SignalConfig

logger = logging.getLogger(__name__)

# Map instrument types to driver classes
INSTRUMENT_DRIVERS = {
    "BK9130": BK9130,
    "BK9200": BK9200,
}


def load_rig_config(config_path: str | None = None) -> dict[str, Any]:
    """
    Load rig configuration from YAML file.
    
    Args:
        config_path: Path to YAML config file. If None, looks for 'rig_config.yml' in current directory.
    
    Returns:
        Rig configuration dict with 'instruments' key containing instrument configs.
    
    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If config is invalid.
    """
    if config_path is None:
        config_path = os.getenv("RIG_CONFIG_PATH", "rig_config.yml")
    
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Rig configuration file not found: {config_path}")
    
    logger.info(f"Loading rig configuration from {config_path}")
    
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
    
    if not config or "rig" not in config:
        raise ValueError("Invalid rig configuration: missing 'rig' section")
    
    rig_config = config["rig"]
    
    # Extract rig_id (required for multi-rig deployments)
    rig_id = rig_config.get("id")
    if not rig_id:
        raise ValueError("Rig configuration missing 'id' field. Each rig must have a unique identifier.")
    
    instruments_config = rig_config.get("instruments", [])
    
    if not instruments_config:
        raise ValueError("No instruments configured in rig_config.yml")
    
    # Build instrument objects from config
    instruments = []
    
    for inst_config in instruments_config:
        if not inst_config.get("enabled", True):
            logger.info(f"Skipping disabled instrument: {inst_config.get('id', 'unknown')}")
            continue
        
        try:
            instrument = _create_instrument(inst_config, rig_id)
            if instrument:
                instruments.append(instrument)
        except Exception as e:
            logger.error(
                f"Failed to create instrument {inst_config.get('id', 'unknown')}: {e}",
                exc_info=True
            )
            # Continue with other instruments even if one fails
    
    if not instruments:
        raise ValueError("No instruments could be initialized. Check your configuration.")
    
    logger.info(f"Successfully configured {len(instruments)} instrument(s) for rig '{rig_id}'")
    
    # Extract telemetry settings if present
    telemetry_config = rig_config.get("telemetry", {})
    
    return {
        "rig_id": rig_id,
        "instruments": instruments,
        "telemetry": telemetry_config,
    }


def _create_instrument(inst_config: dict[str, Any], rig_id: str) -> dict[str, Any] | None:
    """
    Create an instrument driver and configuration from YAML config.
    
    Args:
        inst_config: Instrument configuration dict from YAML.
    
    Returns:
        Instrument configuration dict with 'id', 'name', 'driver', and 'signals'.
    
    Raises:
        ValueError: If configuration is invalid.
    """
    instrument_id = inst_config.get("id")
    instrument_name = inst_config.get("name")
    instrument_type = inst_config.get("type")
    connection_config = inst_config.get("connection", {})
    signals_config = inst_config.get("signals", [])
    
    if not instrument_id:
        raise ValueError("Instrument missing 'id' field")
    if not instrument_name:
        raise ValueError(f"Instrument {instrument_id} missing 'name' field")
    if not instrument_type:
        raise ValueError(f"Instrument {instrument_id} missing 'type' field")
    if not connection_config:
        raise ValueError(f"Instrument {instrument_id} missing 'connection' section")
    
    # Get driver class
    driver_class = INSTRUMENT_DRIVERS.get(instrument_type)
    if not driver_class:
        raise ValueError(
            f"Unknown instrument type '{instrument_type}' for instrument {instrument_id}. "
            f"Available types: {list(INSTRUMENT_DRIVERS.keys())}"
        )
    
    # Create connection
    connection_type_str = connection_config.get("type", "VISA").upper()
    try:
        connection_type = ConnectionType[connection_type_str]
    except KeyError:
        raise ValueError(
            f"Unknown connection type '{connection_type_str}' for instrument {instrument_id}"
        )
    
    address = connection_config.get("address")
    if not address:
        raise ValueError(f"Instrument {instrument_id} missing connection 'address'")
    
    timeout = connection_config.get("timeout", 10.0)
    
    # Create connection and driver
    connection = create_connection(
        connection_type=connection_type,
        address=address,
        timeout=timeout,
    )
    
    thread_safe_conn = ThreadSafeConnection(connection)
    
    # Create driver instance (handle special parameters)
    driver_kwargs = {}
    if instrument_type == "BK9200":
        # BK9200 needs num_channels parameter
        driver_kwargs["num_channels"] = inst_config.get("num_channels", 1)
    
    driver = driver_class(thread_safe_conn, **driver_kwargs)
    
    # Connect to instrument
    if not connection.is_connected():
        connection.connect()
    
    logger.info(f"Connected to {instrument_name} ({instrument_id}) at {address}")
    
    # Build signal configurations
    signals = []
    for signal_config in signals_config:
        channel = signal_config.get("channel")
        if channel is None:
            logger.warning(f"Skipping signal config missing 'channel' in instrument {instrument_id}")
            continue
        
        # Check which signal types are enabled
        if signal_config.get("voltage", {}).get("enabled", True):
            signals.append(
                SignalConfig(
                    rig_id=rig_id,
                    instrument_id=instrument_id,
                    instrument_name=instrument_name,
                    signal_type="voltage",
                    channel=channel,
                )
            )
        
        if signal_config.get("current", {}).get("enabled", True):
            signals.append(
                SignalConfig(
                    rig_id=rig_id,
                    instrument_id=instrument_id,
                    instrument_name=instrument_name,
                    signal_type="current",
                    channel=channel,
                )
            )
    
    if not signals:
        logger.warning(f"No signals configured for instrument {instrument_id}")
        return None
    
    return {
        "id": instrument_id,
        "name": instrument_name,
        "driver": driver,
        "signals": signals,
    }


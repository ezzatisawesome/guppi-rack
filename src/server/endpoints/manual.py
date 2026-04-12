"""Manual instrument control endpoints."""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel

from ..models import SetCurrentRequest, SetOutputRequest, SetVoltageRequest

logger = logging.getLogger(__name__)


class ManualModeRequest(BaseModel):
    """Request model for setting manual mode."""

    enabled: bool


def register_manual_endpoints(app: FastAPI, rig_config: dict):
    """Register manual control endpoints with the FastAPI app.
    
    Args:
        app: FastAPI application instance.
        rig_config: Rig configuration dict containing instruments.
    """
    # Manual mode endpoints
    @app.get("/manual/mode")
    async def get_manual_mode():
        """Get current manual mode state used for telemetry saving."""
        policy = getattr(app.state, "data_save_policy", None)
        if policy is None:
            raise HTTPException(
                status_code=503,
                detail="Data save policy not initialized",
            )
        return {"manual_mode": bool(getattr(policy, "manual_mode", False))}

    @app.post("/manual/mode")
    async def set_manual_mode(request: ManualModeRequest):
        """Set manual mode state used for telemetry saving."""
        policy = getattr(app.state, "data_save_policy", None)
        if policy is None:
            raise HTTPException(
                status_code=503,
                detail="Data save policy not initialized",
            )
        policy.manual_mode = request.enabled
        logger.info("Manual mode set to %s", policy.manual_mode)
        return {"manual_mode": policy.manual_mode}

    # Discovery endpoints
    @app.get("/manual")
    async def list_instruments():
        """List all configured instruments."""
        instruments_list = []
        for inst_id, inst_config in app.state.instruments.items():
            # Extract channels from driver
            driver = inst_config.get("driver")
            if driver and hasattr(driver, "num_channels"):
                channels = list(range(1, driver.num_channels + 1))
            else:
                # Fallback: extract from signals if driver not available
                channels = sorted(set(
                    signal.channel for signal in inst_config.get("signals", [])
                ))
            
            instruments_list.append({
                "id": inst_id,
                "name": inst_config.get("name"),
                "channels": sorted(list(channels)),
            })
        return {"instruments": instruments_list}
    
    @app.get("/manual/{instrument_id}")
    async def get_instrument(instrument_id: str = Path(..., description="Instrument ID")):
        """Get instrument details including available channels."""
        if instrument_id not in app.state.instruments:
            raise HTTPException(status_code=404, detail=f"Instrument '{instrument_id}' not found")
        
        inst_config = app.state.instruments[instrument_id]
        
        # Extract channels from driver
        driver = inst_config.get("driver")
        if driver and hasattr(driver, "num_channels"):
            channels = list(range(1, driver.num_channels + 1))
        else:
            # Fallback: extract from signals if driver not available
            channels = sorted(set(
                signal.channel for signal in inst_config.get("signals", [])
            ))
        
        return {
            "id": instrument_id,
            "name": inst_config.get("name"),
            "channels": channels,
        }
    
    @app.get("/manual/{instrument_id}/channels")
    async def list_channels(instrument_id: str = Path(..., description="Instrument ID")):
        """List all channels for an instrument."""
        if instrument_id not in app.state.instruments:
            raise HTTPException(status_code=404, detail=f"Instrument '{instrument_id}' not found")
        
        inst_config = app.state.instruments[instrument_id]
        
        # Extract channels from driver
        driver = inst_config.get("driver")
        if driver and hasattr(driver, "num_channels"):
            channels = list(range(1, driver.num_channels + 1))
        else:
            # Fallback: extract from signals if driver not available
            channels = sorted(set(
                signal.channel for signal in inst_config.get("signals", [])
            ))
        
        return {
            "instrument_id": instrument_id,
            "channels": channels,
        }
    
    # Control endpoints
    @app.post("/manual/{instrument_id}/channels/{channel_id}/set_voltage")
    async def set_voltage(
        request: SetVoltageRequest,
        instrument_id: str = Path(..., description="Instrument ID"),
        channel_id: int = Path(..., description="Channel ID"),
    ):
        """Set voltage for a channel."""
        return await _handle_set_voltage(app, instrument_id, channel_id, request)
    
    @app.get("/manual/{instrument_id}/channels/{channel_id}/get_voltage")
    async def get_voltage(
        instrument_id: str = Path(..., description="Instrument ID"),
        channel_id: int = Path(..., description="Channel ID"),
    ):
        """Get voltage setting for a channel."""
        return await _handle_get_voltage(app, instrument_id, channel_id)
    
    @app.post("/manual/{instrument_id}/channels/{channel_id}/set_current")
    async def set_current(
        request: SetCurrentRequest,
        instrument_id: str = Path(..., description="Instrument ID"),
        channel_id: int = Path(..., description="Channel ID"),
    ):
        """Set current limit for a channel."""
        return await _handle_set_current(app, instrument_id, channel_id, request)
    
    @app.get("/manual/{instrument_id}/channels/{channel_id}/get_current")
    async def get_current(
        instrument_id: str = Path(..., description="Instrument ID"),
        channel_id: int = Path(..., description="Channel ID"),
    ):
        """Get current limit for a channel."""
        return await _handle_get_current(app, instrument_id, channel_id)
    
    @app.get("/manual/{instrument_id}/channels/{channel_id}/measure_voltage")
    async def measure_voltage(
        instrument_id: str = Path(..., description="Instrument ID"),
        channel_id: int = Path(..., description="Channel ID"),
    ):
        """Measure actual voltage for a channel."""
        return await _handle_measure_voltage(app, instrument_id, channel_id)
    
    @app.get("/manual/{instrument_id}/channels/{channel_id}/measure_current")
    async def measure_current(
        instrument_id: str = Path(..., description="Instrument ID"),
        channel_id: int = Path(..., description="Channel ID"),
    ):
        """Measure actual current for a channel."""
        return await _handle_measure_current(app, instrument_id, channel_id)
    
    @app.post("/manual/{instrument_id}/channels/{channel_id}/set_output")
    async def set_output(
        request: SetOutputRequest,
        instrument_id: str = Path(..., description="Instrument ID"),
        channel_id: int = Path(..., description="Channel ID"),
    ):
        """Enable/disable output for a channel."""
        return await _handle_set_output(app, instrument_id, channel_id, request)
    
    @app.get("/manual/{instrument_id}/channels/{channel_id}/get_output")
    async def get_output(
        instrument_id: str = Path(..., description="Instrument ID"),
        channel_id: int = Path(..., description="Channel ID"),
    ):
        """Get output state for a channel."""
        return await _handle_get_output(app, instrument_id, channel_id)


def _validate_instrument_channel(app: FastAPI, instrument_id: str, channel_id: int) -> tuple[Any, Any]:
    """Validate instrument and channel, return driver and config.
    
    Args:
        app: FastAPI application instance.
        instrument_id: Instrument ID.
        channel_id: Channel ID.
    
    Returns:
        Tuple of (driver, instrument_config).
    
    Raises:
        HTTPException: If instrument or channel is invalid.
    """
    if instrument_id not in app.state.instruments:
        raise HTTPException(status_code=404, detail=f"Instrument '{instrument_id}' not found")
    
    inst_config = app.state.instruments[instrument_id]
    driver = inst_config["driver"]
    
    # Validate channel exists in driver
    if not hasattr(driver, "num_channels"):
        raise HTTPException(
            status_code=500,
            detail=f"Driver for instrument '{instrument_id}' does not have num_channels attribute"
        )
    
    if channel_id < 1 or channel_id > driver.num_channels:
        raise HTTPException(
            status_code=404,
            detail=f"Channel {channel_id} not found for instrument '{instrument_id}'. Available channels: {list(range(1, driver.num_channels + 1))}"
        )
    
    return driver, inst_config


async def _handle_set_voltage(
    app: FastAPI,
    instrument_id: str,
    channel_id: int,
    request: SetVoltageRequest,
) -> dict:
    """Handle set_voltage request."""
    logger.info(f"Received Command: SET_VOLTAGE | Instrument: {instrument_id} | Channel: {channel_id} | Voltage: {request.voltage}V")
    if request.voltage < 0:
        raise HTTPException(status_code=400, detail="Voltage must be non-negative")
    
    try:
        driver, _ = _validate_instrument_channel(app, instrument_id, channel_id)
        driver.set_voltage(channel_id, request.voltage)
        return {
            "instrument_id": instrument_id,
            "channel": channel_id,
            "voltage": request.voltage,
            "status": "success",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting voltage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to set voltage: {str(e)}")


async def _handle_get_voltage(
    app: FastAPI,
    instrument_id: str,
    channel_id: int,
) -> dict:
    """Handle get_voltage request."""
    try:
        driver, _ = _validate_instrument_channel(app, instrument_id, channel_id)
        voltage = driver.get_voltage(channel_id)
        return {
            "instrument_id": instrument_id,
            "channel": channel_id,
            "voltage": voltage,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting voltage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get voltage: {str(e)}")


async def _handle_set_current(
    app: FastAPI,
    instrument_id: str,
    channel_id: int,
    request: SetCurrentRequest,
) -> dict:
    """Handle set_current request."""
    logger.info(f"Received Command: SET_CURRENT | Instrument: {instrument_id} | Channel: {channel_id} | Current: {request.current}A")
    if request.current < 0:
        raise HTTPException(status_code=400, detail="Current must be non-negative")
    
    try:
        driver, _ = _validate_instrument_channel(app, instrument_id, channel_id)
        driver.set_current(channel_id, request.current)
        return {
            "instrument_id": instrument_id,
            "channel": channel_id,
            "current": request.current,
            "status": "success",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting current: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to set current: {str(e)}")


async def _handle_get_current(
    app: FastAPI,
    instrument_id: str,
    channel_id: int,
) -> dict:
    """Handle get_current request."""
    try:
        driver, _ = _validate_instrument_channel(app, instrument_id, channel_id)
        current = driver.get_current(channel_id)
        return {
            "instrument_id": instrument_id,
            "channel": channel_id,
            "current": current,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting current: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get current: {str(e)}")


async def _handle_measure_voltage(
    app: FastAPI,
    instrument_id: str,
    channel_id: int,
) -> dict:
    """Handle measure_voltage request."""
    try:
        driver, _ = _validate_instrument_channel(app, instrument_id, channel_id)
        voltage = driver.measure_voltage(channel_id)
        return {
            "instrument_id": instrument_id,
            "channel": channel_id,
            "voltage": voltage,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error measuring voltage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to measure voltage: {str(e)}")


async def _handle_measure_current(
    app: FastAPI,
    instrument_id: str,
    channel_id: int,
) -> dict:
    """Handle measure_current request."""
    try:
        driver, _ = _validate_instrument_channel(app, instrument_id, channel_id)
        current = driver.measure_current(channel_id)
        return {
            "instrument_id": instrument_id,
            "channel": channel_id,
            "current": current,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error measuring current: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to measure current: {str(e)}")


async def _handle_set_output(
    app: FastAPI,
    instrument_id: str,
    channel_id: int,
    request: SetOutputRequest,
) -> dict:
    """Handle set_output request."""
    logger.info(f"Received Command: SET_OUTPUT | Instrument: {instrument_id} | Channel: {channel_id} | Enabled: {request.enabled}")
    try:
        driver, _ = _validate_instrument_channel(app, instrument_id, channel_id)
        # Check if driver is an ELoad (has set_load) or PSU (has set_output)
        if hasattr(driver, "set_load"):
            # Electronic load
            driver.set_load(channel_id, request.enabled)
        elif hasattr(driver, "set_output"):
            # Power supply
            driver.set_output(channel_id, request.enabled)
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Driver for instrument '{instrument_id}' does not support output/load control"
            )
        return {
            "instrument_id": instrument_id,
            "channel": channel_id,
            "enabled": request.enabled,
            "status": "success",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting output: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to set output: {str(e)}")


async def _handle_get_output(
    app: FastAPI,
    instrument_id: str,
    channel_id: int,
) -> dict:
    """Handle get_output request."""
    try:
        driver, _ = _validate_instrument_channel(app, instrument_id, channel_id)
        # Check if driver is an ELoad (has get_load) or PSU (has get_output)
        if hasattr(driver, "get_load"):
            # Electronic load
            enabled = driver.get_load(channel_id)
        elif hasattr(driver, "get_output"):
            # Power supply
            enabled = driver.get_output(channel_id)
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Driver for instrument '{instrument_id}' does not support output/load query"
            )
        return {
            "instrument_id": instrument_id,
            "channel": channel_id,
            "enabled": enabled,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting output: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get output: {str(e)}")

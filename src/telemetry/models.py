"""Data models for telemetry measurements.

Phase 23 (D-01, D-10): Flat-path architecture. The `path` field replaces the
legacy `signal_type` and `channel` columns, enabling support for arbitrary
instrument types without a fixed column schema.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class SignalConfig:
    """Configuration for a signal to measure from an instrument.
    
    Attributes:
        rig_id: Unique identifier for the rig.
        instrument_id: Unique identifier for the instrument.
        instrument_name: Human-readable name of the instrument.
        path: Flat path string for this signal (e.g. "psu1.voltage", "psu1.current").
        signal_type: Original signal type used by the driver (e.g. 'voltage', 'current').
        channel: Channel number (1-based), used by the driver to read the correct channel.
        unit: Engineering unit for this signal (e.g. "V", "A", "Ω", "s", "W").
    """
    rig_id: str
    instrument_id: str
    instrument_name: str
    path: str
    signal_type: str  # Still needed internally to call the correct driver method
    channel: int      # Still needed internally for driver.measure_voltage(channel)
    unit: str


@dataclass
class Measurement:
    """A single telemetry measurement.
    
    Phase 23 (D-10): Uses flat `path` column instead of separate
    signal_type and channel columns.
    
    Attributes:
        recorded_at: When the measurement was taken.
        rig_id: Unique identifier for the rig.
        instrument_id: Unique identifier for the instrument.
        instrument_name: Human-readable name of the instrument.
        path: Flat path string (e.g. "psu1.ch1.voltage").
        value: The measured value.
        unit: Unit of measurement (e.g., 'V', 'A').
        execution_id: Optional identifier of the test execution
            this measurement is associated with.
    """
    recorded_at: datetime
    rig_id: str
    instrument_id: str
    instrument_name: str
    path: str
    value: float
    unit: str
    execution_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert measurement to dictionary for database insertion."""
        return {
            "recorded_at": self.recorded_at.isoformat(),
            "rig_id": self.rig_id,
            "instrument_id": self.instrument_id,
            "instrument_name": self.instrument_name,
            "path": self.path,
            "value": self.value,
            "unit": self.unit,
            "execution_id": self.execution_id,
        }

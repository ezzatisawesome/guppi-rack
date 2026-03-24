"""Data models for telemetry measurements."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class SignalConfig:
    """Configuration for a signal to measure from an instrument.
    
    Attributes:
        rig_id: Unique identifier for the rig.
        instrument_id: Unique identifier for the instrument.
        instrument_name: Human-readable name of the instrument.
        signal_type: Type of signal (e.g., 'voltage', 'current').
        channel: Channel number (1-based).
    """
    rig_id: str
    instrument_id: str
    instrument_name: str
    signal_type: str  # 'voltage' or 'current'
    channel: int


@dataclass
class Measurement:
    """A single telemetry measurement.
    
    Attributes:
        recorded_at: When the measurement was taken.
        rig_id: Unique identifier for the rig.
        instrument_id: Unique identifier for the instrument.
        instrument_name: Human-readable name of the instrument.
        signal_type: Type of signal (e.g., 'voltage', 'current').
        channel: Channel number.
        value: The measured value.
        unit: Unit of measurement (e.g., 'V', 'A').
        execution_id: Optional[str]: Optional identifier of the test execution
            this measurement is associated with (if collected during a test).
    """
    recorded_at: datetime
    rig_id: str
    instrument_id: str
    instrument_name: str
    signal_type: str
    channel: int
    value: float
    unit: str
    execution_id: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert measurement to dictionary for database insertion."""
        return {
            "recorded_at": self.recorded_at.isoformat(),
            "rig_id": self.rig_id,
            "instrument_id": self.instrument_id,
            "instrument_name": self.instrument_name,
            "signal_type": self.signal_type,
            "channel": self.channel,
            "value": self.value,
            "unit": self.unit,
            "execution_id": self.execution_id,
        }


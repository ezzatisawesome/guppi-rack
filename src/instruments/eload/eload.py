"""Electronic Load abstract base class."""

from abc import ABC, abstractmethod
from enum import Enum

from ..core.connection import Connection


class LoadMode(Enum):
    """Electronic load operating modes."""
    CC = "CC"  # Constant Current
    CV = "CV"  # Constant Voltage
    CR = "CR"  # Constant Resistance
    CP = "CP"  # Constant Power


class ELoad(ABC):
    """Abstract base class for electronic loads."""

    def __init__(
        self,
        connection: Connection,
        num_channels: int,
        channel_limits: list[dict[str, float]],
    ):
        """
        Initialize ELoad with a connection and channel configuration.
        
        Args:
            connection: Connection object to communicate with the ELoad.
            num_channels: Number of channels on this ELoad.
            channel_limits: Array of channel limits. Each element is a dict with
                'voltage_max', 'current_max', 'power_max', and optionally 'resistance_min' keys.
                Index 0 = channel 1, index 1 = channel 2, etc.
        """
        self.connection = connection
        self.num_channels = num_channels
        self.channel_limits = channel_limits
    
    def _validate_channel(self, channel: int):
        """
        Validate channel number.
        
        Args:
            channel: Channel number (1-based).
        
        Raises:
            ValueError: If channel is out of range.
        """
        if channel < 1 or channel > self.num_channels:
            raise ValueError(f"Channel must be between 1 and {self.num_channels}, got {channel}")
    
    def _validate_current(self, channel: int, current: float):
        """
        Validate current value against channel limits.
        
        Args:
            channel: Channel number (1-based).
            current: Current value in amperes.
        
        Raises:
            ValueError: If current is negative or exceeds channel limit.
        """
        if current < 0:
            raise ValueError(f"Current must be non-negative, got {current}A")
        
        self._validate_channel(channel)
        channel_index = channel - 1
        current_max = self.channel_limits[channel_index].get("current_max", float("inf"))
        
        if current > current_max:
            raise ValueError(
                f"Current {current}A exceeds maximum for channel {channel} ({current_max}A)"
            )
    
    def _validate_voltage(self, channel: int, voltage: float):
        """
        Validate voltage value against channel limits.
        
        Args:
            channel: Channel number (1-based).
            voltage: Voltage value in volts.
        
        Raises:
            ValueError: If voltage is negative or exceeds channel limit.
        """
        if voltage < 0:
            raise ValueError(f"Voltage must be non-negative, got {voltage}V")
        
        self._validate_channel(channel)
        channel_index = channel - 1
        voltage_max = self.channel_limits[channel_index].get("voltage_max", float("inf"))
        
        if voltage > voltage_max:
            raise ValueError(
                f"Voltage {voltage}V exceeds maximum for channel {channel} ({voltage_max}V)"
            )
    
    def _validate_power(self, channel: int, power: float):
        """
        Validate power value against channel limits.
        
        Args:
            channel: Channel number (1-based).
            power: Power value in watts.
        
        Raises:
            ValueError: If power is negative or exceeds channel limit.
        """
        if power < 0:
            raise ValueError(f"Power must be non-negative, got {power}W")
        
        self._validate_channel(channel)
        channel_index = channel - 1
        power_max = self.channel_limits[channel_index].get("power_max", float("inf"))
        
        if power > power_max:
            raise ValueError(
                f"Power {power}W exceeds maximum for channel {channel} ({power_max}W)"
            )
    
    def _validate_resistance(self, channel: int, resistance: float):
        """
        Validate resistance value against channel limits.
        
        Args:
            channel: Channel number (1-based).
            resistance: Resistance value in ohms.
        
        Raises:
            ValueError: If resistance is invalid or out of range.
        """
        if resistance <= 0:
            raise ValueError(f"Resistance must be positive, got {resistance}Ω")
        
        self._validate_channel(channel)
        channel_index = channel - 1
        resistance_min = self.channel_limits[channel_index].get("resistance_min", 0.0)
        
        if resistance < resistance_min:
            raise ValueError(
                f"Resistance {resistance}Ω is below minimum for channel {channel} ({resistance_min}Ω)"
            )

    @abstractmethod
    def identify(self) -> str:
        """
        Query instrument identification.
        
        Returns:
            Identification string from the instrument.
        """
        pass

    @abstractmethod
    def set_current(self, channel: int, current: float):
        """
        Set load current for a channel (CC mode).
        
        Args:
            channel: Channel number (1-based).
            current: Current value in amperes.
        """
        pass

    @abstractmethod
    def get_current(self, channel: int) -> float:
        """
        Get load current setting for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Current value in amperes.
        """
        pass

    @abstractmethod
    def set_voltage(self, channel: int, voltage: float):
        """
        Set load voltage for a channel (CV mode).
        
        Args:
            channel: Channel number (1-based).
            voltage: Voltage value in volts.
        """
        pass

    @abstractmethod
    def get_voltage(self, channel: int) -> float:
        """
        Get load voltage setting for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Voltage value in volts.
        """
        pass

    @abstractmethod
    def set_resistance(self, channel: int, resistance: float):
        """
        Set load resistance for a channel (CR mode).
        
        Args:
            channel: Channel number (1-based).
            resistance: Resistance value in ohms.
        """
        pass

    @abstractmethod
    def get_resistance(self, channel: int) -> float:
        """
        Get load resistance setting for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Resistance value in ohms.
        """
        pass

    @abstractmethod
    def set_power(self, channel: int, power: float):
        """
        Set load power for a channel (CP mode).
        
        Args:
            channel: Channel number (1-based).
            power: Power value in watts.
        """
        pass

    @abstractmethod
    def get_power(self, channel: int) -> float:
        """
        Get load power setting for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Power value in watts.
        """
        pass

    @abstractmethod
    def set_mode(self, channel: int, mode: LoadMode):
        """
        Set operating mode for a channel.
        
        Args:
            channel: Channel number (1-based).
            mode: LoadMode enum value (CC, CV, CR, or CP).
        """
        pass

    @abstractmethod
    def get_mode(self, channel: int) -> LoadMode:
        """
        Get operating mode for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            LoadMode enum value.
        """
        pass

    @abstractmethod
    def measure_voltage(self, channel: int) -> float:
        """
        Measure actual input voltage for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Measured voltage in volts.
        """
        pass

    @abstractmethod
    def measure_current(self, channel: int) -> float:
        """
        Measure actual load current for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Measured current in amperes.
        """
        pass

    @abstractmethod
    def measure_power(self, channel: int) -> float:
        """
        Measure actual load power for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Measured power in watts.
        """
        pass

    @abstractmethod
    def set_load(self, channel: int, state: bool):
        """
        Enable or disable load for a channel.
        
        Args:
            channel: Channel number (1-based).
            state: True to enable load, False to disable.
        """
        pass

    @abstractmethod
    def get_load(self, channel: int) -> bool:
        """
        Get load state for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            True if load is enabled, False otherwise.
        """
        pass

    def __enter__(self):
        """Context manager entry."""
        if not self.connection.is_connected():
            self.connection.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Context manager exit."""
        # Connection cleanup is handled by the connection object itself
        pass

"""Power Supply Unit (PSU) abstract base class."""

from abc import ABC, abstractmethod

from ..core.connection import Connection


class PSU(ABC):
    """Abstract base class for power supply units."""

    def __init__(
        self,
        connection: Connection,
        num_channels: int,
        channel_limits: list[dict[str, float]],
    ):
        """
        Initialize PSU with a connection and channel configuration.
        
        Args:
            connection: Connection object to communicate with the PSU.
            num_channels: Number of channels on this PSU.
            channel_limits: Array of channel limits. Each element is a dict with
                'voltage_max' and 'current_max' keys. Index 0 = channel 1, index 1 = channel 2, etc.
        """
        self.connection = connection
        self.num_channels = num_channels
        self.channel_limits = channel_limits
    
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
        
        if channel < 1 or channel > self.num_channels:
            raise ValueError(f"Channel must be between 1 and {self.num_channels}, got {channel}")
        
        channel_index = channel - 1
        voltage_max = self.channel_limits[channel_index]["voltage_max"]
        
        if voltage > voltage_max:
            raise ValueError(
                f"Voltage {voltage}V exceeds maximum for channel {channel} ({voltage_max}V)"
            )
    
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
        
        if channel < 1 or channel > self.num_channels:
            raise ValueError(f"Channel must be between 1 and {self.num_channels}, got {channel}")
        
        channel_index = channel - 1
        current_max = self.channel_limits[channel_index]["current_max"]
        
        if current > current_max:
            raise ValueError(
                f"Current {current}A exceeds maximum for channel {channel} ({current_max}A)"
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
    def set_voltage(self, channel: int, voltage: float):
        """
        Set voltage for a channel.
        
        Args:
            channel: Channel number (1-based).
            voltage: Voltage value in volts.
        """
        pass

    @abstractmethod
    def get_voltage(self, channel: int) -> float:
        """
        Get voltage setting for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Voltage value in volts.
        """
        pass

    @abstractmethod
    def set_current(self, channel: int, current: float):
        """
        Set current limit for a channel.
        
        Args:
            channel: Channel number (1-based).
            current: Current value in amperes.
        """
        pass

    @abstractmethod
    def get_current(self, channel: int) -> float:
        """
        Get current limit setting for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Current value in amperes.
        """
        pass

    @abstractmethod
    def measure_voltage(self, channel: int) -> float:
        """
        Measure actual output voltage for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Measured voltage in volts.
        """
        pass

    @abstractmethod
    def measure_current(self, channel: int) -> float:
        """
        Measure actual output current for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Measured current in amperes.
        """
        pass

    @abstractmethod
    def set_output(self, channel: int, state: bool):
        """
        Enable or disable output for a channel.
        
        Args:
            channel: Channel number (1-based).
            state: True to enable output, False to disable.
        """
        pass

    @abstractmethod
    def get_output(self, channel: int) -> bool:
        """
        Get output state for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            True if output is enabled, False otherwise.
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


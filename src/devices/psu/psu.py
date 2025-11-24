"""Power Supply Unit (PSU) abstract base class."""

from abc import ABC, abstractmethod

from ..core.connection import Connection


class PSU(ABC):
    """Abstract base class for power supply units."""

    def __init__(self, connection: Connection):
        """
        Initialize PSU with a connection.
        
        Args:
            connection: Connection object to communicate with the PSU.
        """
        self.connection = connection

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


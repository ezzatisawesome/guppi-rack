"""OpenHTF plug for PSU instrument control."""

from openhtf.plugs import BasePlug

from instruments.psu.psu import PSU


class PSUPlug(BasePlug):
    """OpenHTF plug that wraps a PSU driver instance.
    
    This plug delegates all operations to the underlying PSU driver.
    The driver is pre-initialized and connected by the server, so
    this plug does not manage the connection lifecycle.
    """

    def __init__(self, driver: PSU, instrument_id: str, instrument_name: str):
        """
        Initialize PSU plug.
        
        Args:
            driver: Pre-initialized PSU driver instance (BK9130, BK9200, etc.)
            instrument_id: Unique identifier for this instrument (e.g., "psu1")
            instrument_name: Human-readable name for this instrument
        """
        super().__init__()
        self.driver = driver
        self.instrument_id = instrument_id
        self.instrument_name = instrument_name

    def tearDown(self):
        """Called automatically by OpenHTF at the end of test execution.
        
        No-op because the server manages the connection lifecycle, not the plug.
        """
        pass

    def set_voltage(self, channel: int, voltage: float):
        """Set voltage for a channel.
        
        Args:
            channel: Channel number (1-based).
            voltage: Voltage value in volts.
        """
        self.driver.set_voltage(channel, voltage)

    def get_voltage(self, channel: int) -> float:
        """Get voltage setting for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Voltage value in volts.
        """
        return self.driver.get_voltage(channel)

    def set_current(self, channel: int, current: float):
        """Set current limit for a channel.
        
        Args:
            channel: Channel number (1-based).
            current: Current value in amperes.
        """
        self.driver.set_current(channel, current)

    def get_current(self, channel: int) -> float:
        """Get current limit setting for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Current value in amperes.
        """
        return self.driver.get_current(channel)

    def measure_voltage(self, channel: int) -> float:
        """Measure actual output voltage for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Measured voltage in volts.
        """
        return self.driver.measure_voltage(channel)

    def measure_current(self, channel: int) -> float:
        """Measure actual output current for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Measured current in amperes.
        """
        return self.driver.measure_current(channel)

    def set_output(self, channel: int, state: bool):
        """Enable or disable output for a channel.
        
        Args:
            channel: Channel number (1-based).
            state: True to enable output, False to disable.
        """
        self.driver.set_output(channel, state)

    def get_output(self, channel: int) -> bool:
        """Get output state for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            True if output is enabled, False otherwise.
        """
        return self.driver.get_output(channel)

    def identify(self) -> str:
        """Query instrument identification.
        
        Returns:
            Identification string from the instrument.
        """
        return self.driver.identify()

    @property
    def num_channels(self) -> int:
        """Get the number of channels on this PSU.
        
        Returns:
            Number of channels.
        """
        return self.driver.num_channels

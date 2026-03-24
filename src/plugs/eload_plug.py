"""OpenHTF plug for Electronic Load instrument control."""

from openhtf.plugs import BasePlug

from instruments.eload.eload import ELoad, LoadMode


class ELoadPlug(BasePlug):
    """OpenHTF plug that wraps an ELoad driver instance.
    
    This plug delegates all operations to the underlying ELoad driver.
    The driver is pre-initialized and connected by the server, so
    this plug does not manage the connection lifecycle.
    """

    def __init__(self, driver: ELoad, instrument_id: str, instrument_name: str):
        """
        Initialize ELoad plug.
        
        Args:
            driver: Pre-initialized ELoad driver instance (Chroma63600, etc.)
            instrument_id: Unique identifier for this instrument (e.g., "eload1")
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

    def set_current(self, channel: int, current: float):
        """Set load current for a channel (CC mode).
        
        Args:
            channel: Channel number (1-based).
            current: Current value in amperes.
        """
        self.driver.set_current(channel, current)

    def get_current(self, channel: int) -> float:
        """Get load current setting for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Current value in amperes.
        """
        return self.driver.get_current(channel)

    def set_voltage(self, channel: int, voltage: float):
        """Set load voltage for a channel (CV mode).
        
        Args:
            channel: Channel number (1-based).
            voltage: Voltage value in volts.
        """
        self.driver.set_voltage(channel, voltage)

    def get_voltage(self, channel: int) -> float:
        """Get load voltage setting for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Voltage value in volts.
        """
        return self.driver.get_voltage(channel)

    def set_resistance(self, channel: int, resistance: float):
        """Set load resistance for a channel (CR mode).
        
        Args:
            channel: Channel number (1-based).
            resistance: Resistance value in ohms.
        """
        self.driver.set_resistance(channel, resistance)

    def get_resistance(self, channel: int) -> float:
        """Get load resistance setting for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Resistance value in ohms.
        """
        return self.driver.get_resistance(channel)

    def set_power(self, channel: int, power: float):
        """Set load power for a channel (CP mode).
        
        Args:
            channel: Channel number (1-based).
            power: Power value in watts.
        """
        self.driver.set_power(channel, power)

    def get_power(self, channel: int) -> float:
        """Get load power setting for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Power value in watts.
        """
        return self.driver.get_power(channel)

    def set_mode(self, channel: int, mode: LoadMode):
        """Set operating mode for a channel.
        
        Args:
            channel: Channel number (1-based).
            mode: LoadMode enum value (CC, CV, CR, or CP).
        """
        self.driver.set_mode(channel, mode)

    def get_mode(self, channel: int) -> LoadMode:
        """Get operating mode for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            LoadMode enum value.
        """
        return self.driver.get_mode(channel)

    def measure_voltage(self, channel: int) -> float:
        """Measure actual input voltage for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Measured voltage in volts.
        """
        return self.driver.measure_voltage(channel)

    def measure_current(self, channel: int) -> float:
        """Measure actual load current for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Measured current in amperes.
        """
        return self.driver.measure_current(channel)

    def measure_power(self, channel: int) -> float:
        """Measure actual load power for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Measured power in watts.
        """
        return self.driver.measure_power(channel)

    def set_load(self, channel: int, state: bool):
        """Enable or disable load for a channel.
        
        Args:
            channel: Channel number (1-based).
            state: True to enable load, False to disable.
        """
        self.driver.set_load(channel, state)

    def get_load(self, channel: int) -> bool:
        """Get load state for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            True if load is enabled, False otherwise.
        """
        return self.driver.get_load(channel)

    def identify(self) -> str:
        """Query instrument identification.
        
        Returns:
            Identification string from the instrument.
        """
        return self.driver.identify()

    @property
    def num_channels(self) -> int:
        """Get the number of channels on this ELoad.
        
        Returns:
            Number of channels.
        """
        return self.driver.num_channels

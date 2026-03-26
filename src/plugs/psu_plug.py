"""OpenHTF plug for PSU instrument control."""

import logging

from openhtf.plugs import BasePlug

from instruments.psu.psu import PSU

logger = logging.getLogger(__name__)


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
        logger.debug(
            "[%s] tearDown called — connection lifecycle managed by server, skipping",
            self.instrument_id,
        )

    def set_voltage(self, channel: int, voltage: float):
        """Set voltage for a channel.
        
        Args:
            channel: Channel number (1-based).
            voltage: Voltage value in volts.
        """
        logger.debug("[%s] set_voltage(channel=%d, voltage=%gV)", self.instrument_id, channel, voltage)
        try:
            self.driver.set_voltage(channel, voltage)
        except Exception as e:
            logger.error(
                "[%s] set_voltage(channel=%d, voltage=%gV) FAILED: %s",
                self.instrument_id, channel, voltage, e, exc_info=True
            )
            raise

    def get_voltage(self, channel: int) -> float:
        """Get voltage setting for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Voltage value in volts.
        """
        logger.debug("[%s] get_voltage(channel=%d)", self.instrument_id, channel)
        try:
            result = self.driver.get_voltage(channel)
            logger.debug("[%s] get_voltage(channel=%d) -> %gV", self.instrument_id, channel, result)
            return result
        except Exception as e:
            logger.error(
                "[%s] get_voltage(channel=%d) FAILED: %s",
                self.instrument_id, channel, e, exc_info=True
            )
            raise

    def set_current(self, channel: int, current: float):
        """Set current limit for a channel.
        
        Args:
            channel: Channel number (1-based).
            current: Current value in amperes.
        """
        logger.debug("[%s] set_current(channel=%d, current=%gA)", self.instrument_id, channel, current)
        try:
            self.driver.set_current(channel, current)
        except Exception as e:
            logger.error(
                "[%s] set_current(channel=%d, current=%gA) FAILED: %s",
                self.instrument_id, channel, current, e, exc_info=True
            )
            raise

    def get_current(self, channel: int) -> float:
        """Get current limit setting for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Current value in amperes.
        """
        logger.debug("[%s] get_current(channel=%d)", self.instrument_id, channel)
        try:
            result = self.driver.get_current(channel)
            logger.debug("[%s] get_current(channel=%d) -> %gA", self.instrument_id, channel, result)
            return result
        except Exception as e:
            logger.error(
                "[%s] get_current(channel=%d) FAILED: %s",
                self.instrument_id, channel, e, exc_info=True
            )
            raise

    def measure_voltage(self, channel: int) -> float:
        """Measure actual output voltage for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Measured voltage in volts.
        """
        logger.debug("[%s] measure_voltage(channel=%d)", self.instrument_id, channel)
        try:
            result = self.driver.measure_voltage(channel)
            logger.debug("[%s] measure_voltage(channel=%d) -> %gV", self.instrument_id, channel, result)
            return result
        except Exception as e:
            logger.error(
                "[%s] measure_voltage(channel=%d) FAILED: %s",
                self.instrument_id, channel, e, exc_info=True
            )
            raise

    def measure_current(self, channel: int) -> float:
        """Measure actual output current for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            Measured current in amperes.
        """
        logger.debug("[%s] measure_current(channel=%d)", self.instrument_id, channel)
        try:
            result = self.driver.measure_current(channel)
            logger.debug("[%s] measure_current(channel=%d) -> %gA", self.instrument_id, channel, result)
            return result
        except Exception as e:
            logger.error(
                "[%s] measure_current(channel=%d) FAILED: %s",
                self.instrument_id, channel, e, exc_info=True
            )
            raise

    def set_output(self, channel: int, state: bool):
        """Enable or disable output for a channel.
        
        Args:
            channel: Channel number (1-based).
            state: True to enable output, False to disable.
        """
        logger.debug(
            "[%s] set_output(channel=%d, state=%s)",
            self.instrument_id, channel, "ON" if state else "OFF",
        )
        try:
            self.driver.set_output(channel, state)
        except Exception as e:
            logger.error(
                "[%s] set_output(channel=%d, state=%s) FAILED: %s",
                self.instrument_id, channel, "ON" if state else "OFF", e, exc_info=True
            )
            raise

    def get_output(self, channel: int) -> bool:
        """Get output state for a channel.
        
        Args:
            channel: Channel number (1-based).
        
        Returns:
            True if output is enabled, False otherwise.
        """
        logger.debug("[%s] get_output(channel=%d)", self.instrument_id, channel)
        try:
            result = self.driver.get_output(channel)
            logger.debug(
                "[%s] get_output(channel=%d) -> %s",
                self.instrument_id, channel, "ON" if result else "OFF",
            )
            return result
        except Exception as e:
            logger.error(
                "[%s] get_output(channel=%d) FAILED: %s",
                self.instrument_id, channel, e, exc_info=True
            )
            raise

    def identify(self) -> str:
        """Query instrument identification.
        
        Returns:
            Identification string from the instrument.
        """
        logger.debug("[%s] identify()", self.instrument_id)
        try:
            result = self.driver.identify()
            logger.info("[%s] identify() -> %r", self.instrument_id, result)
            return result
        except Exception as e:
            logger.error(
                "[%s] identify() FAILED: %s", self.instrument_id, e, exc_info=True
            )
            raise

    @property
    def num_channels(self) -> int:
        """Get the number of channels on this PSU.
        
        Returns:
            Number of channels.
        """
        return self.driver.num_channels

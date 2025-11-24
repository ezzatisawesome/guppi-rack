"""BK Precision 9200 Series Power Supply driver.

Based on BK Precision 9200 Series User Manual.
Supports models: 9200, 9201, 9202, 9205, 9206
"""

from ..core.connection import Connection
from .psu import PSU


class BK9200(PSU):
    """BK Precision 9200 Series Programmable DC Power Supply.

    This driver supports various 9200 series models with different
    channel configurations and power ratings.
    """

    def __init__(self, connection: Connection, num_channels: int = 1):
        """
        Initialize BK9200 power supply.

        Args:
            connection: Connection object (USB TMC, RS-232, or GPIB).
            num_channels: Number of channels (default: 1, can be 1 or 2 for some models).
        """
        super().__init__(connection)
        self._num_channels = num_channels

    def identify(self) -> str:
        """Query instrument identification."""
        return self.connection.query("*IDN?").strip()

    def set_voltage(self, channel: int, voltage: float):
        """
        Set voltage for a channel.

        Args:
            channel: Channel number (1-based, typically 1 or 1-2).
            voltage: Voltage value in volts.
        """
        if channel < 1 or channel > self._num_channels:
            raise ValueError(f"Channel must be between 1 and {self._num_channels}")
        
        if self._num_channels == 1:
            # Single channel: VOLT <value>
            self.connection.write(f"VOLT {voltage:.3f}")
        else:
            # Multi-channel: VOLT <value>,(@<channel>)
            self.connection.write(f"VOLT {voltage:.3f},(@{channel})")

    def get_voltage(self, channel: int) -> float:
        """
        Get voltage setting for a channel.

        Args:
            channel: Channel number (1-based).

        Returns:
            Voltage value in volts.
        """
        if channel < 1 or channel > self._num_channels:
            raise ValueError(f"Channel must be between 1 and {self._num_channels}")
        
        if self._num_channels == 1:
            response = self.connection.query("VOLT?").strip()
        else:
            response = self.connection.query(f"VOLT? (@{channel})").strip()
        return float(response)

    def set_current(self, channel: int, current: float):
        """
        Set current limit for a channel.

        Args:
            channel: Channel number (1-based).
            current: Current value in amperes.
        """
        if channel < 1 or channel > self._num_channels:
            raise ValueError(f"Channel must be between 1 and {self._num_channels}")
        
        if self._num_channels == 1:
            # Single channel: CURR <value>
            self.connection.write(f"CURR {current:.3f}")
        else:
            # Multi-channel: CURR <value>,(@<channel>)
            self.connection.write(f"CURR {current:.3f},(@{channel})")

    def get_current(self, channel: int) -> float:
        """
        Get current limit setting for a channel.

        Args:
            channel: Channel number (1-based).

        Returns:
            Current value in amperes.
        """
        if channel < 1 or channel > self._num_channels:
            raise ValueError(f"Channel must be between 1 and {self._num_channels}")
        
        if self._num_channels == 1:
            response = self.connection.query("CURR?").strip()
        else:
            response = self.connection.query(f"CURR? (@{channel})").strip()
        return float(response)

    def measure_voltage(self, channel: int) -> float:
        """
        Measure actual output voltage for a channel.

        Args:
            channel: Channel number (1-based).

        Returns:
            Measured voltage in volts.
        """
        if channel < 1 or channel > self._num_channels:
            raise ValueError(f"Channel must be between 1 and {self._num_channels}")
        
        if self._num_channels == 1:
            response = self.connection.query("MEAS:VOLT?").strip()
        else:
            response = self.connection.query(f"MEAS:VOLT? (@{channel})").strip()
        return float(response)

    def measure_current(self, channel: int) -> float:
        """
        Measure actual output current for a channel.

        Args:
            channel: Channel number (1-based).

        Returns:
            Measured current in amperes.
        """
        if channel < 1 or channel > self._num_channels:
            raise ValueError(f"Channel must be between 1 and {self._num_channels}")
        
        if self._num_channels == 1:
            response = self.connection.query("MEAS:CURR?").strip()
        else:
            response = self.connection.query(f"MEAS:CURR? (@{channel})").strip()
        return float(response)

    def set_output(self, channel: int, state: bool):
        """
        Enable or disable output for a channel.

        Args:
            channel: Channel number (1-based).
            state: True to enable output, False to disable.
        """
        if channel < 1 or channel > self._num_channels:
            raise ValueError(f"Channel must be between 1 and {self._num_channels}")
        
        state_str = "ON" if state else "OFF"
        
        if self._num_channels == 1:
            # Single channel: OUTP <state>
            self.connection.write(f"OUTP {state_str}")
        else:
            # Multi-channel: OUTP <state>,(@<channel>)
            self.connection.write(f"OUTP {state_str},(@{channel})")

    def get_output(self, channel: int) -> bool:
        """
        Get output state for a channel.

        Args:
            channel: Channel number (1-based).

        Returns:
            True if output is enabled, False otherwise.
        """
        if channel < 1 or channel > self._num_channels:
            raise ValueError(f"Channel must be between 1 and {self._num_channels}")
        
        if self._num_channels == 1:
            response = self.connection.query("OUTP?").strip()
        else:
            response = self.connection.query(f"OUTP? (@{channel})").strip()
        
        return response.upper() in ("1", "ON", "TRUE")

    def reset(self):
        """Reset the instrument to default settings."""
        self.connection.write("*RST")

    def get_status(self) -> dict:
        """
        Get comprehensive status of all channels.

        Returns:
            Dictionary with status information for each channel.
        """
        status = {}
        for ch in range(1, self._num_channels + 1):
            status[f"channel_{ch}"] = {
                "voltage_setting": self.get_voltage(ch),
                "current_setting": self.get_current(ch),
                "voltage_measured": self.measure_voltage(ch),
                "current_measured": self.measure_current(ch),
                "output_enabled": self.get_output(ch),
            }
        return status

    def set_ovp(self, channel: int, voltage: float):
        """
        Set over-voltage protection (OVP) level.

        Args:
            channel: Channel number (1-based).
            voltage: OVP voltage level in volts.
        """
        if channel < 1 or channel > self._num_channels:
            raise ValueError(f"Channel must be between 1 and {self._num_channels}")
        
        if self._num_channels == 1:
            self.connection.write(f"VOLT:PROT {voltage:.3f}")
        else:
            self.connection.write(f"VOLT:PROT {voltage:.3f},(@{channel})")

    def get_ovp(self, channel: int) -> float:
        """
        Get over-voltage protection (OVP) level.

        Args:
            channel: Channel number (1-based).

        Returns:
            OVP voltage level in volts.
        """
        if channel < 1 or channel > self._num_channels:
            raise ValueError(f"Channel must be between 1 and {self._num_channels}")
        
        if self._num_channels == 1:
            response = self.connection.query("VOLT:PROT?").strip()
        else:
            response = self.connection.query(f"VOLT:PROT? (@{channel})").strip()
        return float(response)

    def set_ocp(self, channel: int, current: float):
        """
        Set over-current protection (OCP) level.

        Args:
            channel: Channel number (1-based).
            current: OCP current level in amperes.
        """
        if channel < 1 or channel > self._num_channels:
            raise ValueError(f"Channel must be between 1 and {self._num_channels}")
        
        if self._num_channels == 1:
            self.connection.write(f"CURR:PROT {current:.3f}")
        else:
            self.connection.write(f"CURR:PROT {current:.3f},(@{channel})")

    def get_ocp(self, channel: int) -> float:
        """
        Get over-current protection (OCP) level.

        Args:
            channel: Channel number (1-based).

        Returns:
            OCP current level in amperes.
        """
        if channel < 1 or channel > self._num_channels:
            raise ValueError(f"Channel must be between 1 and {self._num_channels}")
        
        if self._num_channels == 1:
            response = self.connection.query("CURR:PROT?").strip()
        else:
            response = self.connection.query(f"CURR:PROT? (@{channel})").strip()
        return float(response)


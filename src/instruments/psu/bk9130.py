"""BK Precision 9130C Series Power Supply driver.

Based on BK Precision 9130C Series User Manual.
Supports models: 9130C, 9131C, 9132C
"""

from ..core.connection import Connection
from .psu import PSU


class BK9130(PSU):
    """BK Precision 9130C Series Triple Output Programmable DC Power Supply.

    This driver supports the 9130C, 9131C, and 9132C models.
    These are triple output power supplies with:
    - Channel 1 and 2: Variable voltage/current
    - Channel 3: Fixed or variable voltage/current (model dependent)
    """

    def __init__(self, connection: Connection):
        """
        Initialize BK9130 power supply.

        Args:
            connection: Connection object (USB TMC or RS-232).
        """
        # BK9130 has 3 channels:
        # Channel 1 & 2: 30V/3A variable
        # Channel 3: 5V/3A (fixed or variable depending on model)
        channel_limits = [
            {"voltage_max": 30.0, "current_max": 6.0},  # Channel 1
            {"voltage_max": 30.0, "current_max": 6.0},  # Channel 2
            {"voltage_max": 5.0, "current_max": 3.0},   # Channel 3
        ]
        super().__init__(connection, num_channels=3, channel_limits=channel_limits)
        self._num_channels = 3

    def identify(self) -> str:
        """Query instrument identification."""
        return self.connection.query("*IDN?").strip()

    def _select_channel(self, channel: int):
        """Select a channel for subsequent commands."""
        self.connection.write(f"INST:NSEL {channel}")

    def set_voltage(self, channel: int, voltage: float):
        """
        Set voltage for a channel.

        Args:
            channel: Channel number (1, 2, or 3).
            voltage: Voltage value in volts.
        """
        if channel < 1 or channel > self._num_channels:
            raise ValueError(f"Channel must be between 1 and {self._num_channels}")
        
        # Validate against channel limits
        self._validate_voltage(channel, voltage)
        
        # Select channel first, then set voltage
        self._select_channel(channel)
        self.connection.write(f"VOLT {voltage:.3f}")

    def get_voltage(self, channel: int) -> float:
        """
        Get voltage setting for a channel.

        Args:
            channel: Channel number (1, 2, or 3).

        Returns:
            Voltage value in volts.
        """
        if channel < 1 or channel > self._num_channels:
            raise ValueError(f"Channel must be between 1 and {self._num_channels}")
        
        # Select channel first, then query voltage
        self._select_channel(channel)
        response = self.connection.query("VOLT?").strip()
        return float(response)

    def set_current(self, channel: int, current: float):
        """
        Set current limit for a channel.

        Args:
            channel: Channel number (1, 2, or 3).
            current: Current value in amperes.
        """
        if channel < 1 or channel > self._num_channels:
            raise ValueError(f"Channel must be between 1 and {self._num_channels}")
        
        # Validate against channel limits
        self._validate_current(channel, current)
        
        # Select channel first, then set current
        self._select_channel(channel)
        self.connection.write(f"CURR {current:.3f}")

    def get_current(self, channel: int) -> float:
        """
        Get current limit setting for a channel.

        Args:
            channel: Channel number (1, 2, or 3).

        Returns:
            Current value in amperes.
        """
        if channel < 1 or channel > self._num_channels:
            raise ValueError(f"Channel must be between 1 and {self._num_channels}")
        
        # Select channel first, then query current
        self._select_channel(channel)
        response = self.connection.query("CURR?").strip()
        return float(response)

    def measure_voltage(self, channel: int) -> float:
        """
        Measure actual output voltage for a channel.

        Args:
            channel: Channel number (1, 2, or 3).

        Returns:
            Measured voltage in volts.
        """
        if channel < 1 or channel > self._num_channels:
            raise ValueError(f"Channel must be between 1 and {self._num_channels}")
        
        # Select channel first, then measure voltage
        self._select_channel(channel)
        response = self.connection.query("MEAS:VOLT?").strip()
        return float(response)

    def measure_current(self, channel: int) -> float:
        """
        Measure actual output current for a channel.

        Args:
            channel: Channel number (1, 2, or 3).

        Returns:
            Measured current in amperes.
        """
        if channel < 1 or channel > self._num_channels:
            raise ValueError(f"Channel must be between 1 and {self._num_channels}")
        
        # Select channel first, then measure current
        self._select_channel(channel)
        response = self.connection.query("MEAS:CURR?").strip()
        return float(response)

    def set_output(self, channel: int, state: bool):
        """
        Enable or disable output for a channel.

        Args:
            channel: Channel number (1, 2, or 3).
            state: True to enable output, False to disable.
        """
        if channel < 1 or channel > self._num_channels:
            raise ValueError(f"Channel must be between 1 and {self._num_channels}")
        
        # Select channel first, then set output
        self._select_channel(channel)
        state_str = "ON" if state else "OFF"
        self.connection.write(f"OUTP {state_str}")

    def get_output(self, channel: int) -> bool:
        """
        Get output state for a channel.

        Args:
            channel: Channel number (1, 2, or 3).

        Returns:
            True if output is enabled, False otherwise.
        """
        if channel < 1 or channel > self._num_channels:
            raise ValueError(f"Channel must be between 1 and {self._num_channels}")
        
        # Select channel first, then query output state
        self._select_channel(channel)
        response = self.connection.query("OUTP?").strip()
        return response.upper() in ("1", "ON", "TRUE")

    def set_all_outputs(self, state: bool):
        """
        Enable or disable all outputs simultaneously.

        Args:
            state: True to enable all outputs, False to disable all.
        """
        # Set each channel individually
        for ch in range(1, self._num_channels + 1):
            self.set_output(ch, state)

    def get_all_outputs(self) -> list[bool]:
        """
        Get output state for all channels.

        Returns:
            List of output states for channels 1, 2, and 3.
        """
        return [self.get_output(ch) for ch in range(1, self._num_channels + 1)]

    def recall_memory(self, group: int, location: int):
        """
        Recall a stored memory setting.

        Args:
            group: Memory group number (1-4).
            location: Memory location number (1-9).
        """
        if group < 1 or group > 4:
            raise ValueError("Group must be between 1 and 4")
        if location < 1 or location > 9:
            raise ValueError("Location must be between 1 and 9")
        
        self.connection.write(f"*RCL {group},{location}")

    def save_memory(self, group: int, location: int):
        """
        Save current settings to memory.

        Args:
            group: Memory group number (1-4).
            location: Memory location number (1-9).
        """
        if group < 1 or group > 4:
            raise ValueError("Group must be between 1 and 4")
        if location < 1 or location > 9:
            raise ValueError("Location must be between 1 and 9")
        
        self.connection.write(f"*SAV {group},{location}")

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


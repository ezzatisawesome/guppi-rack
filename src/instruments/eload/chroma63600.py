"""Chroma 63600 Series Electronic Load driver."""

from __future__ import annotations

from ..core.connection import Connection
from .eload import ELoad, LoadMode


class Chroma63600(ELoad):
    """Chroma 63600 Series Programmable DC Electronic Load."""

    def __init__(
        self,
        connection: Connection,
        num_channels: int = 1,
        channel_limits: list[dict[str, float]] | None = None,
        channel_map: dict[int, int] | None = None,
        # channel_map maps logical channel -> physical SCPI channel number
        # Example for your chassis: {1: 1, 2: 3}
        auto_discover_channels: bool = True,
    ):
        if channel_limits is None:
            channel_limits = [
                {"voltage_max": 150.0, "current_max": 30.0, "power_max": 300.0, "resistance_min": 0.0}
                for _ in range(num_channels)
            ]
        else:
            if len(channel_limits) != num_channels:
                raise ValueError(f"channel_limits must have {num_channels} entries")
            for limits in channel_limits:
                if "resistance_min" not in limits:
                    limits["resistance_min"] = 0.0

        super().__init__(connection, num_channels=num_channels, channel_limits=channel_limits)
        self._num_channels = num_channels

        self._set_values = {
            "current": [0.0] * num_channels,
            "voltage": [0.0] * num_channels,
            "resistance": [0.0] * num_channels,
            "power": [0.0] * num_channels,
            "mode": [LoadMode.CC] * num_channels,
        }

        # --- channel mapping ---
        if channel_map is not None:
            # validate map
            for лог, phys in channel_map.items():
                if not (1 <= лог <= num_channels):
                    raise ValueError(f"channel_map has invalid logical channel {лог}")
                if phys < 1:
                    raise ValueError(f"channel_map has invalid physical channel {phys}")
            self._channel_map = dict(channel_map)
        else:
            # Default: identity mapping; optionally discover real physical IDs.
            self._channel_map = {i: i for i in range(1, num_channels + 1)}
            self._auto_discover_channels = auto_discover_channels
            self._channel_map_discovered = False

    def identify(self) -> str:
        return self.connection.query("*IDN?").strip()
    
    def __enter__(self):
        """Context manager entry - establish connection and discover channels if needed."""
        result = super().__enter__()
        # Discover channels now that connection is established
        if self._auto_discover_channels and not self._channel_map_discovered and self._num_channels > 1:
            if self.connection.is_connected():
                try:
                    self._channel_map = self._discover_channel_map(self._num_channels)
                    self._channel_map_discovered = True
                except Exception:
                    # If discovery fails, keep identity mapping
                    pass
        return result

    # ---------- low-level SCPI helpers ----------

    def _drain_errors(self, max_reads: int = 20) -> list[str]:
        """Drain the instrument error queue and return all errors read."""
        errs: list[str] = []
        for _ in range(max_reads):
            e = self.connection.query("SYST:ERR?").strip()
            errs.append(e)
            if e.startswith("0,"):
                break
        return errs

    def _select_channel(self, channel: int):
        """Select logical channel -> physical SCPI channel using 'CHAN <n>'."""
        if channel < 1 or channel > self._num_channels:
            raise ValueError(f"Channel must be between 1 and {self._num_channels}, got {channel}")

        phys = self._channel_map.get(channel)
        if phys is None:
            raise ValueError(f"No physical mapping for logical channel {channel}")

        # Clear prior errors so we can attribute errors to this select
        self._drain_errors()

        self.connection.write(f"CHAN {phys}")
        err = self.connection.query("SYST:ERR?").strip()
        if not err.startswith("0,"):
            raise RuntimeError(
                f"Failed to select logical channel {channel} (phys CHAN {phys}): {err}. "
                f"Fix channel_map or chassis config."
            )

    def _send_command(self, channel: int, command: str):
        self._select_channel(channel)
        self.connection.write(command)
        err = self.connection.query("SYST:ERR?").strip()
        if not err.startswith("0,"):
            raise RuntimeError(f"SCPI error after '{command}' on ch{channel}: {err}")

    def _query_command(self, channel: int, command: str) -> str:
        self._select_channel(channel)
        resp = self.connection.query(command).strip()
        err = self.connection.query("SYST:ERR?").strip()
        if not err.startswith("0,"):
            raise RuntimeError(f"SCPI error after '{command}' on ch{channel}: {err}")
        return resp

    def _discover_channel_map(self, logical_count: int) -> dict[int, int]:
        """
        Discover which physical CHAN IDs exist, then map them to logical 1..N in order.
        Your chassis example will discover [1,3] and map {1:1, 2:3}.
        """
        existing: list[int] = []
        for phys in range(1, 9):  # scan a little wider; cheap and safe
            self._drain_errors()
            self.connection.write(f"CHAN {phys}")
            err = self.connection.query("SYST:ERR?").strip()
            if err.startswith("0,"):
                existing.append(phys)

        if len(existing) < logical_count:
            raise RuntimeError(
                f"Expected at least {logical_count} channels, discovered only {existing}. "
                f"Check installed modules / chassis configuration."
            )

        existing = existing[:logical_count]
        return {i + 1: existing[i] for i in range(logical_count)}

    # ---------- public API ----------

    def set_current(self, channel: int, current: float):
        self._validate_current(channel, current)
        if self._set_values["mode"][channel - 1] != LoadMode.CC:
            self.set_mode(channel, LoadMode.CC)

        # 63600 uses static level setpoints for CC
        self._send_command(channel, f"CURR:STAT:L1 {current:.6f}")
        self._set_values["current"][channel - 1] = current

    def get_current(self, channel: int) -> float:
        self._validate_channel(channel)
        return self._set_values["current"][channel - 1]

    def set_voltage(self, channel: int, voltage: float):
        self._validate_voltage(channel, voltage)
        if self._set_values["mode"][channel - 1] != LoadMode.CV:
            self.set_mode(channel, LoadMode.CV)

        self._send_command(channel, f"VOLT:STAT:L1 {voltage:.6f}")
        self._set_values["voltage"][channel - 1] = voltage

    def get_voltage(self, channel: int) -> float:
        self._validate_channel(channel)
        return self._set_values["voltage"][channel - 1]

    def set_resistance(self, channel: int, resistance: float):
        self._validate_resistance(channel, resistance)
        if self._set_values["mode"][channel - 1] != LoadMode.CR:
            self.set_mode(channel, LoadMode.CR)

        self._send_command(channel, f"RES:STAT:L1 {resistance:.6f}")
        self._set_values["resistance"][channel - 1] = resistance

    def get_resistance(self, channel: int) -> float:
        self._validate_channel(channel)
        return self._set_values["resistance"][channel - 1]

    def set_power(self, channel: int, power: float):
        self._validate_power(channel, power)
        if self._set_values["mode"][channel - 1] != LoadMode.CP:
            self.set_mode(channel, LoadMode.CP)

        self._send_command(channel, f"POW:STAT:L1 {power:.6f}")
        self._set_values["power"][channel - 1] = power

    def get_power(self, channel: int) -> float:
        self._validate_channel(channel)
        return self._set_values["power"][channel - 1]

    def set_mode(self, channel: int, mode: LoadMode):
        self._validate_channel(channel)
        mode_str = f"{mode.value}H"
        self._send_command(channel, f"MODE {mode_str}")
        self._set_values["mode"][channel - 1] = mode

    def get_mode(self, channel: int) -> LoadMode:
        self._validate_channel(channel)
        response = self._query_command(channel, "MODE?").upper()
        if response.startswith("CC"):
            mode = LoadMode.CC
        elif response.startswith("CV"):
            mode = LoadMode.CV
        elif response.startswith("CR"):
            mode = LoadMode.CR
        elif response.startswith("CP"):
            mode = LoadMode.CP
        else:
            mode = self._set_values["mode"][channel - 1]
        self._set_values["mode"][channel - 1] = mode
        return mode

    def measure_voltage(self, channel: int) -> float:
        self._validate_channel(channel)
        return float(self._query_command(channel, "MEAS:VOLT?"))

    def measure_current(self, channel: int) -> float:
        self._validate_channel(channel)
        return float(self._query_command(channel, "MEAS:CURR?"))

    def measure_power(self, channel: int) -> float:
        self._validate_channel(channel)
        return float(self._query_command(channel, "MEAS:POW?"))

    def set_load(self, channel: int, state: bool):
        self._validate_channel(channel)
        self._send_command(channel, f"LOAD {'ON' if state else 'OFF'}")

    def get_load(self, channel: int) -> bool:
        self._validate_channel(channel)
        return self._query_command(channel, "LOAD?").upper() in ("1", "ON", "TRUE")

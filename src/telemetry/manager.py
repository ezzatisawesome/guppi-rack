"""Telemetry manager for collecting and streaming instrument measurements.

Runs a single background thread that reads instrument signals, updates
an in-memory latest-values cache (for the REST /telemetry/latest endpoint),
and publishes each measurement to MQTT for real-time browser streaming.

All database persistence is handled externally by guppi-agent's
MqttIngestWorker — this service does NOT write to Postgres.
"""

import logging
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional, TYPE_CHECKING

from .models import Measurement, SignalConfig

if TYPE_CHECKING:
    from .mqtt_publisher import MqttPublisher

logger = logging.getLogger(__name__)


class TelemetryManager:
    """Manages telemetry collection and MQTT publishing.
    
    Runs a single background thread that reads instrument signals,
    updates an in-memory cache, and publishes to MQTT.
    """
    
    def __init__(
        self,
        rig_config: Dict[str, Any],
        measurement_interval: float = 1.0,
        get_test_id: Optional[Callable[[], Optional[str]]] = None,
        mqtt_publisher: Optional["MqttPublisher"] = None,
    ):
        """
        Initialize telemetry manager.
        
        Args:
            rig_config: Configuration dict containing:
                - 'instruments': List of instrument configs with:
                  - 'id': Unique instrument ID
                  - 'name': Instrument name
                  - 'driver': Instrument driver instance (with ThreadSafeConnection)
                  - 'signals': List of SignalConfig objects
            measurement_interval: Time between measurements in seconds (default: 1.0).
            get_test_id: Optional callback returning the current test execution ID.
                Used to tag MQTT meta channels with the active test.
            mqtt_publisher: Optional MqttPublisher for real-time streaming.
                If provided, every measurement is published to MQTT immediately.
        """
        self.rig_config = rig_config
        self.measurement_interval = measurement_interval
        self._get_test_id = get_test_id
        self._mqtt_publisher = mqtt_publisher
        
        # Thread control
        self._stop_event = threading.Event()
        self._measurement_thread: Optional[threading.Thread] = None
        
        # Statistics
        self._measurements_produced = 0
        self._stats_lock = threading.Lock()
        
        # Latest values dict for direct REST polling (bypasses Supabase)
        self._latest_values: Dict[str, Dict[str, Any]] = {}
        self._latest_values_lock = threading.Lock()

    def _current_test_id(self) -> Optional[str]:
        """Get the current test execution id, if any."""
        if self._get_test_id is None:
            return None
        try:
            return self._get_test_id()
        except Exception as e:
            logger.error(f"Error getting current test id: {e}", exc_info=True)
            return None
    
    def start(self):
        """Start the measurement thread."""
        if self._measurement_thread is not None and self._measurement_thread.is_alive():
            logger.warning("Telemetry manager already running")
            return
        
        logger.info("Starting telemetry manager...")
        self._stop_event.clear()
        
        # Start measurement thread
        self._measurement_thread = threading.Thread(
            target=self._measurement_loop,
            name="TelemetryMeasurement",
            daemon=True
        )
        self._measurement_thread.start()
        
        logger.info("Telemetry manager started")
    
    def stop(self, timeout: float = 5.0):
        """Stop the measurement thread.
        
        Args:
            timeout: Maximum time to wait for the thread to stop (seconds).
        """
        if self._measurement_thread is None or not self._measurement_thread.is_alive():
            logger.info("Telemetry manager not running")
            return
        
        logger.info("Stopping telemetry manager...")
        self._stop_event.set()
        
        # Wait for thread to finish
        if self._measurement_thread is not None and self._measurement_thread.is_alive():
            self._measurement_thread.join(timeout=timeout)
            if self._measurement_thread.is_alive():
                logger.warning("Measurement thread did not stop in time (likely blocked on instrument read)")
        
        logger.info("Telemetry manager stopped")
    
    def _measurement_loop(self):
        """Main loop for measurement thread.
        
        Reads configured signals from instruments, updates the in-memory
        latest-values cache, and publishes to MQTT.
        """
        logger.info("Measurement thread started")
        
        # Dictionary to track last print time for throttling terminal output
        self._last_print_time = {}
        
        instruments = self.rig_config.get("instruments", [])
        rig_id = self.rig_config.get("rig_id")
        
        if not instruments:
            logger.warning("No instruments configured for telemetry")
            return
        
        if not rig_id:
            logger.error("Rig ID not found in configuration")
            return
        
        while not self._stop_event.is_set():
            try:
                dt = datetime.now()
                execution_id = self._current_test_id()
                
                # Measure all configured signals
                for instrument_config in instruments:
                    instrument_id = instrument_config["id"]
                    instrument_name = instrument_config["name"]
                    driver = instrument_config["driver"]
                    signals = instrument_config.get("signals", [])
                    
                    for signal_config in signals:
                        try:
                            # Read measurement from instrument
                            value = self._read_signal(driver, signal_config)
                            
                            with self._stats_lock:
                                self._measurements_produced += 1
                            
                            # Update latest values for direct polling
                            with self._latest_values_lock:
                                self._latest_values[signal_config.path] = {
                                    "value": value,
                                    "unit": signal_config.unit,
                                    "instrument_id": instrument_id,
                                    "timestamp": dt.isoformat(),
                                }
                            
                            # Publish to MQTT for real-time browser streaming.
                            # Topic: {rig_id}/{instrument_id}/{metric}
                            # Metric is derived from the flat path by stripping
                            # the instrument_id prefix (e.g. "psu1.voltage" → "voltage").
                            if self._mqtt_publisher is not None:
                                prefix = f"{instrument_id}."
                                metric = signal_config.path.removeprefix(prefix)
                                self._mqtt_publisher.publish_measurement(
                                    instrument_id=instrument_id,
                                    metric=metric,
                                    value=value,
                                )
                            
                            # Print to terminal for debugging
                            if signal_config.signal_type in ["voltage", "current"]:
                                current_time = time.time()
                                key = f"{instrument_name}_{signal_config.channel}_{signal_config.signal_type}"
                                if current_time - self._last_print_time.get(key, 0) >= 1.0:
                                    print(f"[{dt.strftime('%H:%M:%S')}] {instrument_name} Ch {signal_config.channel} {signal_config.signal_type.capitalize()}: {value:.3f} {signal_config.unit}")
                                    self._last_print_time[key] = current_time
                            
                            
                        except Exception as e:
                            logger.error(
                                f"Error measuring {signal_config.signal_type} "
                                f"on {instrument_name} channel {signal_config.channel}: {e}",
                                exc_info=True
                            )

                # Also publish meta telemetry for test status as dedicated MQTT channels
                is_running_value = 1.0 if execution_id is not None else 0.0

                if self._mqtt_publisher is not None:
                    self._mqtt_publisher.publish_measurement(
                        instrument_id="system",
                        metric="test_running",
                        value=is_running_value,
                    )

                # Update latest values for meta channels
                with self._latest_values_lock:
                    self._latest_values["system.test_running"] = {
                        "value": is_running_value,
                        "unit": "bool",
                        "instrument_id": "system",
                        "timestamp": dt.isoformat(),
                    }
                
                # Sleep until next measurement interval
                self._stop_event.wait(self.measurement_interval)
                
            except Exception as e:
                logger.error(f"Error in measurement loop: {e}", exc_info=True)
                # Continue running even if there's an error
                self._stop_event.wait(self.measurement_interval)
        
        logger.info("Measurement thread stopped")
    
    def _read_signal(self, driver: Any, signal_config: SignalConfig) -> float:
        """Read a signal value from an instrument driver.
        
        Args:
            driver: Instrument driver instance (must have measure_voltage/measure_current methods).
            signal_config: Signal configuration.
        
        Returns:
            Measured value.
        """
        if signal_config.signal_type == "voltage":
            return driver.measure_voltage(signal_config.channel)
        elif signal_config.signal_type == "current":
            return driver.measure_current(signal_config.channel)
        else:
            raise ValueError(f"Unknown signal type: {signal_config.signal_type}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get telemetry statistics.
        
        Returns:
            Dictionary with statistics:
            - measurements_produced: Total measurements read from instruments
            - mqtt_connected: Whether the MQTT publisher is connected
        """
        with self._stats_lock:
            stats: Dict[str, Any] = {
                "measurements_produced": self._measurements_produced,
            }
        
        # Add MQTT connection status if publisher is available
        if self._mqtt_publisher is not None:
            stats["mqtt_connected"] = self._mqtt_publisher._connected
        else:
            stats["mqtt_connected"] = False
        
        return stats

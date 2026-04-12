"""Telemetry manager for collecting and uploading instrument measurements."""

import logging
import threading
import time
from datetime import datetime
from queue import Empty, Full, Queue
from typing import Any, Callable, Optional

from psycopg2.extras import execute_values

from .models import Measurement, SignalConfig

logger = logging.getLogger(__name__)


class TelemetryManager:
    """Manages telemetry collection and upload to PostgreSQL.
    
    Runs two background threads:
    1. Measurement thread: Reads instrument signals and enqueues measurements
    2. Uploader thread: Batches measurements and uploads to PostgreSQL
    """
    
    def __init__(
        self,
        rig_config: dict[str, Any],
        db_connection_pool: Any,
        measurement_interval: float = 1.0,
        batch_size: int = 100,
        queue_maxsize: int = 10000,
        queue_behavior: str = "drop_oldest",
        table_name: str = "telemetry",
        get_should_save_data: Optional[Callable[[], bool]] = None,
        get_test_id: Optional[Callable[[], Optional[str]]] = None,
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
            db_connection_pool: PostgreSQL connection pool (psycopg2.pool.ThreadedConnectionPool).
            measurement_interval: Time between measurements in seconds (default: 1.0).
            batch_size: Number of measurements to batch before uploading (default: 100).
            queue_maxsize: Maximum size of the measurement queue (default: 10000).
            queue_behavior: Behavior when queue is full:
                - 'drop_oldest': Remove oldest item and add new (default)
                - 'drop_new': Skip new measurement
                - 'block': Block until space available
            table_name: Name of the database table (default: 'telemetry').
        """
        self.rig_config = rig_config
        self.db_connection_pool = db_connection_pool
        self.table_name = table_name
        self.measurement_interval = measurement_interval
        self.batch_size = batch_size
        self.queue_maxsize = queue_maxsize
        self.queue_behavior = queue_behavior
        self._get_should_save_data = get_should_save_data
        self._get_test_id = get_test_id
        
        # Bounded queue for measurements
        self.queue: Queue[Measurement] = Queue(maxsize=queue_maxsize)
        
        # Thread control
        self._stop_event = threading.Event()
        self._measurement_thread: Optional[threading.Thread] = None
        self._uploader_thread: Optional[threading.Thread] = None
        
        # Statistics
        self._measurements_produced = 0
        self._measurements_uploaded = 0
        self._measurements_dropped = 0
        self._upload_errors = 0
        self._stats_lock = threading.Lock()

    def _should_save_data(self) -> bool:
        """Determine whether measurements should currently be saved."""
        if self._get_should_save_data is None:
            return True
        try:
            return bool(self._get_should_save_data())
        except Exception as e:
            logger.error(f"Error evaluating should_save_data: {e}", exc_info=True)
            return False

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
        """Start the measurement and uploader threads."""
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
        
        # Start uploader thread
        self._uploader_thread = threading.Thread(
            target=self._uploader_loop,
            name="TelemetryUploader",
            daemon=True
        )
        self._uploader_thread.start()
        
        logger.info("Telemetry manager started")
    
    def stop(self, timeout: float = 5.0):
        """Stop the measurement and uploader threads.
        
        Args:
            timeout: Maximum time to wait for threads to stop (seconds).
        """
        if self._measurement_thread is None or not self._measurement_thread.is_alive():
            logger.info("Telemetry manager not running")
            return
        
        logger.info("Stopping telemetry manager...")
        self._stop_event.set()
        
        # Wait for threads to finish
        if self._measurement_thread is not None and self._measurement_thread.is_alive():
            self._measurement_thread.join(timeout=timeout / 2)
            if self._measurement_thread.is_alive():
                logger.warning("Measurement thread did not stop in time (likely blocked on instrument read)")
        
        if self._uploader_thread is not None and self._uploader_thread.is_alive():
            self._uploader_thread.join(timeout=timeout / 2)
            if self._uploader_thread.is_alive():
                logger.warning("Uploader thread did not stop in time")
        
        logger.info("Telemetry manager stopped")
    
    def _measurement_loop(self):
        """Main loop for measurement thread.
        
        Reads configured signals from instruments and enqueues measurements.
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
                save_data = self._should_save_data()
                
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
                            
                            # Only enqueue if we should be saving data
                            if save_data:
                                # Create measurement object with flat path
                                # Phase 23 (D-10): Use the signal config's flat path and unit
                                measurement = Measurement(
                                    recorded_at=dt,
                                    rig_id=rig_id,
                                    instrument_id=instrument_id,
                                    instrument_name=instrument_name,
                                    path=signal_config.path,
                                    value=value,
                                    unit=signal_config.unit,
                                    execution_id=execution_id,
                                )
                                
                                # Enqueue measurement
                                self._enqueue_measurement(measurement)
                            
                            # Print to terminal for debugging
                            if signal_config.signal_type in ["voltage", "current"]:
                                current_time = time.time()
                                key = f"{instrument_name}_{signal_config.channel}_{signal_config.signal_type}"
                                if current_time - self._last_print_time.get(key, 0) >= 1.0:
                                    save_tag = " [SAVING]" if save_data else ""
                                    print(f"[{dt.strftime('%H:%M:%S')}] {instrument_name} Ch {signal_config.channel} {signal_config.signal_type.capitalize()}: {value:.3f} {signal_config.unit}{save_tag}")
                                    self._last_print_time[key] = current_time
                            
                            
                        except Exception as e:
                            logger.error(
                                f"Error measuring {signal_config.signal_type} "
                                f"on {instrument_name} channel {signal_config.channel}: {e}",
                                exc_info=True
                            )

                # Also record meta telemetry for test status as dedicated channels
                if save_data:
                    is_running_value = 1.0 if execution_id is not None else 0.0
                    meta_instrument_id = "system"
                    meta_instrument_name = "System"

                    # Channel indicating whether a test is currently running (1.0 or 0.0)
                    test_running_measurement = Measurement(
                        recorded_at=dt,
                        rig_id=rig_id,
                        instrument_id=meta_instrument_id,
                        instrument_name=meta_instrument_name,
                        path="system.test_running",
                        value=is_running_value,
                        unit="bool",
                        execution_id=execution_id,
                    )
                    self._enqueue_measurement(test_running_measurement)

                    # Channel carrying the test id via the execution_id column; only when a test is running
                    if execution_id is not None:
                        test_id_measurement = Measurement(
                            recorded_at=dt,
                            rig_id=rig_id,
                            instrument_id=meta_instrument_id,
                            instrument_name=meta_instrument_name,
                            path="system.test_id",
                            value=0.0,
                            unit="id",
                            execution_id=execution_id,
                        )
                        self._enqueue_measurement(test_id_measurement)
                
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
    
    def _enqueue_measurement(self, measurement: Measurement):
        """Enqueue a measurement, handling queue full scenarios.
        
        Args:
            measurement: Measurement to enqueue.
        """
        try:
            if self.queue_behavior == "drop_oldest":
                # Try to put, but if full, remove oldest and add new
                try:
                    self.queue.put_nowait(measurement)
                except Full:
                    try:
                        # Remove oldest
                        self.queue.get_nowait()
                        # Add new
                        self.queue.put_nowait(measurement)
                        with self._stats_lock:
                            self._measurements_dropped += 1
                    except Exception:
                        # If we can't remove oldest, just drop the new one
                        with self._stats_lock:
                            self._measurements_dropped += 1
                else:
                    with self._stats_lock:
                        self._measurements_produced += 1
            
            elif self.queue_behavior == "drop_new":
                # Try to put, but if full, drop the new measurement
                try:
                    self.queue.put_nowait(measurement)
                    with self._stats_lock:
                        self._measurements_produced += 1
                except Full:
                    with self._stats_lock:
                        self._measurements_dropped += 1
            
            elif self.queue_behavior == "block":
                # Block until space is available (with timeout)
                try:
                    self.queue.put(measurement, timeout=1.0)
                    with self._stats_lock:
                        self._measurements_produced += 1
                except:
                    # Timeout - drop the measurement
                    with self._stats_lock:
                        self._measurements_dropped += 1
            
            else:
                raise ValueError(f"Unknown queue behavior: {self.queue_behavior}")
                
        except Exception as e:
            logger.error(f"Error enqueueing measurement: {e}", exc_info=True)
    
    def _uploader_loop(self):
        """Main loop for uploader thread.
        
        Consumes measurements from queue, batches them, and uploads to Supabase.
        """
        logger.info("Uploader thread started")
        
        batch: list[Measurement] = []
        
        while not self._stop_event.is_set():
            try:
                # Try to get a measurement (with timeout to allow checking stop event)
                # Wait up to 0.5s for an item
                try:
                    measurement = self.queue.get(timeout=0.5)
                    batch.append(measurement)
                except Empty:
                    pass
                
                # Quickly drain any other items already in the queue, up to batch_size
                while len(batch) < self.batch_size:
                    try:
                        measurement = self.queue.get_nowait()
                        batch.append(measurement)
                    except Empty:
                        break
                
                # Upload whatever we collected
                if batch:
                    self._upload_batch(batch)
                    batch = []
                    
            except Exception as e:
                logger.error(f"Error in uploader loop: {e}", exc_info=True)
                # Continue running even if there's an error
        
        # Upload any remaining measurements
        if batch:
            self._upload_batch(batch)
        
        logger.info("Uploader thread stopped")
    
    def _upload_batch(self, batch: list[Measurement]):
        """Upload a batch of measurements to PostgreSQL.
        
        Args:
            batch: List of measurements to upload.
        """
        if not batch:
            return
        
        max_retries = 3
        retry_delay = 1.0
        connection = None
        
        for attempt in range(max_retries):
            connection = None
            cursor = None
            try:
                # Get connection from pool
                t_start = time.time()
                connection = self.db_connection_pool.getconn()
                cursor = connection.cursor()
                
                # Prepare batch insert query using execute_values for bulk INSERT
                # Phase 23 (D-10): Use flat path column instead of signal_type/channel
                insert_query = f"""
                    INSERT INTO {self.table_name} 
                    (recorded_at, rig_id, instrument_id, instrument_name, path, value, unit, execution_id)
                    VALUES %s
                """
                
                # Convert measurements to tuples for batch insert
                records = [
                    (
                        m.recorded_at,
                        m.rig_id,
                        m.instrument_id,
                        m.instrument_name,
                        m.path,
                        m.value,
                        m.unit,
                        m.execution_id,
                    )
                    for m in batch
                ]
                
                # execute_values sends a single INSERT with all rows — 
                # dramatically faster than executemany which sends N round-trips
                execute_values(cursor, insert_query, records, page_size=len(records))
                connection.commit()
                
                elapsed_ms = (time.time() - t_start) * 1000
                
                # Success
                with self._stats_lock:
                    self._measurements_uploaded += len(batch)
                
                logger.info(f"Uploaded {len(batch)} measurements in {elapsed_ms:.0f}ms (queue: {self.queue.qsize()})")
                
                # Clean up
                if cursor:
                    cursor.close()
                if connection:
                    self.db_connection_pool.putconn(connection)
                return
                
            except Exception as e:
                # Clean up on error
                if cursor:
                    try:
                        cursor.close()
                    except Exception:
                        pass
                if connection:
                    try:
                        connection.rollback()
                        self.db_connection_pool.putconn(connection)
                    except Exception:
                        # If we can't return connection, try to close it
                        try:
                            connection.close()
                        except Exception:
                            pass
                
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Upload failed (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {retry_delay}s..."
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(
                        f"Upload failed after {max_retries} attempts: {e}",
                        exc_info=True
                    )
                    with self._stats_lock:
                        self._upload_errors += 1
    
    def _flush_queue(self):
        """Upload all remaining measurements in the queue."""
        logger.info("Flushing remaining measurements...")
        batch: list[Measurement] = []
        
        # Drain the queue
        while True:
            try:
                measurement = self.queue.get_nowait()
                batch.append(measurement)
                
                # Upload in batches
                if len(batch) >= self.batch_size:
                    self._upload_batch(batch)
                    batch = []
            except Empty:
                break
        
        # Upload remaining
        if batch:
            self._upload_batch(batch)
        
        logger.info("Queue flushed")
    
    def get_stats(self) -> dict[str, int]:
        """Get telemetry statistics.
        
        Returns:
            Dictionary with statistics:
            - measurements_produced: Total measurements created
            - measurements_uploaded: Total measurements uploaded
            - measurements_dropped: Total measurements dropped
            - upload_errors: Total upload errors
            - queue_size: Current queue size
        """
        with self._stats_lock:
            return {
                "measurements_produced": self._measurements_produced,
                "measurements_uploaded": self._measurements_uploaded,
                "measurements_dropped": self._measurements_dropped,
                "upload_errors": self._upload_errors,
                "queue_size": self.queue.qsize(),
            }


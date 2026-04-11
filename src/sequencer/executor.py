"""Test executor for running OpenHTF tests."""

import json
import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Optional

import openhtf as htf
from openhtf.core import test_record

from plugs.psu_plug import PSUPlug
from server.supabase_client import download_file

logger = logging.getLogger(__name__)


class TestExecutor:
    """Executes OpenHTF test scripts fetched from Supabase Storage.

    Manages test execution lifecycle:
    - Fetches scripts from Supabase Storage (``project-data`` bucket)
    - Saves execution start timestamp to Postgres
    - Executes test with bound instrument plugs
    - Saves execution end timestamp and results to Postgres
    """

    def __init__(
        self,
        rig_config: dict[str, Any],
        db_connection_pool: Any,
        execution_table_name: str = "test_executions",
    ):
        """
        Initialize test executor.

        Args:
            rig_config: Rig configuration dict containing instruments.
            db_connection_pool: PostgreSQL connection pool (psycopg2.pool.ThreadedConnectionPool).
            execution_table_name: Name of the Postgres table storing execution results.
        """
        self.rig_config = rig_config
        self.db_connection_pool = db_connection_pool
        self.execution_table_name = execution_table_name
        self.rig_id = rig_config.get("rig_id", "unknown")

        # Concurrency control - only one test at a time
        self._execution_lock = threading.Lock()
        self._current_execution: Optional[dict[str, Any]] = None

        # Build bound plug classes for each instrument
        self._bound_plugs = self._create_bound_plugs()

        logger.info(
            "TestExecutor initialized for rig '%s' with %d instrument plug(s)",
            self.rig_id,
            len(self._bound_plugs),
        )

    def _create_bound_plugs(self) -> dict[str, Any]:
        """Create plug instances for each instrument in the rig.

        Returns:
            Dictionary mapping instrument_id to plug instance factory function.
        """
        bound_plugs = {}
        instruments = self.rig_config.get("instruments", [])

        for inst_config in instruments:
            instrument_id = inst_config.get("id")
            instrument_name = inst_config.get("name")
            driver = inst_config.get("driver")

            if not instrument_id or not driver:
                logger.warning(
                    "Skipping instrument with missing 'id' or 'driver': %s",
                    inst_config,
                )
                continue

            # Create plug instance
            plug_instance = PSUPlug(
                driver=driver,
                instrument_id=instrument_id,
                instrument_name=instrument_name,
            )

            # Create a factory function that returns the plug instance
            # Use default argument to capture plug_instance in closure properly
            def plug_factory(plug=plug_instance):
                return plug

            # Use instrument_id as the variable name (e.g., PSU1, PSU2)
            bound_plugs[instrument_id.upper()] = plug_factory
            logger.debug(
                "Created plug factory for %s -> %s",
                instrument_id,
                instrument_id.upper(),
            )

        return bound_plugs

    # ── Script fetching (Supabase Storage) ─────────────────────────────

    def fetch_script_from_storage(self, script_path: str) -> Optional[str]:
        """Fetch a test script from the Supabase Storage ``project-data`` bucket.

        Args:
            script_path: Full path within the bucket, e.g.
                ``projects/abc123/scripts/voltage_ramp.py``.

        Returns:
            Script code as a UTF-8 string, or None if not found.
        """
        data = download_file(script_path)
        if data is None:
            logger.error("Script not found in storage: %s", script_path)
            return None

        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            logger.error("Script at '%s' is not valid UTF-8 text", script_path)
            return None

    # ── Execution record persistence (Postgres) ───────────────────────

    def save_execution_start(
        self,
        execution_id: str,
        dut_serial: Optional[str] = None,
    ) -> bool:
        """Save execution start record to Postgres.

        Args:
            execution_id: Unique execution identifier.
            dut_serial: Optional DUT serial number.

        Returns:
            True if successful, False otherwise.
        """
        connection = None
        cursor = None
        try:
            connection = self.db_connection_pool.getconn()
            cursor = connection.cursor()

            started_at = datetime.now()

            cursor.execute(
                f"""
                INSERT INTO {self.execution_table_name}
                (execution_id, rig_id, dut_serial, status, started_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (execution_id, self.rig_id, dut_serial, "running", started_at),
            )
            connection.commit()

            logger.info("Saved execution start: %s at %s", execution_id, started_at)
            return True

        except Exception as e:
            logger.error("Error saving execution start: %s", e, exc_info=True)
            if connection:
                connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if connection:
                self.db_connection_pool.putconn(connection)

    def save_execution_end(
        self,
        execution_id: str,
        status: str,
        result_json: dict[str, Any],
    ) -> bool:
        """Save execution end record to Postgres.

        Args:
            execution_id: Unique execution identifier.
            status: Test status ('pass', 'fail', 'error').
            result_json: Full OpenHTF test record as dictionary.

        Returns:
            True if successful, False otherwise.
        """
        connection = None
        cursor = None
        try:
            connection = self.db_connection_pool.getconn()
            cursor = connection.cursor()

            completed_at = datetime.now()
            result_json_str = json.dumps(result_json)

            cursor.execute(
                f"""
                UPDATE {self.execution_table_name}
                SET status = %s, completed_at = %s, result_json = %s::jsonb
                WHERE execution_id = %s
                """,
                (status, completed_at, result_json_str, execution_id),
            )
            connection.commit()

            logger.info(
                "Saved execution end: %s with status %s at %s",
                execution_id,
                status,
                completed_at,
            )
            return True

        except Exception as e:
            logger.error("Error saving execution end: %s", e, exc_info=True)
            if connection:
                connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if connection:
                self.db_connection_pool.putconn(connection)

    # ── Test execution ─────────────────────────────────────────────────

    def execute_test(
        self,
        script_code: str,
        dut_serial: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> dict[str, Any]:
        """
        Execute a test script.

        Args:
            script_code: Python code containing OpenHTF test phases.
            dut_serial: Optional DUT serial number.
            timeout: Optional execution timeout in seconds.

        Returns:
            Dictionary with execution_id, status, and optional error message.
        """
        # Check if already executing
        if not self._execution_lock.acquire(blocking=False):
            logger.warning(
                "[rig=%s] Rejected test execution — another test is already running (%s)",
                self.rig_id,
                self._current_execution.get("execution_id")
                if self._current_execution
                else "unknown",
            )
            return {
                "execution_id": None,
                "status": "error",
                "error": "Another test is currently running",
            }

        execution_id = str(uuid.uuid4())

        try:
            # Save execution start
            if not self.save_execution_start(execution_id, dut_serial):
                logger.error(
                    "[exec=%s] Aborting — failed to persist execution start to database",
                    execution_id,
                )
                return {
                    "execution_id": execution_id,
                    "status": "error",
                    "error": "Failed to save execution start to database",
                }

            self._current_execution = {
                "execution_id": execution_id,
                "status": "running",
                "started_at": datetime.now(),
            }

            # Build execution namespace with OpenHTF and bound plugs
            namespace = {
                "openhtf": htf,
                "htf": htf,
                "time": time,
                "__builtins__": __builtins__,
            }

            # Inject bound plug classes into namespace
            namespace.update(self._bound_plugs)

            # Compile and execute script to extract TEST_PHASES
            try:
                code_obj = compile(script_code, "<user_script>", "exec")
                exec(code_obj, namespace)
            except SyntaxError as e:
                error_msg = f"Syntax error in test script: {e}"
                logger.error(error_msg)
                self.save_execution_end(
                    execution_id,
                    "error",
                    {"error": error_msg, "syntax_error": str(e)},
                )
                return {
                    "execution_id": execution_id,
                    "status": "error",
                    "error": error_msg,
                }
            except Exception as e:
                error_msg = f"Error compiling test script: {e}"
                logger.error(error_msg, exc_info=True)
                self.save_execution_end(
                    execution_id,
                    "error",
                    {"error": error_msg, "compile_error": str(e)},
                )
                return {
                    "execution_id": execution_id,
                    "status": "error",
                    "error": error_msg,
                }

            # Extract TEST_PHASES from namespace
            test_phases = namespace.get("TEST_PHASES")
            if not test_phases:
                error_msg = "TEST_PHASES not defined in script — script must assign a list of phase functions to TEST_PHASES"
                logger.error("[exec=%s] %s", execution_id, error_msg)
                self.save_execution_end(
                    execution_id,
                    "error",
                    {"error": error_msg},
                )
                return {
                    "execution_id": execution_id,
                    "status": "error",
                    "error": error_msg,
                }

            logger.info(
                "[exec=%s] TEST_PHASES extracted: %d phase(s) — %s",
                execution_id,
                len(test_phases),
                [getattr(p, "__name__", repr(p)) for p in test_phases],
            )

            # Create OpenHTF test
            test = htf.Test(*test_phases)

            # Add output callback to capture results
            test_record_result: Optional[test_record.TestRecord] = None

            def capture_result(record: test_record.TestRecord):
                nonlocal test_record_result
                test_record_result = record

            test.add_output_callbacks(capture_result)

            # Execute test
            logger.info(
                "[exec=%s] Starting OpenHTF test execution (rig=%s, dut=%s, plugs=%s)",
                execution_id,
                self.rig_id,
                dut_serial or "<none>",
                list(self._bound_plugs.keys()),
            )
            test_passed = test.execute(
                test_start=lambda: dut_serial or execution_id
            )

            # Determine status
            status = "pass" if test_passed else "fail"

            logger.info(
                "[exec=%s] Test completed with status=%s (rig=%s, dut=%s)",
                execution_id,
                status.upper(),
                self.rig_id,
                dut_serial or "<none>",
            )

            # Convert test record to JSON-serializable dict
            result_dict = (
                self._test_record_to_dict(test_record_result)
                if test_record_result
                else {}
            )

            # Save execution end
            self.save_execution_end(execution_id, status, result_dict)

            return {
                "execution_id": execution_id,
                "status": status,
            }

        except Exception as e:
            error_msg = f"Unhandled exception during test execution: {type(e).__name__}: {e}"
            logger.error(
                "[exec=%s] %s (rig=%s, dut=%s)",
                execution_id,
                error_msg,
                self.rig_id,
                dut_serial or "<none>",
                exc_info=True,
            )
            self.save_execution_end(
                execution_id,
                "error",
                {
                    "error": error_msg,
                    "exception": str(e),
                    "exception_type": type(e).__name__,
                },
            )
            return {
                "execution_id": execution_id,
                "status": "error",
                "error": error_msg,
            }
        finally:
            self._current_execution = None
            logger.debug("[exec=%s] Execution lock released", execution_id)
            self._execution_lock.release()

    def _test_record_to_dict(
        self, record: test_record.TestRecord
    ) -> dict[str, Any]:
        """Convert OpenHTF TestRecord to JSON-serializable dictionary."""
        if not record:
            return {}

        try:
            if hasattr(record, "cached_record") and record.cached_record:
                return dict(record.cached_record)

            result = {
                "dut_id": record.dut_id,
                "station_id": record.station_id,
                "start_time_millis": record.start_time_millis,
                "end_time_millis": record.end_time_millis,
                "outcome": str(record.outcome) if record.outcome else None,
                "phases": [],
            }

            for phase in record.phases:
                phase_dict = {
                    "name": phase.name if hasattr(phase, "name") else None,
                    "codeinfo": (
                        str(phase.codeinfo)
                        if hasattr(phase, "codeinfo")
                        else None
                    ),
                    "measurements": {},
                }

                if hasattr(phase, "measurements"):
                    for key, measurement in phase.measurements.items():
                        phase_dict["measurements"][key] = {
                            "value": (
                                measurement.value
                                if hasattr(measurement, "value")
                                else None
                            ),
                            "outcome": (
                                str(measurement.outcome)
                                if hasattr(measurement, "outcome")
                                else None
                            ),
                        }

                result["phases"].append(phase_dict)

            return result

        except Exception as e:
            logger.error(
                "Error converting test record to dict: %s", e, exc_info=True
            )
            return {"error": f"Failed to serialize test record: {e}"}

    def get_current_execution(self) -> Optional[dict[str, Any]]:
        """Get information about the currently running test."""
        return (
            self._current_execution.copy()
            if self._current_execution
            else None
        )

    def is_executing(self) -> bool:
        """Check if a test is currently executing."""
        return self._current_execution is not None

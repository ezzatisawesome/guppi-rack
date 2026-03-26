"""USB connection implementation."""

import logging

import pyvisa as visa

from ..connection import Connection

logger = logging.getLogger(__name__)


class UsbConnection(Connection):
    """USB TMC (Test & Measurement Class) connection implementation."""

    def __init__(
        self,
        address: str,
        timeout: float = 10.0,
        **kwargs
    ):
        """
        Initialize USB connection.
        
        Args:
            address: VISA resource address (e.g., 'USB0::0x1234::0x5678::INSTR').
            timeout: Timeout for the connection in seconds.
            **kwargs: Additional keyword arguments to pass to pyvisa.
        """
        super().__init__(address, timeout, **kwargs)
        self._visa_kwargs = kwargs
        self._resource_manager = None

    def connect(self):
        """Establish USB connection."""
        if self.is_connected():
            logger.debug("[%s] Already connected, skipping connect()", self.address)
            return
        
        # Create ResourceManager if not already created
        if self._resource_manager is None:
            self._resource_manager = visa.ResourceManager('@py')

        try:
            logger.info("[%s] Opening VISA resource (timeout=%.1fs)", self.address, self.timeout)
            self._resource = self._resource_manager.open_resource(
                self.address,
                timeout=int(self.timeout * 1000),  # pyvisa uses milliseconds
                **self._visa_kwargs
            )
            logger.info("[%s] VISA resource opened successfully", self.address)
        except Exception as e:
            logger.error(
                "[%s] Failed to open VISA resource: %s",
                self.address, e, exc_info=True
            )
            raise

    def disconnect(self):
        """Close the USB connection properly."""
        if self._resource is not None:
            try:
                logger.info("[%s] Closing VISA resource", self.address)
                self._resource.close()
                logger.info("[%s] VISA resource closed", self.address)
            except Exception as e:
                logger.warning(
                    "[%s] Error closing VISA resource (ignored): %s",
                    self.address, e
                )
            finally:
                self._resource = None
        else:
            logger.debug("[%s] disconnect() called but already disconnected", self.address)

    def is_connected(self) -> bool:
        """Check if the USB connection is active."""
        return self._resource is not None

    def write(self, command: str):
        """Write a command to the instrument."""
        if not self.is_connected():
            raise RuntimeError(
                f"[{self.address}] Cannot write — connection is not established. Call connect() first."
            )
        logger.debug("[%s] WRITE >> %s", self.address, command)
        try:
            self._resource.write(command)
        except Exception as e:
            logger.error(
                "[%s] WRITE FAILED (cmd=%r): %s", self.address, command, e, exc_info=True
            )
            raise

    def read(self) -> str:
        """Read a response from the instrument."""
        if not self.is_connected():
            raise RuntimeError(
                f"[{self.address}] Cannot read — connection is not established. Call connect() first."
            )
        try:
            response = self._resource.read()
            logger.debug("[%s] READ  << %r", self.address, response)
            return response
        except Exception as e:
            logger.error(
                "[%s] READ FAILED: %s", self.address, e, exc_info=True
            )
            raise

    def query(self, command: str) -> str:
        """Write a command and read the response."""
        if not self.is_connected():
            raise RuntimeError(
                f"[{self.address}] Cannot query — connection is not established. Call connect() first."
            )
        logger.debug("[%s] QUERY >> %s", self.address, command)
        try:
            response = self._resource.query(command)
            logger.debug("[%s] QUERY << %r", self.address, response)
            return response
        except Exception as e:
            logger.error(
                "[%s] QUERY FAILED (cmd=%r): %s", self.address, command, e, exc_info=True
            )
            raise


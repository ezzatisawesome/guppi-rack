"""USB connection implementation."""

import pyvisa as visa

from ..connection import Connection


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
            return
        
        # Create ResourceManager if not already created
        if self._resource_manager is None:
            self._resource_manager = visa.ResourceManager('@py')
        
        self._resource = self._resource_manager.open_resource(
            self.address,
            timeout=int(self.timeout * 1000),  # pyvisa uses milliseconds
            **self._visa_kwargs
        )

    def disconnect(self):
        """Close the USB connection properly."""
        if self._resource is not None:
            try:
                self._resource.close()
            except Exception:
                # Ignore errors during cleanup, but still clear the resource
                pass
            finally:
                self._resource = None

    def is_connected(self) -> bool:
        """Check if the USB connection is active."""
        return self._resource is not None

    def write(self, command: str):
        """Write a command to the instrument."""
        if not self.is_connected():
            raise RuntimeError("Connection is not established. Call connect() first.")
        self._resource.write(command)

    def read(self) -> str:
        """Read a response from the instrument."""
        if not self.is_connected():
            raise RuntimeError("Connection is not established. Call connect() first.")
        return self._resource.read()

    def query(self, command: str) -> str:
        """Write a command and read the response."""
        if not self.is_connected():
            raise RuntimeError("Connection is not established. Call connect() first.")
        return self._resource.query(command)


"""Connection types for instrument communication."""

from abc import ABC, abstractmethod
from enum import StrEnum


class ConnectionType(StrEnum):    
    SERIAL = "serial"
    USB = "usb"
    ETHERNET = "ethernet"
    GPIB = "gpib"
    USB_TMC = "usb_tmc"
    VISA = "visa"


class Connection(ABC):
    """Abstract base class for instrument connections."""

    def __init__(
        self, 
        address: str,
        timeout: float = 10.0,
        **kwargs
    ):
        """
        Initialize connection.
        
        Args:
            address: Address of the instrument.
            timeout: Timeout for the connection.
            **kwargs: Additional keyword arguments to pass to the connection.
        """
        self.address = address
        self.timeout = timeout
        self._resource = None
    
    @abstractmethod
    def connect(self):
        """Establish connection to the instrument."""
        pass

    @abstractmethod
    def disconnect(self):
        """Close the connection to the instrument."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the connection is active."""
        pass

    @abstractmethod
    def write(self, command: str):
        """Write a command to the instrument."""
        pass

    @abstractmethod
    def read(self) -> str:
        """Read a response from the instrument."""
        pass

    @abstractmethod
    def query(self, command: str) -> str:
        """Write a command and read the response."""
        pass

    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """Automatically disconnect when exiting context manager."""
        self.disconnect()

    def __del__(self):
        """Ensure connection is closed when object is garbage collected."""
        try:
            if hasattr(self, '_resource') and self.is_connected():
                self.disconnect()
        except Exception:
            # Ignore errors during cleanup to avoid issues during garbage collection
            pass


def create_connection(
    connection_type: ConnectionType,
    address: str,
    timeout: float = 10.0,
    **kwargs
) -> Connection:
    """
    Factory function to create a connection based on the connection type.
    
    Args:
        connection_type: Type of connection to create.
        address: Address of the instrument.
        timeout: Timeout for the connection.
        **kwargs: Additional keyword arguments to pass to the connection.
    
    Returns:
        Connection instance of the appropriate type.
    
    Raises:
        ValueError: If the connection type is not supported.
    """
    if connection_type == ConnectionType.VISA:
        from .connections import UsbConnection
        return UsbConnection(address, timeout, **kwargs)
    else:
        raise ValueError(f"Unsupported connection type: {connection_type}")
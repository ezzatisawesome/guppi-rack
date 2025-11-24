"""Thread-safe wrapper for instrument connections."""

import threading
from typing import Protocol

from .connection import Connection


class ThreadSafeConnection:
    """Thread-safe wrapper around Connection for concurrent access.
    
    This allows multiple threads to safely access the same instrument
    connection. The measurement thread can read values while the
    command thread sends control commands without blocking each other.
    """
    
    def __init__(self, connection: Connection):
        """
        Initialize thread-safe connection wrapper.
        
        Args:
            connection: The underlying Connection object to wrap.
        """
        self._connection = connection
        self._lock = threading.RLock()  # Reentrant lock for nested calls
    
    def write(self, command: str):
        """Write a command to the instrument (thread-safe)."""
        with self._lock:
            return self._connection.write(command)
    
    def read(self) -> str:
        """Read a response from the instrument (thread-safe)."""
        with self._lock:
            return self._connection.read()
    
    def query(self, command: str) -> str:
        """Write a command and read the response (thread-safe)."""
        with self._lock:
            return self._connection.query(command)
    
    def connect(self):
        """Establish connection (thread-safe)."""
        with self._lock:
            return self._connection.connect()
    
    def disconnect(self):
        """Close the connection (thread-safe)."""
        with self._lock:
            return self._connection.disconnect()
    
    def is_connected(self) -> bool:
        """Check if the connection is active (thread-safe)."""
        # Reading a simple attribute doesn't need a lock, but we use it
        # for consistency and to prevent issues during connect/disconnect
        with self._lock:
            return self._connection.is_connected()
    
    @property
    def connection(self) -> Connection:
        """Access underlying connection if needed (use with caution)."""
        return self._connection
    
    @property
    def address(self) -> str:
        """Get the connection address."""
        return self._connection.address
    
    @property
    def timeout(self) -> float:
        """Get the connection timeout."""
        return self._connection.timeout


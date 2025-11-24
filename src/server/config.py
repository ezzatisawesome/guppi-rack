"""Configuration utilities for server setup."""

import os

import psycopg2
from dotenv import load_dotenv
from psycopg2 import pool

# Load environment variables from .env
load_dotenv()


def get_db_connection_pool(
    min_conn: int = 1,
    max_conn: int = 5,
) -> pool.ThreadedConnectionPool:
    """
    Create and return a PostgreSQL connection pool.
    
    Reads connection URL from DATABASE_URL environment variable.
    
    Args:
        min_conn: Minimum number of connections in the pool.
        max_conn: Maximum number of connections in the pool.
    
    Returns:
        ThreadedConnectionPool instance.
    
    Raises:
        ValueError: If DATABASE_URL environment variable is not set.
        psycopg2.Error: If connection pool creation fails.
    """
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        raise ValueError("DATABASE_URL environment variable must be set")
    
    try:
        connection_pool = pool.ThreadedConnectionPool(
            min_conn,
            max_conn,
            dsn=database_url,
        )
        return connection_pool
    except psycopg2.OperationalError as e:
        # OperationalError includes connection failures (network issues, wrong host, etc.)
        raise ConnectionError(f"Failed to connect to database: {e}") from e
    except psycopg2.Error as e:
        # Other psycopg2 errors (authentication, configuration, etc.)
        raise ValueError(f"Failed to create connection pool: {e}") from e


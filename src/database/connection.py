"""
Database connection manager for Bill Generation System.
Provides thread-safe database connections and context manager support.
"""
import sqlite3
import threading
from contextlib import contextmanager
from typing import Optional
import config


class DatabaseConnection:
    """Singleton database connection manager."""
    
    _instance: Optional['DatabaseConnection'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.db_path = config.get_database_path()
            self.initialized = True
    
    def get_connection(self) -> sqlite3.Connection:
        """
        Get a new database connection.
        
        Returns:
            sqlite3.Connection: Database connection object
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    
    @contextmanager
    def get_cursor(self):
        """
        Context manager for database operations.
        Automatically commits on success and rolls back on error.
        
        Usage:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT * FROM table")
                results = cursor.fetchall()
        
        Yields:
            sqlite3.Cursor: Database cursor
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> list:
        """
        Execute a SELECT query and return results as list of dicts.
        
        Args:
            query: SQL query string
            params: Query parameters
        
        Returns:
            list: Query results as dicts (supports .get() method)
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            # Convert sqlite3.Row to dict for .get() support
            return [dict(row) for row in rows]
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """
        Execute an INSERT, UPDATE, or DELETE query.
        
        Args:
            query: SQL query string
            params: Query parameters
        
        Returns:
            int: Number of affected rows
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount
    
    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """
        Execute an INSERT query and return the last inserted row ID.
        
        Args:
            query: SQL query string
            params: Query parameters
        
        Returns:
            int: Last inserted row ID
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.lastrowid


# Global database instance
db = DatabaseConnection()

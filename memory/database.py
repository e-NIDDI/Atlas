"""SQLite database for Jarvis memory layer."""

import sqlite3
import json
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

from jarvis.config import config
from jarvis.logger import logger


@dataclass
class ProjectRecord:
    """Project database record."""
    id: Optional[int]
    name: str
    path: str
    created_at: str
    description: Optional[str] = None


@dataclass
class ActionRecord:
    """Action database record."""
    id: Optional[int]
    timestamp: str
    tool: str
    arguments: str  # JSON string
    approved: bool
    success: bool
    error: Optional[str] = None
    result: Optional[str] = None


@dataclass
class ConversationRecord:
    """Conversation database record."""
    id: Optional[int]
    role: str
    content: str
    timestamp: str
    is_tool_request: bool = False
    tool_name: Optional[str] = None
    tool_args: Optional[str] = None


class Database:
    """SQLite database manager for Jarvis."""
    
    def __init__(self, db_path: Optional[Path] = None) -> None:
        """
        Initialize database connection.
        
        Args:
            db_path: Path to database file
        """
        self.db_path = db_path or config.db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Database initialized at: {self.db_path}")
    
    def connect(self) -> None:
        """Connect to the database."""
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            logger.debug("Database connected")
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self) -> None:
        """Disconnect from the database."""
        if self.conn:
            try:
                self.conn.close()
                logger.debug("Database disconnected")
            except sqlite3.Error as e:
                logger.error(f"Error disconnecting from database: {e}")
        self.conn = None
        self.cursor = None
    
    def initialize_schema(self) -> None:
        """Create database tables if they don't exist."""
        if not self.conn:
            self.connect()
        
        try:
            # Projects table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    description TEXT
                )
            """)
            
            # Actions table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    tool TEXT NOT NULL,
                    arguments TEXT NOT NULL,
                    approved BOOLEAN NOT NULL,
                    success BOOLEAN NOT NULL,
                    error TEXT,
                    result TEXT
                )
            """)
            
            # Conversation table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    is_tool_request BOOLEAN DEFAULT FALSE,
                    tool_name TEXT,
                    tool_args TEXT
                )
            """)
            
            # Settings table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Create indexes for better performance
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_actions_timestamp 
                ON actions(timestamp)
            """)
            
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_timestamp 
                ON conversation(timestamp)
            """)
            
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_role 
                ON conversation(role)
            """)
            
            self.conn.commit()
            logger.info("Database schema initialized")
            
        except sqlite3.Error as e:
            logger.error(f"Error initializing database schema: {e}")
            raise
    
    def execute_query(self, query: str, params: tuple = ()) -> Optional[sqlite3.Cursor]:
        """
        Execute a SQL query.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Cursor object or None if error
        """
        if not self.conn:
            self.connect()
        
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            return self.cursor
        except sqlite3.Error as e:
            logger.error(f"Error executing query: {e}")
            self.conn.rollback()
            return None
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """
        Fetch a single row.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Row as dictionary or None
        """
        cursor = self.execute_query(query, params)
        if cursor:
            row = cursor.fetchone()
            return dict(row) if row else None
        return None
    
    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Fetch all rows.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            List of rows as dictionaries
        """
        cursor = self.execute_query(query, params)
        if cursor:
            return [dict(row) for row in cursor.fetchall()]
        return []
    
    # Project operations
    
    def insert_project(self, project: ProjectRecord) -> Optional[int]:
        """
        Insert a project record.
        
        Args:
            project: Project record
            
        Returns:
            Project ID or None if error
        """
        query = """
            INSERT OR REPLACE INTO projects (name, path, created_at, description)
            VALUES (?, ?, ?, ?)
        """
        cursor = self.execute_query(
            query,
            (project.name, project.path, project.created_at, project.description)
        )
        if cursor:
            return cursor.lastrowid
        return None
    
    def get_project(self, name: str) -> Optional[ProjectRecord]:
        """
        Get a project by name.
        
        Args:
            name: Project name
            
        Returns:
            Project record or None
        """
        query = "SELECT * FROM projects WHERE name = ?"
        row = self.fetch_one(query, (name,))
        if row:
            return ProjectRecord(
                id=row["id"],
                name=row["name"],
                path=row["path"],
                created_at=row["created_at"],
                description=row["description"]
            )
        return None
    
    def get_all_projects(self) -> List[ProjectRecord]:
        """
        Get all projects.
        
        Returns:
            List of project records
        """
        query = "SELECT * FROM projects ORDER BY created_at DESC"
        rows = self.fetch_all(query)
        return [
            ProjectRecord(
                id=row["id"],
                name=row["name"],
                path=row["path"],
                created_at=row["created_at"],
                description=row["description"]
            )
            for row in rows
        ]
    
    def delete_project(self, name: str) -> bool:
        """
        Delete a project record.
        
        Args:
            name: Project name
            
        Returns:
            True if deleted, False otherwise
        """
        query = "DELETE FROM projects WHERE name = ?"
        cursor = self.execute_query(query, (name,))
        return cursor is not None and cursor.rowcount > 0
    
    # Action operations
    
    def insert_action(self, action: ActionRecord) -> Optional[int]:
        """
        Insert an action record.
        
        Args:
            action: Action record
            
        Returns:
            Action ID or None if error
        """
        query = """
            INSERT INTO actions (timestamp, tool, arguments, approved, success, error, result)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        cursor = self.execute_query(
            query,
            (
                action.timestamp,
                action.tool,
                action.arguments,
                action.approved,
                action.success,
                action.error,
                action.result
            )
        )
        if cursor:
            return cursor.lastrowid
        return None
    
    def get_recent_actions(self, limit: int = 50) -> List[ActionRecord]:
        """
        Get recent actions.
        
        Args:
            limit: Maximum number of actions to return
            
        Returns:
            List of action records
        """
        query = "SELECT * FROM actions ORDER BY timestamp DESC LIMIT ?"
        rows = self.fetch_all(query, (limit,))
        return [
            ActionRecord(
                id=row["id"],
                timestamp=row["timestamp"],
                tool=row["tool"],
                arguments=row["arguments"],
                approved=row["approved"],
                success=row["success"],
                error=row["error"],
                result=row["result"]
            )
            for row in rows
        ]
    
    # Conversation operations
    
    def insert_conversation(self, record: ConversationRecord) -> Optional[int]:
        """
        Insert a conversation record.
        
        Args:
            record: Conversation record
            
        Returns:
            Record ID or None if error
        """
        query = """
            INSERT INTO conversation (role, content, timestamp, is_tool_request, tool_name, tool_args)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        cursor = self.execute_query(
            query,
            (
                record.role,
                record.content,
                record.timestamp,
                record.is_tool_request,
                record.tool_name,
                record.tool_args
            )
        )
        if cursor:
            return cursor.lastrowid
        return None
    
    def get_conversation_history(self, limit: int = 100) -> List[ConversationRecord]:
        """
        Get conversation history.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of conversation records
        """
        query = "SELECT * FROM conversation ORDER BY timestamp ASC LIMIT ?"
        rows = self.fetch_all(query, (limit,))
        return [
            ConversationRecord(
                id=row["id"],
                role=row["role"],
                content=row["content"],
                timestamp=row["timestamp"],
                is_tool_request=row["is_tool_request"],
                tool_name=row["tool_name"],
                tool_args=row["tool_args"]
            )
            for row in rows
        ]
    
    def clear_conversation(self) -> bool:
        """
        Clear conversation history.
        
        Returns:
            True if successful, False otherwise
        """
        query = "DELETE FROM conversation"
        cursor = self.execute_query(query)
        return cursor is not None
    
    # Settings operations
    
    def set_setting(self, key: str, value: str) -> bool:
        """
        Set a setting value.
        
        Args:
            key: Setting key
            value: Setting value
            
        Returns:
            True if successful, False otherwise
        """
        timestamp = datetime.now().isoformat()
        query = """
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
        """
        cursor = self.execute_query(query, (key, value, timestamp))
        return cursor is not None
    
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a setting value.
        
        Args:
            key: Setting key
            default: Default value if not found
            
        Returns:
            Setting value or default
        """
        query = "SELECT value FROM settings WHERE key = ?"
        row = self.fetch_one(query, (key,))
        return row["value"] if row else default
    
    def get_all_settings(self) -> Dict[str, str]:
        """
        Get all settings.
        
        Returns:
            Dictionary of settings
        """
        query = "SELECT key, value FROM settings"
        rows = self.fetch_all(query)
        return {row["key"]: row["value"] for row in rows}
    
    def __enter__(self) -> "Database":
        """Context manager entry."""
        self.connect()
        self.initialize_schema()
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.disconnect()


# Global database instance
db = Database()
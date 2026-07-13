"""History management for Jarvis memory layer."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass

from jarvis.memory.database import Database, ActionRecord, ConversationRecord
from jarvis.logger import logger


@dataclass
class ActionHistory:
    """Action history entry."""
    id: Optional[int]
    timestamp: str
    tool: str
    arguments: Dict[str, Any]
    approved: bool
    success: bool
    error: Optional[str] = None
    result: Optional[str] = None


@dataclass
class ConversationHistory:
    """Conversation history entry."""
    id: Optional[int]
    role: str
    content: str
    timestamp: str
    is_tool_request: bool = False
    tool_name: Optional[str] = None
    tool_args: Optional[str] = None


class HistoryManager:
    """Manages action and conversation history."""
    
    def __init__(self, db: Optional[Database] = None) -> None:
        """
        Initialize history manager.
        
        Args:
            db: Database instance
        """
        self.db = db or Database()
        self.db.connect()
        self.db.initialize_schema()
        logger.info("History manager initialized")
    
    def log_action(
        self,
        tool: str,
        arguments: Dict[str, Any],
        approved: bool,
        success: bool,
        error: Optional[str] = None,
        result: Optional[str] = None
    ) -> Optional[int]:
        """
        Log an action to the database.
        
        Args:
            tool: Tool name
            arguments: Tool arguments
            approved: Whether action was approved
            success: Whether action succeeded
            error: Error message if failed
            result: Result message
            
        Returns:
            Action ID or None if error
        """
        import json
        
        action = ActionRecord(
            id=None,
            timestamp=datetime.now().isoformat(),
            tool=tool,
            arguments=json.dumps(arguments),
            approved=approved,
            success=success,
            error=error,
            result=result
        )
        
        action_id = self.db.insert_action(action)
        logger.debug(f"Action logged: {tool} (id={action_id})")
        return action_id
    
    def log_conversation(
        self,
        role: str,
        content: str,
        is_tool_request: bool = False,
        tool_name: Optional[str] = None,
        tool_args: Optional[str] = None
    ) -> Optional[int]:
        """
        Log a conversation message to the database.
        
        Args:
            role: Message role (user, assistant, system)
            content: Message content
            is_tool_request: Whether this was a tool request
            tool_name: Tool name if applicable
            tool_args: Tool arguments if applicable
            
        Returns:
            Record ID or None if error
        """
        record = ConversationRecord(
            id=None,
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            is_tool_request=is_tool_request,
            tool_name=tool_name,
            tool_args=tool_args
        )
        
        record_id = self.db.insert_conversation(record)
        logger.debug(f"Conversation logged: {role} (id={record_id})")
        return record_id
    
    def get_recent_actions(self, limit: int = 50) -> List[ActionHistory]:
        """
        Get recent actions.
        
        Args:
            limit: Maximum number of actions to return
            
        Returns:
            List of ActionHistory objects
        """
        import json
        
        records = self.db.get_recent_actions(limit)
        return [
            ActionHistory(
                id=record.id,
                timestamp=record.timestamp,
                tool=record.tool,
                arguments=json.loads(record.arguments) if record.arguments else {},
                approved=record.approved,
                success=record.success,
                error=record.error,
                result=record.result
            )
            for record in records
        ]
    
    def get_conversation_history(self, limit: int = 100) -> List[ConversationHistory]:
        """
        Get conversation history.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of ConversationHistory objects
        """
        records = self.db.get_conversation_history(limit)
        return [
            ConversationHistory(
                id=record.id,
                role=record.role,
                content=record.content,
                timestamp=record.timestamp,
                is_tool_request=record.is_tool_request,
                tool_name=record.tool_name,
                tool_args=record.tool_args
            )
            for record in records
        ]
    
    def clear_conversation_history(self) -> bool:
        """
        Clear conversation history.
        
        Returns:
            True if successful, False otherwise
        """
        result = self.db.clear_conversation()
        if result:
            logger.info("Conversation history cleared")
        return result
    
    def get_action_stats(self) -> Dict[str, Any]:
        """
        Get action statistics.
        
        Returns:
            Dictionary with action statistics
        """
        try:
            # Total actions
            total = self.db.fetch_one("SELECT COUNT(*) as count FROM actions")
            total_count = total["count"] if total else 0
            
            # Approved vs rejected
            approved = self.db.fetch_one(
                "SELECT COUNT(*) as count FROM actions WHERE approved = 1"
            )
            approved_count = approved["count"] if approved else 0
            
            # Success rate
            successful = self.db.fetch_one(
                "SELECT COUNT(*) as count FROM actions WHERE success = 1"
            )
            success_count = successful["count"] if successful else 0
            
            # Tool usage
            tool_usage = self.db.fetch_all(
                "SELECT tool, COUNT(*) as count FROM actions GROUP BY tool ORDER BY count DESC"
            )
            
            return {
                "total_actions": total_count,
                "approved_actions": approved_count,
                "rejected_actions": total_count - approved_count,
                "successful_actions": success_count,
                "failed_actions": total_count - success_count,
                "approval_rate": (approved_count / total_count * 100) if total_count > 0 else 0,
                "success_rate": (success_count / total_count * 100) if total_count > 0 else 0,
                "tool_usage": {row["tool"]: row["count"] for row in tool_usage}
            }
        except Exception as e:
            logger.error(f"Error getting action stats: {e}")
            return {}
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """
        Get conversation statistics.
        
        Returns:
            Dictionary with conversation statistics
        """
        try:
            # Total messages
            total = self.db.fetch_one("SELECT COUNT(*) as count FROM conversation")
            total_count = total["count"] if total else 0
            
            # Messages by role
            by_role = self.db.fetch_all(
                "SELECT role, COUNT(*) as count FROM conversation GROUP BY role"
            )
            
            # Tool requests
            tool_requests = self.db.fetch_one(
                "SELECT COUNT(*) as count FROM conversation WHERE is_tool_request = 1"
            )
            tool_request_count = tool_requests["count"] if tool_requests else 0
            
            return {
                "total_messages": total_count,
                "messages_by_role": {row["role"]: row["count"] for row in by_role},
                "tool_requests": tool_request_count,
                "regular_messages": total_count - tool_request_count
            }
        except Exception as e:
            logger.error(f"Error getting conversation stats: {e}")
            return {}
    
    def export_history(self, file_path: str) -> bool:
        """
        Export history to a JSON file.
        
        Args:
            file_path: Path to export file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import json
            
            # Get all data
            actions = self.get_recent_actions(limit=1000)
            conversations = self.get_conversation_history(limit=1000)
            
            # Convert to dictionaries
            export_data = {
                "exported_at": datetime.now().isoformat(),
                "actions": [
                    {
                        "timestamp": a.timestamp,
                        "tool": a.tool,
                        "arguments": a.arguments,
                        "approved": a.approved,
                        "success": a.success,
                        "error": a.error,
                        "result": a.result
                    }
                    for a in actions
                ],
                "conversations": [
                    {
                        "role": c.role,
                        "content": c.content,
                        "timestamp": c.timestamp,
                        "is_tool_request": c.is_tool_request,
                        "tool_name": c.tool_name,
                        "tool_args": c.tool_args
                    }
                    for c in conversations
                ]
            }
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"History exported to: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting history: {e}")
            return False


# Global history manager instance
history_manager = HistoryManager()
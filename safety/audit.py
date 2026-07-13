"""Audit logging for Jarvis.

Records all actions, tool executions, and decisions
for accountability and debugging.
"""

import json
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from jarvis.config import config
from jarvis.logger import logger


class AuditLog:
    """Structured audit log for all Jarvis actions."""

    def __init__(self, log_dir: Optional[Path] = None) -> None:
        self.log_dir = log_dir or config.log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Audit log initialized at {self.log_dir}")

    def _get_log_file(self) -> Path:
        """Get today's audit log file."""
        return self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl"

    def record(
        self,
        action: str,
        tool: Optional[str] = None,
        args: Optional[Dict[str, Any]] = None,
        result: Optional[str] = None,
        success: bool = True,
        user: str = "default",
        duration_ms: Optional[float] = None,
    ) -> None:
        """Record an action to the audit log."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "tool": tool,
            "args": args,
            "result": result,
            "success": success,
            "user": user,
            "duration_ms": duration_ms,
        }

        log_file = self._get_log_file()
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def query(
        self,
        action: Optional[str] = None,
        tool: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 100,
    ) -> list:
        """Query audit log entries."""
        log_file = self._get_log_file()
        results = []

        if not log_file.exists():
            return results

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if action and entry.get("action") != action:
                        continue
                    if tool and entry.get("tool") != tool:
                        continue
                    if success is not None and entry.get("success") != success:
                        continue

                    results.append(entry)
                    if len(results) >= limit:
                        break
        except Exception as e:
            logger.error(f"Failed to query audit log: {e}")

        return results


# Global instance
audit = AuditLog()
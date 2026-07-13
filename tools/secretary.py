"""Secretary capabilities for Jarvis.

Provides:
- Note taking and retrieval
- Task tracking and management
- Project organization and context
- Summary generation
- Information retrieval across projects
"""

import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from jarvis.tools.registry import BaseTool, ToolResult
from jarvis.tools.filesystem import fs
from jarvis.config import config
from jarvis.logger import logger


# ──────────────────────────────────────────────
#  Secretary Manager
# ──────────────────────────────────────────────

class SecretaryManager:
    """Manages notes, tasks, and project organization."""

    NOTES_DIR = "jarvis_notes"
    TASKS_DIR = "jarvis_tasks"
    PROJECT_MEMORY_FILE = "jarvis_project_memory.json"

    def __init__(self) -> None:
        self.notes_path = config.workspace_root / self.NOTES_DIR
        self.tasks_path = config.workspace_root / self.TASKS_DIR
        self.memory_file = config.workspace_root / self.PROJECT_MEMORY_FILE
        self.notes_path.mkdir(parents=True, exist_ok=True)
        self.tasks_path.mkdir(parents=True, exist_ok=True)
        self._project_memory: Dict[str, Any] = {}
        self._load_project_memory()
        logger.info("Secretary manager initialized")

    # ── Notes ──────────────────────────────────

    def create_note(self, title: str, content: str, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a new note."""
        safe_title = self._sanitize_filename(title)
        timestamp = datetime.now()
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{safe_title}.md"
        filepath = self.notes_path / filename

        note_content = self._format_note(title, content, tags)
        filepath.write_text(note_content, encoding='utf-8')

        note = {
            "title": title,
            "filename": filename,
            "path": str(filepath),
            "created": timestamp.isoformat(),
            "tags": tags or [],
            "word_count": len(content.split()),
        }

        logger.info(f"Note created: {title}")
        return note

    def search_notes(self, query: str) -> List[Dict[str, Any]]:
        """Search notes by title or content."""
        results = []
        query_lower = query.lower()

        for note_file in sorted(self.notes_path.glob("*.md"), reverse=True):
            try:
                content = note_file.read_text(encoding='utf-8')
                if query_lower in content.lower():
                    # Extract title from first line
                    first_line = content.split('\n')[0].lstrip('# ')
                    results.append({
                        "title": first_line,
                        "filename": note_file.name,
                        "path": str(note_file),
                        "preview": content[:200].replace('\n', ' '),
                        "modified": datetime.fromtimestamp(
                            note_file.stat().st_mtime
                        ).isoformat(),
                    })
            except Exception:
                continue

        return results

    def list_notes(self, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all notes, optionally filtered by tag."""
        notes = []
        for note_file in sorted(self.notes_path.glob("*.md"), reverse=True):
            try:
                content = note_file.read_text(encoding='utf-8')
                first_line = content.split('\n')[0].lstrip('# ')

                # Extract tags from front matter or tag line
                tags = self._extract_tags(content)

                if tag and tag not in tags:
                    continue

                notes.append({
                    "title": first_line,
                    "filename": note_file.name,
                    "path": str(note_file),
                    "tags": tags,
                    "modified": datetime.fromtimestamp(
                        note_file.stat().st_mtime
                    ).isoformat(),
                })
            except Exception:
                continue

        return notes

    def read_note(self, filename: str) -> Optional[str]:
        """Read a note by filename."""
        filepath = self.notes_path / filename
        if not filepath.exists():
            # Try to find by title
            for nf in self.notes_path.glob("*.md"):
                content = nf.read_text(encoding='utf-8')
                if filename.lower() in content.split('\n')[0].lower():
                    return content
            return None
        return filepath.read_text(encoding='utf-8')

    # ── Tasks ──────────────────────────────────

    def create_task(
        self,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        project: Optional[str] = None,
        due_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new task."""
        task_id = f"TASK-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        task = {
            "id": task_id,
            "title": title,
            "description": description or "",
            "priority": priority,
            "project": project,
            "status": "open",
            "created": datetime.now().isoformat(),
            "due_date": due_date,
            "updated": datetime.now().isoformat(),
        }

        # Save as individual JSON file
        task_file = self.tasks_path / f"{task_id}.json"
        task_file.write_text(json.dumps(task, indent=2), encoding='utf-8')

        logger.info(f"Task created: {task_id} - {title}")
        return task

    def list_tasks(self, status: Optional[str] = None, project: Optional[str] = None) -> List[Dict[str, Any]]:
        """List tasks, optionally filtered."""
        tasks = []
        for task_file in sorted(self.tasks_path.glob("*.json"), reverse=True):
            try:
                task = json.loads(task_file.read_text(encoding='utf-8'))
                if status and task.get("status") != status:
                    continue
                if project and task.get("project") != project:
                    continue
                tasks.append(task)
            except Exception:
                continue
        return tasks

    def update_task(self, task_id: str, **updates) -> Optional[Dict[str, Any]]:
        """Update a task's fields."""
        task_file = self.tasks_path / f"{task_id}.json"
        if not task_file.exists():
            return None

        task = json.loads(task_file.read_text(encoding='utf-8'))
        for key, value in updates.items():
            if value is not None:
                task[key] = value
        task["updated"] = datetime.now().isoformat()

        task_file.write_text(json.dumps(task, indent=2), encoding='utf-8')
        logger.info(f"Task updated: {task_id}")
        return task

    def complete_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Mark a task as completed."""
        return self.update_task(task_id, status="completed")

    # ── Project Memory ─────────────────────────

    def _load_project_memory(self) -> None:
        """Load project memory from disk."""
        if self.memory_file.exists():
            try:
                self._project_memory = json.loads(
                    self.memory_file.read_text(encoding='utf-8')
                )
            except Exception:
                self._project_memory = {}
        else:
            self._project_memory = {}

    def _save_project_memory(self) -> None:
        """Save project memory to disk."""
        self.memory_file.write_text(
            json.dumps(self._project_memory, indent=2, ensure_ascii=False),
            encoding='utf-8',
        )

    def remember_project_context(self, project: str, key: str, value: Any) -> None:
        """Store a piece of information about a project."""
        if project not in self._project_memory:
            self._project_memory[project] = {
                "created": datetime.now().isoformat(),
                "notes": [],
                "decisions": [],
                "context": {},
            }
        self._project_memory[project]["context"][key] = {
            "value": value,
            "timestamp": datetime.now().isoformat(),
        }
        self._save_project_memory()
        logger.info(f"Project memory updated: {project}.{key}")

    def get_project_context(self, project: str) -> Optional[Dict[str, Any]]:
        """Get all stored context for a project."""
        return self._project_memory.get(project)

    def add_project_note(self, project: str, note: str) -> None:
        """Add a note to a project's memory."""
        if project not in self._project_memory:
            self._project_memory[project] = {
                "created": datetime.now().isoformat(),
                "notes": [],
                "decisions": [],
                "context": {},
            }
        self._project_memory[project]["notes"].append({
            "text": note,
            "timestamp": datetime.now().isoformat(),
        })
        self._save_project_memory()

    def add_project_decision(self, project: str, decision: str) -> None:
        """Record a decision made about a project."""
        if project not in self._project_memory:
            self._project_memory[project] = {
                "created": datetime.now().isoformat(),
                "notes": [],
                "decisions": [],
                "context": {},
            }
        self._project_memory[project]["decisions"].append({
            "text": decision,
            "timestamp": datetime.now().isoformat(),
        })
        self._save_project_memory()

    def list_projects_with_memory(self) -> List[str]:
        """List all projects that have stored memory."""
        return list(self._project_memory.keys())

    def search_memory(self, query: str) -> List[Dict[str, Any]]:
        """Search across all project memories."""
        results = []
        query_lower = query.lower()

        for project, data in self._project_memory.items():
            # Search context values
            for key, ctx in data.get("context", {}).items():
                if query_lower in str(ctx.get("value", "")).lower():
                    results.append({
                        "project": project,
                        "type": "context",
                        "key": key,
                        "value": ctx["value"],
                        "timestamp": ctx["timestamp"],
                    })

            # Search notes
            for note in data.get("notes", []):
                if query_lower in note["text"].lower():
                    results.append({
                        "project": project,
                        "type": "note",
                        "text": note["text"],
                        "timestamp": note["timestamp"],
                    })

            # Search decisions
            for decision in data.get("decisions", []):
                if query_lower in decision["text"].lower():
                    results.append({
                        "project": project,
                        "type": "decision",
                        "text": decision["text"],
                        "timestamp": decision["timestamp"],
                    })

        return results

    # ── Helpers ────────────────────────────────

    def _format_note(self, title: str, content: str, tags: Optional[List[str]] = None) -> str:
        """Format a note as Markdown."""
        lines = [f"# {title}", ""]
        if tags:
            lines.append(f"Tags: {', '.join(f'#{t}' for t in tags)}")
            lines.append("")
        lines.append(content)
        return "\n".join(lines)

    def _extract_tags(self, content: str) -> List[str]:
        """Extract tags from note content."""
        tags = []
        for line in content.split('\n'):
            if line.lower().startswith('tags:'):
                tags = re.findall(r'#(\w+)', line)
                break
        return tags

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Sanitize a string for use as a filename."""
        name = name.strip().lower()
        name = re.sub(r'[^a-z0-9_-]', '_', name)
        name = re.sub(r'_+', '_', name)
        return name[:100] or "untitled"


# Global instance
secretary = SecretaryManager()


# ══════════════════════════════════════════════
#  Tool Implementations
# ══════════════════════════════════════════════

class CreateNoteTool(BaseTool):
    name = "create_note"
    description = "Create a new note with title, content, and optional tags"
    requires_confirmation = False

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "title" not in kwargs:
            return False, "Missing required argument: title"
        if "content" not in kwargs:
            return False, "Missing required argument: content"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["title", "content"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            note = secretary.create_note(
                kwargs["title"],
                kwargs["content"],
                kwargs.get("tags"),
            )
            return ToolResult(
                success=True,
                message=f"Note created: '{note['title']}'",
                data=note,
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class SearchNotesTool(BaseTool):
    name = "search_notes"
    description = "Search through notes by keyword"
    requires_confirmation = False

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "query" not in kwargs:
            return False, "Missing required argument: query"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["query"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            results = secretary.search_notes(kwargs["query"])
            if not results:
                return ToolResult(
                    success=True,
                    message=f"No notes matching '{kwargs['query']}'",
                    data=[],
                )
            lines = [f"Found {len(results)} note(s):"]
            for r in results:
                lines.append(f"  📝 {r['title']} ({r['filename']})")
                lines.append(f"     {r['preview'][:100]}...")
            return ToolResult(
                success=True,
                message="\n".join(lines),
                data=results,
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class ListNotesTool(BaseTool):
    name = "list_notes"
    description = "List all notes, optionally filtered by tag"
    requires_confirmation = False

    def get_required_args(self) -> List[str]:
        return []

    async def execute(self, **kwargs) -> ToolResult:
        try:
            tag = kwargs.get("tag")
            notes = secretary.list_notes(tag)
            if not notes:
                return ToolResult(
                    success=True,
                    message="No notes found. Create one with 'create_note'.",
                    data=[],
                )
            lines = [f"Notes ({len(notes)}):"]
            for n in notes:
                tag_str = f" [{', '.join(n['tags'])}]" if n['tags'] else ""
                lines.append(f"  📝 {n['title']}{tag_str}")
            return ToolResult(
                success=True,
                message="\n".join(lines),
                data=notes,
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class CreateTaskTool(BaseTool):
    name = "create_task"
    description = "Create a new task with title, description, priority, and project"
    requires_confirmation = False

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "title" not in kwargs:
            return False, "Missing required argument: title"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["title"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            task = secretary.create_task(
                kwargs["title"],
                kwargs.get("description"),
                kwargs.get("priority", "medium"),
                kwargs.get("project"),
                kwargs.get("due_date"),
            )
            return ToolResult(
                success=True,
                message=f"Task created: {task['id']} - {task['title']}",
                data=task,
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class ListTasksTool(BaseTool):
    name = "list_tasks"
    description = "List tasks, optionally filtered by status or project"
    requires_confirmation = False

    def get_required_args(self) -> List[str]:
        return []

    async def execute(self, **kwargs) -> ToolResult:
        try:
            tasks = secretary.list_tasks(
                kwargs.get("status"),
                kwargs.get("project"),
            )
            if not tasks:
                return ToolResult(
                    success=True,
                    message="No tasks found.",
                    data=[],
                )
            lines = [f"Tasks ({len(tasks)}):"]
            for t in tasks:
                status_icon = "✅" if t["status"] == "completed" else "🔄" if t["status"] == "in_progress" else "📋"
                priority_mark = "🔴" if t["priority"] == "high" else "🟡" if t["priority"] == "medium" else "🟢"
                proj = f" [{t['project']}]" if t.get("project") else ""
                lines.append(f"  {status_icon} {priority_mark} {t['id']}: {t['title']}{proj} ({t['status']})")
            return ToolResult(
                success=True,
                message="\n".join(lines),
                data=tasks,
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class CompleteTaskTool(BaseTool):
    name = "complete_task"
    description = "Mark a task as completed"
    requires_confirmation = False

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "task_id" not in kwargs:
            return False, "Missing required argument: task_id"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["task_id"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            task = secretary.complete_task(kwargs["task_id"])
            if not task:
                return ToolResult(
                    success=False,
                    message=f"Task not found: {kwargs['task_id']}",
                    error="Task not found",
                )
            return ToolResult(
                success=True,
                message=f"Task completed: {task['id']} - {task['title']}",
                data=task,
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class RememberProjectContextTool(BaseTool):
    name = "remember_project_context"
    description = "Store information about a project for future reference"
    requires_confirmation = False

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "project" not in kwargs:
            return False, "Missing required argument: project"
        if "key" not in kwargs:
            return False, "Missing required argument: key"
        if "value" not in kwargs:
            return False, "Missing required argument: value"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["project", "key", "value"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            secretary.remember_project_context(
                kwargs["project"], kwargs["key"], kwargs["value"]
            )
            return ToolResult(
                success=True,
                message=f"Remembered: {kwargs['project']}.{kwargs['key']}",
                data={"project": kwargs["project"], "key": kwargs["key"]},
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class GetProjectContextTool(BaseTool):
    name = "get_project_context"
    description = "Retrieve all stored context about a project"
    requires_confirmation = False

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "project" not in kwargs:
            return False, "Missing required argument: project"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["project"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            context = secretary.get_project_context(kwargs["project"])
            if not context:
                return ToolResult(
                    success=True,
                    message=f"No stored context for project: {kwargs['project']}",
                    data=None,
                )

            lines = [f"Project Memory: {kwargs['project']}"]
            lines.append(f"  Created: {context.get('created', 'unknown')}")

            ctx = context.get("context", {})
            if ctx:
                lines.append("  Context:")
                for key, val in ctx.items():
                    lines.append(f"    {key}: {val.get('value', '')}")

            notes = context.get("notes", [])
            if notes:
                lines.append(f"  Notes ({len(notes)}):")
                for n in notes[-5:]:
                    lines.append(f"    • {n['text'][:100]}")

            decisions = context.get("decisions", [])
            if decisions:
                lines.append(f"  Decisions ({len(decisions)}):")
                for d in decisions[-5:]:
                    lines.append(f"    • {d['text'][:100]}")

            return ToolResult(
                success=True,
                message="\n".join(lines),
                data=context,
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class SearchMemoryTool(BaseTool):
    name = "search_memory"
    description = "Search across all project memories for information"
    requires_confirmation = False

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "query" not in kwargs:
            return False, "Missing required argument: query"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["query"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            results = secretary.search_memory(kwargs["query"])
            if not results:
                return ToolResult(
                    success=True,
                    message=f"No memories matching '{kwargs['query']}'",
                    data=[],
                )
            lines = [f"Found {len(results)} memory match(es):"]
            for r in results:
                lines.append(f"  [{r['project']}] ({r['type']}): {r.get('text', r.get('value', ''))[:100]}")
            return ToolResult(
                success=True,
                message="\n".join(lines),
                data=results,
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))
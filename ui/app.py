"""Main Textual application for Jarvis."""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Header,
    Footer,
    Static,
    Input,
    Button,
    RichLog,
    ListView,
    ListItem,
    Label,
)
from textual.reactive import reactive
from textual.binding import Binding
from typing import Optional
import asyncio

from jarvis.config import config
from jarvis.logger import logger
from jarvis.brain.agent import get_agent, AgentState


class JarvisApp(App):
    """Main Jarvis terminal application."""
    
    CSS = """
    Screen {
        layout: vertical;
    }
    
    #main_container {
        height: 1fr;
    }
    
    #sidebar {
        width: 30;
        dock: left;
        background: $panel;
    }
    
    #chat_container {
        height: 1fr;
    }
    
    #chat_log {
        height: 1fr;
        border: solid $primary;
        padding: 1;
        overflow-y: auto;
    }
    
    #input_container {
        height: 3;
        padding: 1;
    }
    
    #user_input {
        width: 1fr;
    }
    
    #status_bar {
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
    }
    
    #log_panel {
        height: 10;
        border: solid $accent;
        padding: 1;
        overflow-y: auto;
    }
    
    ListView {
        height: 1fr;
    }
    
    ListItem {
        padding: 0 1;
    }
    
    ListItem:hover {
        background: $accent;
    }
    
    .project-item {
        text-style: bold;
    }
    
    .user-message {
        color: $success;
        text-style: bold;
    }
    
    .assistant-message {
        color: $text;
    }
    
    .system-message {
        color: $warning;
        text-style: italic;
    }
    
    .error-message {
        color: $error;
        text-style: bold;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+l", "clear_logs", "Clear Logs", show=False),
        Binding("ctrl+n", "new_project", "New Project", show=False),
    ]
    
    current_project: reactive[Optional[str]] = reactive(None)
    
    def __init__(self) -> None:
        """Initialize the application."""
        super().__init__()
        self.title = "Jarvis AI Assistant"
        self.sub_title = "Local AI Workspace Manager"
    
    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header()
        
        with Container(id="main_container"):
            # Sidebar
            with Vertical(id="sidebar"):
                yield Static("📁 Projects", classes="header")
                yield ListView(id="project_list")
                yield Button("New Project", id="new_project_btn", variant="primary")
            
            # Main content area
            with Vertical(id="chat_container"):
                # Chat log
                yield RichLog(
                    id="chat_log",
                    highlight=True,
                    markup=True,
                    wrap=True,
                )
                
                # Input area
                with Horizontal(id="input_container"):
                    yield Input(
                        placeholder="Ask Jarvis anything...",
                        id="user_input",
                    )
                    yield Button("Send", id="send_btn", variant="success")
        
        # Status bar
        yield Static("Ready", id="status_bar")
        
        # Log panel
        yield Static("📋 Logs", classes="header")
        yield RichLog(
            id="log_panel",
            highlight=True,
            markup=True,
            wrap=True,
            max_lines=100,
        )
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Handle application mount."""
        logger.info("Jarvis application started")
        
        # Set up log panel
        self.log_panel = self.query_one("#log_panel", RichLog)
        self.chat_log = self.query_one("#chat_log", RichLog)
        self.status_bar = self.query_one("#status_bar", Static)
        self.user_input = self.query_one("#user_input", Input)
        
        # Add initial message
        self.add_message(
            "system",
            "Welcome to Jarvis! I'm your local AI assistant. How can I help you today?"
        )
        
        # Load projects
        self.refresh_project_list()
        
        # Focus input
        self.user_input.focus()
    
    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the chat log.
        
        Args:
            role: Message role (user, assistant, system, error)
            content: Message content
        """
        if role == "user":
            self.chat_log.write(f"[bold cyan]You:[/bold cyan] {content}")
        elif role == "assistant":
            self.chat_log.write(f"[bold green]Jarvis:[/bold green] {content}")
        elif role == "system":
            self.chat_log.write(f"[bold yellow]System:[/bold yellow] {content}")
        elif role == "error":
            self.chat_log.write(f"[bold red]Error:[/bold red] {content}")
        else:
            self.chat_log.write(content)
        
        logger.debug(f"Chat message added - Role: {role}, Content: {content[:100]}")
    
    def add_log(self, level: str, message: str) -> None:
        """
        Add a log entry to the log panel.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR)
            message: Log message
        """
        color_map = {
            "DEBUG": "dim",
            "INFO": "cyan",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold red",
        }
        color = color_map.get(level, "white")
        self.log_panel.write(f"[{color}]{level}[/{color}] {message}")
    
    def update_status(self, message: str) -> None:
        """
        Update the status bar.
        
        Args:
            message: Status message
        """
        self.status_bar.update(message)
        logger.debug(f"Status updated: {message}")
    
    def refresh_project_list(self) -> None:
        """Refresh the project list in the sidebar."""
        try:
            # TODO: Load projects from database
            project_list = self.query_one("#project_list", ListView)
            project_list.clear()
            
            # Placeholder - will be implemented in Step 3
            project_list.append(ListItem(Label("No projects yet")))
            
        except Exception as e:
            logger.error(f"Failed to refresh project list: {e}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "send_btn":
            self.send_message()
        elif event.button.id == "new_project_btn":
            self.action_new_project()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if event.input.id == "user_input":
            self.send_message()
    
    async def send_message(self) -> None:
        """Send the user's message."""
        message = self.user_input.value.strip()
        
        if not message:
            return
        
        # Add user message to chat
        self.add_message("user", message)
        
        # Clear input
        self.user_input.value = ""
        
        # Update status
        self.update_status("Thinking...")
        
        try:
            # Get agent and process message
            agent = get_agent()
            
            # Process message with UI
            response = await agent.process_message_with_ui(message, self)
            
            # Add response to chat
            self.add_message("assistant", response.message)
            
            # Update status based on what happened
            if response.tool_executed:
                if response.tool_result and response.tool_result.success:
                    self.update_status(f"Action completed: {response.tool_name}")
                else:
                    self.update_status("Action failed")
            else:
                self.update_status("Ready")
                
        except Exception as e:
            logger.error(f"Error sending message: {e}", exc_info=True)
            self.add_message("error", f"Error: {e}")
            self.update_status("Error")
    
    def action_quit(self) -> None:
        """Quit the application."""
        logger.info("Jarvis application shutting down")
        self.exit()
    
    def action_clear_logs(self) -> None:
        """Clear the log panel."""
        self.log_panel.clear()
        self.add_log("INFO", "Logs cleared")
    
    def action_new_project(self) -> None:
        """Create a new project."""
        # TODO: Implement project creation dialog
        # This will be implemented in Step 6
        self.add_message("system", "Project creation will be implemented in Step 6")
    
    def watch_current_project(self, old_value: Optional[str], new_value: Optional[str]) -> None:
        """React to project changes."""
        if new_value:
            self.update_status(f"Project: {new_value}")
        else:
            self.update_status("Ready")


if __name__ == "__main__":
    app = JarvisApp()
    app.run()
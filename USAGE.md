# Jarvis AI Assistant - Usage Guide

## Getting Started

Once Jarvis is running, you'll see a terminal interface with:
- **Left sidebar**: Shows your projects
- **Main area**: Chat window where you interact with Jarvis
- **Bottom**: Input box to type messages
- **Right side**: Log panel showing system activity
- **Top**: Status bar showing current state

## Basic Usage

### 1. Chat with Jarvis

Simply type your message in the input box at the bottom and press **Enter** or click **Send**.

**Examples:**
```
Hello, how are you?
What can you help me with?
Tell me about Python programming
```

### 2. Create a Project

Ask Jarvis to create a new project:

```
Create a new project called my-app
```

Jarvis will:
1. Show a confirmation dialog
2. Ask you to approve (press **Y** or click "Yes, Execute")
3. Create the project folder in your workspace

### 3. List Your Projects

```
List all my projects
Show me my projects
What projects do I have?
```

### 4. Work with Files

**Read a file:**
```
Read the README.md file
Show me the contents of main.py
```

**Write to a file:**
```
Write "Hello World" to test.txt
Create a file called notes.md with content "My notes"
```

**List files:**
```
List files in my project
Show me all Python files
```

**Search files:**
```
Search for files containing "import"
Find all .py files
```

### 5. Git Operations

```
Check git status
Show git status for my project
```

### 6. Run Tests**

```
Run tests in my project
Execute the test suite
```

## Keyboard Shortcuts

- **Ctrl+C**: Quit Jarvis
- **Ctrl+L**: Clear the log panel
- **Ctrl+N**: Create a new project (shortcut)
- **Y**: Approve an action (in confirmation dialog)
- **N**: Reject an action (in confirmation dialog)
- **Escape**: Cancel/close dialog

## Understanding the Interface

### Chat Messages

- **Cyan "You:"**: Your messages
- **Green "Jarvis:"**: Jarvis's responses
- **Yellow "System:"**: System notifications
- **Red "Error:"**: Error messages

### Status Bar

Shows current state:
- "Ready" - Waiting for input
- "Thinking..." - Processing your request
- "Action completed: [tool]" - Tool executed successfully
- "Action failed" - Tool execution failed
- "Error" - Something went wrong

### Log Panel

Shows technical details:
- **DEBUG**: Detailed debugging info
- **INFO**: General information
- **WARNING**: Warnings
- **ERROR**: Errors

## Example Session

```
You: Create a new project called web-app

Jarvis: ✓ Action completed: Project 'web-app' created successfully at /home/user/JarvisWorkspace/web-app

You: List files in web-app

Jarvis: No files found in web-app

You: Create a file called index.html in web-app

[Confirmation Dialog appears]
Tool: create_file
Arguments: path: web-app/index.html
Risk Level: [HIGH]

Press Y to approve, N to reject

You: Y

Jarvis: ✓ Action completed: File created successfully: web-app/index.html

You: Write <h1>Hello</h1> to web-app/index.html

[Confirmation Dialog appears]
...

You: List files in web-app

Jarvis: Found 1 file(s) in web-app:
1. web-app/index.html (0.0 KB)
```

## Safety Features

### Confirmation Dialogs

For dangerous operations, Jarvis will show a confirmation dialog:
- **Tool name**: What action will be performed
- **Arguments**: What parameters will be used
- **Risk Level**: LOW, MEDIUM, HIGH, or CRITICAL
- **Options**: Yes, Execute / No, Cancel

**Always review before approving!**

### Blocked Operations

Some operations are completely blocked for safety:
- Deleting files with `rm` or `del`
- System commands like `shutdown`, `reboot`
- Network commands like `curl`, `wget`
- Permission changes like `chmod`, `sudo`

### Path Safety

All file operations are confined to your workspace directory (`~/JarvisWorkspace`). Jarvis cannot access files outside this directory.

## Tips & Best Practices

1. **Be specific**: Instead of "create a file", say "create a file called app.py in my-project"

2. **Use project names**: When working in a project, mention it:
   ```
   Read config.py in my-project
   ```

3. **Check before approving**: Always review the confirmation dialog before pressing Y

4. **Use natural language**: Jarvis understands conversational requests:
   ```
   Can you help me create a simple Python script?
   I need a project for my web application
   ```

5. **Ask for clarification**: If unsure, ask Jarvis:
   ```
   What tools can you use?
   What projects do I have?
   ```

## Common Issues

### "Cannot connect to Ollama"
- Make sure Ollama is running: `ollama serve`
- Check if model is pulled: `ollama list`
- Verify URL in config.py is correct

### "Path is outside workspace"
- All files must be created within the workspace
- Use relative paths or project names
- Don't try to access files with `../` or absolute paths outside workspace

### "Command not allowed"
- Only safe commands are allowed
- Jarvis cannot run arbitrary shell commands
- Use the available tools instead

### UI looks broken
- Use Windows Terminal, PowerShell, or Command Prompt
- Resize terminal window if needed
- Restart Jarvis if issues persist

## Next Steps

1. **Create your first project**: "Create a project called test-project"
2. **Explore file operations**: Try creating, reading, and listing files
3. **Check git status**: Initialize a git repo and check status
4. **Have a conversation**: Ask Jarvis questions about programming

## Getting Help

- Check logs in `jarvis/logs/` for technical details
- Review `README.md` for architecture overview
- See `WSL_SETUP.md` or `WINDOWS_SETUP.md` for setup issues
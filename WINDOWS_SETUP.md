# Jarvis AI Assistant - Windows Setup Guide

This guide will help you set up and run Jarvis on Windows 10/11.

## Prerequisites

- Windows 10 or 11
- Python 3.12 or higher
- Ollama (for local AI)

## Step 1: Install Python

1. Download Python from https://www.python.org/downloads/windows/
2. Run the installer
3. **IMPORTANT**: Check "Add Python to PATH" during installation
4. Verify installation by opening Command Prompt and running:
   ```cmd
   python --version
   ```

## Step 2: Install Ollama

1. Download Ollama from https://ollama.ai/download/windows
2. Run the installer
3. After installation, open Command Prompt and pull a model:
   ```cmd
   ollama pull llama2
   ```
4. Verify Ollama is running:
   ```cmd
   ollama list
   ```

## Step 3: Download/Clone Jarvis

1. Extract the ZIP file to a folder (e.g., `C:\Users\YourName\Documents\jarvis`)
2. Or clone with Git:
   ```cmd
   git clone <repository-url>
   cd jarvis
   ```

## Step 4: Install Dependencies

1. Open Command Prompt in the jarvis folder
2. Install required packages:
   ```cmd
   pip install -r requirements.txt
   ```

If you get permission errors, try:
```cmd
pip install --user -r requirements.txt
```

## Step 5: Run Jarvis

### Option A: Using Command Prompt
```cmd
cd jarvis
python -m jarvis.app
```

### Option B: Using PowerShell
```powershell
cd jarvis
python -m jarvis.app
```

### Option C: Create a Batch File (Recommended)

Create a file called `run_jarvis.bat` in the jarvis folder with this content:

```batch
@echo off
echo Starting Jarvis AI Assistant...
python -m jarvis.app
pause
```

Double-click `run_jarvis.bat` to run Jarvis.

## Step 6: Using Jarvis

1. The terminal UI will open
2. Type your message in the input box at the bottom
3. Press Enter or click "Send"
4. Jarvis will respond and can perform actions with your approval

## Troubleshooting

### Python not found
- Make sure Python is installed and added to PATH
- Try restarting Command Prompt after installation
- Use `py` instead of `python`:
  ```cmd
  py -m jarvis.app
  ```

### Ollama connection errors
- Make sure Ollama is running (check system tray)
- Test with: `curl http://localhost:11434/api/tags`
- If curl fails, restart Ollama

### Permission errors
- Run Command Prompt as Administrator
- Or install packages with `--user` flag:
  ```cmd
  pip install --user -r requirements.txt
  ```

### Textual UI issues
- Make sure you're using a modern terminal (Windows Terminal, PowerShell, or Command Prompt)
- If the UI looks broken, try Windows Terminal from Microsoft Store

### Module import errors
- Make sure you're in the jarvis directory
- Try running from the parent directory:
  ```cmd
  cd ..
  python -m jarvis.app
  ```

## Configuration

To customize Jarvis, edit `jarvis/config.py`:

```python
# Change workspace location
workspace_root: Path = Path("C:/Users/YourName/Documents/MyProjects")

# Change Ollama model
ollama_model: str = "llama2"  # or "mistral", "codellama", etc.
```

## Uninstalling

1. Delete the jarvis folder
2. Uninstall Ollama from Windows Settings > Apps
3. (Optional) Uninstall Python from Windows Settings > Apps

## Notes

- First run may take a minute as Ollama loads the model
- The workspace folder will be created at `~/JarvisWorkspace`
- Logs are stored in `jarvis/logs/`
- Database is stored at `~/JarvisWorkspace/jarvis.db`

## Getting Help

If you encounter issues:
1. Check the logs in `jarvis/logs/`
2. Ensure Ollama is running: `ollama list`
3. Verify Python version: `python --version`
4. Check that all dependencies are installed: `pip list`
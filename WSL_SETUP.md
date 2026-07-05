# Jarvis AI Assistant - WSL Setup Guide

This guide will help you set up and run Jarvis on Windows Subsystem for Linux (WSL).

## Prerequisites

- Windows 10/11 with WSL2 installed
- Ubuntu or other Linux distribution in WSL
- Python 3.12 or higher
- Ollama (for local AI)

## Step 1: Set Up WSL (if not already done)

If you don't have WSL installed:

```bash
# In Windows Command Prompt or PowerShell (as Administrator)
wsl --install
```

This will install WSL2 and Ubuntu by default. Restart your computer when prompted.

## Step 2: Install Python in WSL

1. Open WSL terminal (search for "Ubuntu" in Windows Start Menu)
2. Update package list:
   ```bash
   sudo apt update
   sudo apt upgrade -y
   ```

3. Install Python 3.12:
   ```bash
   sudo apt install python3.12 python3.12-venv python3-pip -y
   ```

4. Verify installation:
   ```bash
   python3.12 --version
   ```

## Step 3: Install Ollama in WSL

1. Install Ollama:
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. Pull a model:
   ```bash
   ollama pull llama2
   ```

3. Verify Ollama is running:
   ```bash
   ollama list
   ```

**Note**: Ollama in WSL will be accessible from Windows at `http://localhost:11434`

## Step 4: Access Your Windows Files from WSL

Your Windows files are accessible in WSL at `/mnt/c/`. For example:
- Windows: `C:\Users\YourName\Documents\jarvis`
- WSL: `/mnt/c/Users/YourName/Documents/jarvis`

## Step 5: Navigate to Jarvis Directory

```bash
# If you cloned/extracted to Windows Documents
cd /mnt/c/Users/YourName/Documents/jarvis

# Or if you cloned directly in WSL home directory
cd ~/jarvis
```

## Step 6: Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python3.12 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

## Step 7: Install Dependencies

```bash
# If using virtual environment
pip install -r requirements.txt

# If not using virtual environment
pip3 install -r requirements.txt
```

## Step 8: Run Jarvis

```bash
# If using virtual environment
python -m jarvis.app

# If not using virtual environment
python3 -m jarvis.app
```

## Step 9: Create a Launch Script (Optional)

Create a file called `run_jarvis.sh` in the jarvis folder:

```bash
#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run Jarvis
python -m jarvis.app
```

Make it executable:
```bash
chmod +x run_jarvis.sh
```

Run it:
```bash
./run_jarvis.sh
```

## Alternative: Run from Windows

You can also run Jarvis directly from Windows Command Prompt or PowerShell:

```cmd
# In Windows Command Prompt
cd C:\Users\YourName\Documents\jarvis
python -m jarvis.app
```

This works because WSL and Windows can access the same files.

## Configuration

### Option 1: Edit config.py directly

Edit `jarvis/config.py` to customize settings:

```python
# Change workspace location (WSL path)
workspace_root: Path = Path.home() / "JarvisWorkspace"

# Or use Windows path from WSL
workspace_root: Path = Path("/mnt/c/Users/YourName/Documents/MyProjects")

# Ollama settings (use localhost since Ollama in WSL is accessible from Windows)
ollama_url: str = "http://localhost:11434"
ollama_model: str = "llama2"
```

### Option 2: Use Environment Variables

Create a `.env` file in the jarvis folder:
```bash
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama2
WORKSPACE_ROOT=/home/yourname/JarvisWorkspace
```

## Troubleshooting

### Python command not found
```bash
# Use python3 instead of python
python3 -m jarvis.app

# Or create an alias
echo "alias python=python3" >> ~/.bashrc
source ~/.bashrc
```

### Ollama connection errors
```bash
# Check if Ollama is running
ollama list

# Start Ollama service
sudo systemctl start ollama

# Enable Ollama to start on boot
sudo systemctl enable ollama
```

### Permission errors
```bash
# Make sure you own the files
sudo chown -R $USER:$USER /path/to/jarvis

# Or run with appropriate permissions
chmod +x run_jarvis.sh
```

### Display issues
- WSL doesn't support the full Textual UI by default
- Use Windows Terminal or PowerShell to run Jarvis from Windows side
- Or use a Linux terminal emulator like Windows Terminal

### Import errors
```bash
# Make sure you're in the jarvis directory
cd /path/to/jarvis

# Try running from parent directory
cd ..
python3 -m jarvis.app
```

## Performance Tips

1. **Use WSL2** (not WSL1) for better performance
2. **Store project files in WSL filesystem** (`~/`) for better I/O performance
3. **Use virtual environment** to avoid permission issues
4. **Keep Ollama running** in background for faster responses

## Accessing Files

### From WSL to Windows:
```bash
# Access Windows C: drive
cd /mnt/c/

# Access specific Windows folder
cd /mnt/c/Users/YourName/Documents
```

### From Windows to WSL:
```bash
# In Windows Command Prompt
\\wsl$\Ubuntu\home\yourname\jarvis
```

## Uninstalling

```bash
# Remove Jarvis
rm -rf ~/jarvis
rm -rf ~/JarvisWorkspace

# Remove Ollama (optional)
curl -fsSL https://ollama.ai/install.sh | uninstall

# Remove Python packages (optional)
sudo apt remove python3.12 python3.12-venv python3-pip
```

## Notes

- First run may take a minute as Ollama loads the model
- The workspace folder will be created at `~/JarvisWorkspace` in WSL
- Logs are stored in `jarvis/logs/`
- Database is stored at `~/JarvisWorkspace/jarvis.db`
- Ollama in WSL is accessible from Windows applications at `http://localhost:11434`

## Getting Help

If you encounter issues:
1. Check the logs in `jarvis/logs/`
2. Ensure Ollama is running: `ollama list`
3. Verify Python version: `python3 --version`
4. Check that all dependencies are installed: `pip list`
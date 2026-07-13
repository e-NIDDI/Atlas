# Jarvis AI Assistant — Complete Codebase Review and Overhaul Plan

## Executive Summary

Jarvis is a promising local AI assistant built on Ollama, but it is non-functional as a file-system-aware AI secretary. The codebase has **5 architectural layers** (brain, cli, memory, safety, tools) with ~4,200 lines of code, yet it cannot perform any real work because:

1. **No actual file system tools** exist — `read_file`, `write_file`, `delete_file`, `append_file`, etc. are declared as tool *names* in the system prompt but the underlying implementations are non-existent or stubs
2. **No document parsing** — PDFs, DOCX, CSV, Markdown files cannot be read
3. **No RAG system** — no embeddings, no vector database, no semantic search
4. **No memory architecture** — the "memory" layer is just an SQLite action log, no long-term/short-term/episodic memory
5. **Fundamental tool name conflicts** — `SearchFilesTool` is defined in BOTH `tools/files.py` and `tools/search.py`, causing silent overwrites during registration
6. **Agent loop is non-functional for small models** — the default `qwen2.5:1.5b` is in `SMALL_MODELS` but the buffered path bypasses the LLM entirely for file/tool requests, relying on brittle regex intent detection that barely handles 5 patterns
7. **The system prompt declares tools that don't exist** — `delete_file`, `append_file`, `rename_item`, `move_item`, `copy_item`, `create_folder`, `get_file_metadata`, `summarize_document` are never implemented
8. **No secretary features** — no task tracking, note taking, project memory, or document summarization
9. **No deployment scripts** — `pyproject.toml` is incorrectly configured (packages list is wrong, missing dependencies)

---

## Current Problems (Detailed)

### CRITICAL — Tool Name Collision
```
tools/files.py:       class SearchFilesTool(BaseTool)  → name = "search_files"
tools/search.py:      class SearchFilesTool(BaseTool)  → name = "search_files"
```
The second registration silently overwrites the first. The `search_files` tool in `files.py` uses `file_manager.search_files()` which does **glob-based file name matching**. The one in `search.py` uses `search_manager.search_by_pattern()` which does **regex-based matching**. Both register under the same name. The registry keeps whichever registers last (from `register_tools.py` line 25 and 33).

### CRITICAL — No Actual Filesystem Tools
Despite declaring these in the system prompt and parser:
- `read_file(path)` — works, reads text files only
- `write_file(path, content)` — works, writes text files only
- `create_file(path)` — works, creates empty files
- `delete_file(path)` — **MISSING** (declared in prompt, not implemented)
- `append_file(path, content)` — **MISSING**
- `create_folder(path)` → `create_directory(path)` — **MISSING**
- `delete_folder(path)` → `delete_directory(path)` — **MISSING**
- `rename_item(old_path, new_path)` — **MISSING**
- `move_item(source, destination)` — **MISSING**
- `copy_item(source, destination)` — **MISSING**
- `get_file_metadata(path)` — **MISSING**

Only 3 of 11 required filesystem tools are implemented.

### CRITICAL — No Document Intelligence
The system prompt says Jarvis can read/summarize documents, but:
- No PDF parser (no `pypdf` or `pdfminer` dependency)
- No DOCX parser (no `python-docx`)
- No CSV parser with intelligence
- No document summarization logic
- No content extraction pipeline
- When asked to "read this PDF", the `read_file` tool calls `.read_text()` which will **throw a UnicodeDecodeError**

### CRITICAL — No RAG System
- No embeddings model integration
- No vector database (ChromaDB, FAISS, etc.)
- No document chunking
- No semantic search
- No retrieval-augmented generation pipeline
- `SearchManager.search_content()` uses **regex line-by-line grep**, not semantic search

### CRITICAL — No Memory Architecture
What exists: SQLite tables for `actions`, `conversation`, `projects`, `settings`.
What's missing:
- **Short-term memory** — conversation window management across sessions
- **Long-term memory** — persistent semantic knowledge about user/projects
- **Episodic memory** — remembering past actions and their outcomes
- **Project memory** — tracking what was discussed about each project
- **Working memory** — current task state, pending operations

The current `HistoryManager` logs actions to SQLite but **nothing reads context back into prompts**. The agent never gets historical context.

### CRITICAL — pyproject.toml Configuration Errors
```toml
package-dir = {"jarvis" = "."}
```
This is wrong. In the jarvis directory, the structure is:
```
/ (treated as jarvis/)
  brain/
  cli/
  memory/
  safety/
  tools/
  ui/
```

But `packages = ["jarvis", "jarvis.brain", ...]` means setuptools looks for `jarvis/jarvis/`. This explains why the package probably doesn't install correctly.

### HIGH — Intent Detection Is Fragile
`brain/intent.py` has 15 regex patterns for detecting tool intents. This is a brittle fallback for small models, but:
- Only handles `create_project`, `list_projects`, `read_file` (with extension), `list_files`, `git_status`
- Cannot handle: delete, rename, move, copy, search, summarize, or any advanced operation
- Pattern `read_file` requires a file extension (`\w+`), misses files without extensions or with multiple dots
- The `create_project` patterns have complex overlapping regexes that can produce incorrect extractions

### HIGH — Async Event Loop Issues
- `cli/app.py:main()` calls `asyncio.run(run_chat(...))` 
- `run_chat()` calls `await agent.process_message()` which is an `AsyncGenerator`
- The `process_message` generator is consumed correctly, but if there's a nested event loop (e.g., from an existing running loop), `asyncio.run()` will crash

### HIGH — No Permission/Safety System Integration
- `SafetyValidator` validates tool requests but `ToolDispatcher` only checks validation result — it never calls `validate_command()` for command tools
- The `SafetyWhitelist` blocks `curl`, `wget` but the `CommandManager` in `tools/commands.py` has its own separate whitelist that says `curl`, `wget` are NOT in allowed commands — two different whitelists that disagree
- No user-defined safe directories support despite being listed in requirements
- No sandboxing for file operations

### MEDIUM — Code Quality Issues
1. **`tools/__init__.py` line 29**: `SearchFilesTool` imported from BOTH `files` and `search` modules — only one survives
2. **`brain/chat.py` line 133**: `send_message` is async generator but type hint says `AsyncGenerator[str, None]` — correct, but `chat_complete` in ollama.py collects from generator with non-streaming flag but the generator still yields normally
3. **`brain/parser.py` line 231-243**: `validate_tool_request` has a hardcoded tool list that differs from both the system prompt AND `register_tools.py` — contains `search_content`, `run_tests` that are registered, but missing `delete_file`, `append_file`, etc.
4. **`brain/prompts.py`**: `format_chat_prompt()` is **never called** — unused dead code
5. **`memory/database.py`**: `Database` has no connection pooling, creates connection on each operation
6. **`safety/whitelist.py`**: `.js` is in BOTH `safe_extensions` AND `dangerous_extensions` — contradiction
7. **`cli/app.py` line 11**: Imports `cli_confirm` but `cli/approval.py` also defines `cli_confirm` — unused import in display.py

---

## Missing Components

| Component | Current State | Required State |
|-----------|--------------|----------------|
| File Read | Text-only (`.read_text()`) | PDF, DOCX, CSV, MD, TXT, binary detection |
| File Write | Text-only | Text + append + binary |
| File Delete | Not implemented | With trash/recycle + confirmation |
| Folder Create | Via `create_project` only | Generic `create_folder(path)` |
| Folder Delete | Via `delete_project` only | Generic `delete_folder(path)` |
| Rename | Project-only | Generic `rename_item(old, new)` |
| Move | Not implemented | `move_item(src, dst)` |
| Copy | Not implemented | `copy_item(src, dst)` |
| Search Files | Glob + regex (two conflicting implementations) | Unified glob + regex |
| Search Content | Naive grep (regex line scan) | Semantic + keyword + regex |
| Document Parsing | None | PDF, DOCX, CSV, MD, TXT, code |
| Document Summarization | None | LLM-based summarization |
| RAG | None | Chunking → Embeddings → Vector DB → Semantic Search → Context Retrieval |
| Short-Term Memory | ConversationHistory (in-memory, 50 turns) | Session-aware, with summarization |
| Long-Term Memory | SQLite action logs (unused by agent) | Vector-indexed semantic memory |
| Project Memory | None | Per-project context, notes, decisions |
| Task Tracking | None | Task creation, status, prioritization |
| Agent Planning | None (single-shot tool calls) | Multi-step plan execution |
| Safety Layer | Path validation only | Sandboxing, audit log, user-defined rules |
| Function Calling | JSON-in-prompt (fragile) | Structured tool definitions with proper schema |

---

## Architecture Review

### Current Architecture
```
app.py → cli/app.py → brain/agent.py → brain/chat.py → brain/ollama.py (Ollama API)
                  ↓
         tools/dispatcher.py → tools/registry.py → tools/*.py
                  ↓
         safety/validator.py → safety/paths.py, safety/whitelist.py
                  ↓
         memory/history.py → memory/database.py
```

**Flaws**:
1. **No separation of concerns** — `brain/agent.py` has both orchestration logic AND LLM interaction
2. **No plugin system** — tools are hardcoded in `register_tools.py`
3. **No pipeline for document processing**
4. **No context injection** — history is stored but never fed into LLM prompts
5. **No error recovery** — any exception terminates the current interaction
6. **No streaming for buffered models** — the buffer path just concatenates and yields at end

### Proposed Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    CLI Layer (jarvis.cli)                │
│  app.py (entry) → display.py → approval.py              │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                 Agent Layer (jarvis.agent)               │
│  agent.py (main loop) → planner.py (multi-step)         │
│  → executor.py → validator.py (tool validation)         │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                LLM Layer (jarvis.llm)                    │
│  ollama.py → prompts.py → parser.py → errors.py         │
│  → function_calling.py (structured tool definitions)    │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│              Tools Layer (jarvis.tools)                  │
│  registry.py → dispatcher.py                            │
│  filesystem.py → documents.py → search.py               │
│  projects.py → commands.py → secretary.py               │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│           Memory & RAG Layer (jarvis.memory)             │
│  database.py → history.py                               │
│  short_term.py → long_term.py → episodic.py             │
│  embeddings.py → vector_store.py → rag.py               │
│  project_memory.py → task_tracker.py                    │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│              Safety Layer (jarvis.safety)                │
│  paths.py → validator.py → whitelist.py                 │
│  permissions.py → audit.py → sandbox.py                 │
└─────────────────────────────────────────────────────────┘
```

---

## Security Review

### Critical Issues
1. **Path traversal in `FileManager.resolve_path()`** — relative paths with `../../../etc/passwd` resolve but get caught by the relative_to check. However, symlinks within the workspace are not resolved, so a symlink to `/etc/passwd` inside workspace would bypass the check.

2. **Command execution in `tools/commands.py`** — `subprocess.run()` with `shell=False` and explicit command array is safe, but the whitelist only has 11 allowed commands and the validation function has a fallback that allows restricted commands:
   ```python
   # For now, we'll allow restricted commands but log them
   return True, None
   ```

3. **No input sanitization on file content** — writing untrusted content to files could include escape sequences or control characters.

4. **Two conflicting permission systems** — `safety/whitelist.py` and `tools/commands.py:CommandManager` both have whitelists that disagree.

5. **SQL injection potential** — `memory/database.py` uses parameterized queries (safe), but `execute_query` has broad exception handling that could mask injection attempts.

### Acceptable Issues
- Workspace confinement with `relative_to` is mostly effective
- File size limits (10MB) prevent memory exhaustion
- Operation timeout (30-60s) prevents hanging
- The confirmation system works but is bypassable with `--yes`

---

## Recommended Architecture

### Layer 1: Core & Config
- `config.py` — extended with DB paths, embedding model, safe directories
- `logger.py` — extended with structured logging (JSON logs)
- `exceptions.py` — hierarchical exception classes

### Layer 2: LLM Integration
- `llm/client.py` — Ollama + OpenAI-compatible API clients
- `llm/prompts.py` — prompt templates with dynamic context injection
- `llm/parser.py` — JSON extraction from model output
- `llm/function_calling.py` — structured function definitions for model

### Layer 3: Tools (Expanded)
- `tools/filesystem.py` — ALL filesystem operations (read, write, append, delete, create_folder, delete_folder, rename, move, copy, list, metadata)
- `tools/documents.py` — PDF, DOCX, CSV, MD, TXT parsing with metadata extraction
- `tools/search.py` — unified search (glob, regex, fuzzy, content)
- `tools/secretary.py` — notes, tasks, project organization, summaries

### Layer 4: Memory & RAG
- `memory/short_term.py` — conversation buffer with summarization
- `memory/long_term.py` — SQLite-backed semantic memory
- `memory/episodic.py` — action/outcome recall
- `memory/embeddings.py` — local embeddings via Ollama or sentence-transformers
- `memory/vector_store.py` — ChromaDB or simple numpy FAISS
- `memory/rag.py` — retrieval pipeline with chunking

### Layer 5: Agent
- `agent/planner.py` — multi-step plan decomposition
- `agent/executor.py` — step-by-step execution with verification
- `agent/agent.py` — main loop with state machine
- `agent/context.py` — context assembly from memory

### Layer 6: Safety
- `safety/permissions.py` — user-defined safe directories, file type rules
- `safety/audit.py` — comprehensive action auditing

---

Now I will implement every piece of code needed.

## Files to Modify:
1. `pyproject.toml` — fix package config, add dependencies
2. `requirements.txt` — add all required packages
3. `config.py` — add new configuration fields
4. `brain/prompts.py` — update tool descriptions
5. `brain/parser.py` — update tool validation list
6. `tools/register_tools.py` — add new tool registrations
7. `tools/files.py` → RENAME to `tools/filesystem.py` — add all missing operations
8. `cli/app.py` — add new commands
9. `tools/__init__.py` — update exports

## New Files to Create:
1. `tools/documents.py` — document intelligence (PDF, DOCX, CSV parsing)
2. `tools/secretary.py` — secretary features (notes, tasks, project memory)
3. `memory/embeddings.py` — embedding generation
4. `memory/vector_store.py` — vector database
5. `memory/rag.py` — RAG pipeline
6. `memory/project_memory.py` — project-specific memory
7. `safety/permissions.py` — permission system
8. `safety/audit.py` — audit logging
9. `config.yaml` — configuration file template
10. `INSTALL.md` — deployment instructions

## Code Fix Implementation:

### Fix 1: pyproject.toml — fix package structure
"""Jarvis CLI — interactive terminal assistant."""

import argparse
import asyncio
import sys
from typing import Optional

from jarvis.brain.agent import get_agent
from jarvis.brain.ollama import OllamaClient
from jarvis.cli.approval import cli_confirm
from jarvis.cli.display import (
    clear_thinking,
    print_assistant,
    print_banner,
    print_error,
    print_help,
    print_stream_chunk,
    print_stream_end,
    print_stream_start,
    print_system,
    print_thinking,
    print_user,
    c,
    CYAN,
    BOLD,
)
from jarvis.config import config
from jarvis.logger import logger, set_console_log_level
from jarvis.tools.dispatcher import ToolDispatcher
from jarvis.tools.projects import project_manager
from jarvis.tools.register_tools import register_all_tools


SLASH_COMMANDS = {"/help", "/clear", "/projects", "/tools", "/status", "/quit", "/exit"}


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="jarvis",
        description="Jarvis — local AI workspace assistant powered by Ollama",
    )
    parser.add_argument(
        "-m", "--model",
        help=f"Ollama model to use (default: {config.ollama_model})",
    )
    parser.add_argument(
        "-w", "--workspace",
        help=f"Workspace directory (default: {config.workspace_root})",
    )
    parser.add_argument(
        "--ollama-url",
        help=f"Ollama API URL (default: {config.ollama_url})",
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Auto-approve tool actions without prompting",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show log output during chat",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="Set logging level",
    )

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("chat", help="Start interactive chat (default)")

    ask_parser = subparsers.add_parser("ask", help="Send a single message and exit")
    ask_parser.add_argument("message", help="Message to send to Jarvis")

    subparsers.add_parser("status", help="Check Ollama connection and configuration")
    subparsers.add_parser("tools", help="List available tools")

    return parser


def apply_config(args: argparse.Namespace) -> None:
    """Apply CLI overrides to global config."""
    if args.model:
        config.ollama_model = args.model
    if args.workspace:
        config.workspace_root = __import__("pathlib").Path(args.workspace).expanduser().resolve()
        config.workspace_root.mkdir(parents=True, exist_ok=True)
    if args.ollama_url:
        config.ollama_url = args.ollama_url
    if args.log_level:
        config.log_level = args.log_level
        logger.setLevel(getattr(__import__("logging"), args.log_level))

    # Chat mode: quiet logs by default, unless --verbose
    command = getattr(args, "command", None) or "chat"
    if args.verbose:
        set_console_log_level("INFO")
    elif command in ("chat", "ask"):
        set_console_log_level("ERROR")
    else:
        set_console_log_level("WARNING")


async def check_status() -> bool:
    """Check Ollama status and print info."""
    client = OllamaClient()
    try:
        connected = await client.check_connection()
        models = await client.list_models() if connected else []
        model_details = await client.get_model_details() if connected else []

        print(c("Status", BOLD + CYAN))
        print(f"  Ollama URL:  {config.ollama_url}")
        print(f"  Connected:   {'yes' if connected else 'no'}")
        print(f"  Model:       {config.ollama_model}")
        print(f"  Workspace:   {config.workspace_root}")

        model_ok = True
        if connected:
            if models:
                print(f"  Available:   {', '.join(models)}")
                if config.ollama_model not in models and not any(
                    config.ollama_model in m for m in models
                ):
                    model_ok = False

                # RAM warning for large models
                _warn_if_low_ram(model_details, config.ollama_model)
            else:
                model_ok = False

        if not connected:
            print()
            print_error("Cannot connect to Ollama. Is it running? Try: ollama serve")
            return False

        if not model_ok:
            print()
            if models:
                print_error(
                    f"Model '{config.ollama_model}' not found. "
                    f"Run: ollama pull {config.ollama_model}"
                )
            else:
                print_error("No models installed. Run: ollama pull tinyllama")
            return False

        return True
    finally:
        await client.close()


def _warn_if_low_ram(model_details: list, target_model: str) -> None:
    """Warn if the target model is likely too large for available RAM."""
    try:
        import os
        avail_bytes = os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
        avail_gb = avail_bytes / (1024 ** 3)
    except (AttributeError, ValueError, OSError):
        return

    for m in model_details:
        name = m.get("name", "")
        base = name.split(":")[0]
        if target_model not in name and target_model != base:
            continue
        size_gb = m.get("size", 0) / (1024 ** 3)
        needed_gb = size_gb + 1.5
        if needed_gb > avail_gb:
            print()
            print_system(
                f"RAM warning: {name} needs ~{needed_gb:.1f}GB but only "
                f"{avail_gb:.1f}GB is available — it will likely crash.\n"
                f"  Fix: ollama pull tinyllama  →  jarvis -m tinyllama"
            )
        return


def list_tools() -> None:
    """List available tools."""
    dispatcher = ToolDispatcher()
    tools = dispatcher.get_available_tools()

    print(c("Available Tools", BOLD + CYAN))
    for name in sorted(tools):
        info = dispatcher.get_tool_info(name)
        if info:
            confirm = " [needs approval]" if info.get("requires_confirmation") else ""
            print(f"  • {name}{confirm}")
            print(f"    {info.get('description', '')}")
    print()


def list_projects() -> None:
    """List workspace projects."""
    project_manager.load_projects()
    projects = project_manager.list_projects()

    if not projects:
        print_system("No projects yet. Try: \"Create a project called my-app\"")
        return

    print(c("Projects", BOLD + CYAN))
    for i, project in enumerate(projects, 1):
        print(f"  {i}. {project.name}  ({project.path})")
    print()


async def handle_slash_command(command: str, agent) -> bool:
    """
    Handle slash commands.

    Returns:
        True to continue chat loop, False to exit.
    """
    cmd = command.lower().strip()

    if cmd in ("/quit", "/exit"):
        return False

    if cmd == "/help":
        print_help()
    elif cmd == "/clear":
        agent.clear_history()
        print_system("Conversation history cleared.")
    elif cmd == "/projects":
        list_projects()
    elif cmd == "/tools":
        list_tools()
    elif cmd == "/status":
        await check_status()
    else:
        print_error(f"Unknown command: {command}. Type /help for options.")

    return True


async def process_message(
    message: str,
    agent,
    auto_approve: bool = False,
    stream: bool = True,
) -> str:
    """Process a user message and display the response."""
    confirm_fn = None if auto_approve else cli_confirm

    if stream:
        print_thinking()
        full_response = ""
        tool_handled = False

        async for chunk in agent.process_message(
            message,
            auto_approve=auto_approve,
            confirm_fn=confirm_fn,
        ):
            if not tool_handled:
                clear_thinking()
                print_stream_start()
                tool_handled = True
            print_stream_chunk(chunk)
            full_response += chunk

        if tool_handled:
            print_stream_end()
        else:
            clear_thinking()

        return full_response

    response = await agent.process_message_complete(
        message,
        auto_approve=auto_approve,
        confirm_fn=confirm_fn,
    )
    print_assistant(response.message)
    return response.message


async def run_chat(auto_approve: bool = False, verbose: bool = False) -> None:
    """Run the interactive chat loop."""
    if not verbose:
        print_banner()

    ok = await check_status()
    if not ok:
        print_system("Starting anyway — Ollama may become available later.")

    register_all_tools()
    project_manager.load_projects()
    agent = get_agent()

    if not verbose:
        print_system('Type a message or /help for commands. Ctrl+C or /quit to exit.')
        print()

    try:
        while True:
            try:
                user_input = input(c("› ", BOLD + CYAN)).strip()
            except EOFError:
                print()
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                if not await handle_slash_command(user_input, agent):
                    break
                continue

            print_user(user_input)

            try:
                await process_message(user_input, agent, auto_approve=auto_approve)
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                print_error(str(e))

            print()

    except KeyboardInterrupt:
        print()
        print_system("Goodbye!")
    finally:
        await agent.close()


async def run_ask(message: str, auto_approve: bool = False) -> int:
    """Run a single message and exit."""
    ok = await check_status()
    if not ok:
        return 1

    register_all_tools()
    project_manager.load_projects()
    agent = get_agent()

    try:
        print_user(message)
        await process_message(
            message,
            agent,
            auto_approve=auto_approve,
            stream=False,
        )
        return 0
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        print_error(str(e))
        return 1
    finally:
        await agent.close()


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    apply_config(args)

    command = args.command or "chat"

    try:
        if command == "status":
            ok = asyncio.run(check_status())
            return 0 if ok else 1
        elif command == "tools":
            register_all_tools()
            list_tools()
            return 0
        elif command == "ask":
            return asyncio.run(run_ask(args.message, auto_approve=args.yes))
        else:
            asyncio.run(run_chat(auto_approve=args.yes, verbose=args.verbose))
            return 0
    except KeyboardInterrupt:
        print()
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print_error(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

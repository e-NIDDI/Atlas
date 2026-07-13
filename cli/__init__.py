"""CLI layer for Jarvis."""


def main(argv=None):
    """Run the CLI without importing it while this package initializes."""
    from jarvis.cli.app import main as cli_main

    return cli_main(argv)


__all__ = ["main"]

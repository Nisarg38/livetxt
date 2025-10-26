"""CLI for LiveTxt runtime."""

import asyncio
import importlib.util
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click

from .config import LiveTxtConfig
from .runtime import run_worker

if TYPE_CHECKING:
    from livekit.agents import WorkerOptions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def run_app(opts: "WorkerOptions") -> None:
    """
    Run a LiveKit agent in SMS mode using LiveTxt.

    This function provides a drop-in replacement for livekit.agents.cli.run_app()
    that enables SMS functionality via the LiveTxt gateway.

    Configuration is loaded from environment variables:
    - LIVETXT_GATEWAY_URL: URL of the LiveTxt gateway (required)
    - LIVETXT_API_KEY: API key for authentication (required)

    Example:
        ```python
        from livekit.agents import WorkerOptions, cli
        from livetxt import cli as livetxt_cli

        if __name__ == "__main__":
            # Voice mode (original)
            # cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

            # SMS mode (LiveTxt)
            livetxt_cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
        ```

    Args:
        opts: WorkerOptions containing the entrypoint function and configuration
    """
    # Extract entrypoint function
    entrypoint = opts.entrypoint_fnc

    if not entrypoint:
        logger.error("❌ WorkerOptions.entrypoint_fnc is required")
        sys.exit(1)

    # Load configuration from environment
    try:
        config = LiveTxtConfig.from_env()
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        logger.info("💡 Set LIVETXT_GATEWAY_URL and LIVETXT_API_KEY environment variables")
        sys.exit(1)

    # Log startup info
    logger.info("🚀 Starting LiveTxt SMS worker")
    logger.info(f"🌐 Gateway: {config.gateway_url}")
    logger.info("📱 SMS mode enabled - agent will respond to text messages")

    # Run worker
    try:
        asyncio.run(run_worker(config, entrypoint))
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        sys.exit(1)


def load_agent_entrypoint(agent_file: str):
    """
    Load agent entrypoint function from a Python file.

    Looks for a function named 'entrypoint' in the file.
    """
    agent_path = Path(agent_file)

    if not agent_path.exists():
        raise FileNotFoundError(f"Agent file not found: {agent_file}")

    # Load the module
    spec = importlib.util.spec_from_file_location("agent_module", agent_path)
    if not spec or not spec.loader:
        raise ImportError(f"Could not load agent file: {agent_file}")

    module = importlib.util.module_from_spec(spec)
    sys.modules["agent_module"] = module
    spec.loader.exec_module(module)

    # Find entrypoint function
    if not hasattr(module, "entrypoint"):
        raise AttributeError(f"Agent file must define an 'entrypoint' function: {agent_file}")

    return module.entrypoint


@click.group()
def cli():
    """LiveTxt - Run LiveKit agents over SMS."""
    pass


@cli.command()
@click.argument("agent_file", type=click.Path(exists=True))
@click.option(
    "--gateway-url",
    envvar="LIVETXT_GATEWAY_URL",
    help="Gateway URL",
    required=True,
)
@click.option(
    "--api-key",
    envvar="LIVETXT_API_KEY",
    help="API key for authentication",
    required=True,
)
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Log level",
)
def run(agent_file: str, gateway_url: str, api_key: str, log_level: str):
    """
    Run an agent worker.

    AGENT_FILE is the path to your agent Python file containing an 'entrypoint' function.

    Example:
        livetxt run agent.py --gateway-url https://gateway.example.com --api-key sk_xxx
    """
    # Set log level
    logging.getLogger().setLevel(getattr(logging, log_level))

    # Load agent entrypoint
    click.echo(f"📦 Loading agent from {agent_file}")
    try:
        entrypoint = load_agent_entrypoint(agent_file)
    except Exception as e:
        click.echo(f"❌ Error loading agent: {e}", err=True)
        sys.exit(1)

    # Create config
    config = LiveTxtConfig(gateway_url=gateway_url, api_key=api_key)

    click.echo(f"🌐 Connecting to {gateway_url}")

    # Run worker
    try:
        asyncio.run(run_worker(config, entrypoint))
    except KeyboardInterrupt:
        click.echo("\n👋 Shutting down")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def version():
    """Show version information."""
    from . import __version__

    click.echo(f"LiveTxt version {__version__}")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()

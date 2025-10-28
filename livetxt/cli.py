from __future__ import annotations

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


def run_app(opts: WorkerOptions) -> None:
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


async def run_worker_with_agent_class(config: LiveTxtConfig, agent_class: type):
    """
    Run worker with an Agent class (automatic mode).
    
    This creates an entrypoint wrapper that:
    1. Instantiates the agent class
    2. Automatically captures and restores state
    3. Returns state to gateway
    """
    from .shim.auto_patch import (
        clear_agent_state,
        get_agent_state,
        install_agent_hooks,
    )

    async def auto_entrypoint(ctx):
        """Automatically created entrypoint that handles state."""
        # TODO: Extract context from ctx if available
        # For now, agent will auto-restore from global context set by worker

        # Create agent instance (auto-patches will restore state)
        agent = agent_class()

        # Install additional hooks (function tool wrapping)
        install_agent_hooks(agent)

        # Call agent's lifecycle methods if they exist
        if hasattr(agent, 'on_enter'):
            await agent.on_enter()

        # Agent runs here - user's logic executes
        # State is automatically captured as agent runs

        # Cleanup
        if hasattr(agent, 'on_exit'):
            await agent.on_exit()

        # Get captured state
        state = get_agent_state(agent)

        # Clean up
        clear_agent_state(agent)

        # TODO: Return state to gateway through ctx
        logger.debug(f"Captured state: {list(state.keys())}")

    # Run worker with auto entrypoint
    await run_worker(config, auto_entrypoint)


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
    "--agent-class",
    default=None,
    help="Specific Agent class name (if multiple in file)",
)
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Log level",
)
def run(agent_file: str, gateway_url: str, api_key: str, agent_class: str | None, log_level: str):
    """
    Run an agent worker with ZERO code changes.

    AGENT_FILE is the path to your Python file containing a livekit.agents.Agent subclass.
    
    Your agent code remains UNCHANGED - just write normal livekit-agents code:
    
    \b
    # your_agent.py
    from livekit.agents import Agent
    
    class MyAgent(Agent):
        def __init__(self):
            super().__init__(instructions="You are helpful")
        
        @llm.function_tool()
        async def my_tool(self):
            return "result"
    
    Then run: livetxt run your_agent.py

    Example:
        livetxt run agent.py --gateway-url https://gateway.example.com --api-key sk_xxx
    """
    # Set log level
    logging.getLogger().setLevel(getattr(logging, log_level))

    click.echo("🚀 LiveTxt - Zero-Code-Change Agent Runner")
    click.echo(f"📦 Loading agent from {agent_file}")

    # STEP 1: Apply automatic patches BEFORE loading user code
    click.echo("🔧 Installing automatic state capture...")
    from .shim.auto_patch import patch_livekit_auto
    patch_livekit_auto()

    # STEP 2: Auto-discover and load agent class
    try:
        from .loader import load_agent_from_file
        agent_cls = load_agent_from_file(agent_file, agent_class)
        click.echo(f"✅ Found agent: {agent_cls.__name__}")
    except Exception as e:
        click.echo(f"❌ Error loading agent: {e}", err=True)
        sys.exit(1)

    # STEP 3: Create config
    config = LiveTxtConfig(gateway_url=gateway_url, api_key=api_key)
    click.echo(f"🌐 Connecting to {gateway_url}")
    click.echo("📱 State capture enabled automatically")

    # STEP 4: Run worker with auto-patched agent
    try:
        # Pass agent class instead of entrypoint
        asyncio.run(run_worker_with_agent_class(config, agent_cls))
    except KeyboardInterrupt:
        click.echo("\n👋 Shutting down")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command()
def version():
    """Show version information."""
    from . import __version__

    click.echo(f"LiveTxt version {__version__}")


@cli.command()
@click.argument("agent_file", type=click.Path(exists=True))
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8080, type=int, help="Port to bind to")
@click.option("--agent-class", default=None, help="Specific Agent class name")
@click.option(
    "--log-level",
    default="info",
    type=click.Choice(["debug", "info", "warning", "error"]),
    help="Log level",
)
def serve(agent_file: str, host: str, port: int, agent_class: str | None, log_level: str):
    """Start the worker HTTP server with the given agent."""
    import uvicorn

    from .http_server import create_app

    # Create app and pre-load agent via startup request after server starts
    app = create_app()

    click.echo(f"🚀 Starting LiveTxt Worker on {host}:{port}")
    click.echo(f"📦 Agent file: {agent_file}")

    # We cannot call /load_agent before server starts, so rely on gateway to call it,
    # or document a curl call; for local testing we log instructions.
    click.echo("ℹ️  After server starts, load the agent with:")
    click.echo(
        f"   curl -X POST 'http://{host}:{port}/load_agent?agent_file={agent_file}&agent_class={agent_class or ''}'"
    )

    uvicorn.run(app, host=host, port=port, log_level=log_level)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()

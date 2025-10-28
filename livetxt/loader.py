from __future__ import annotations

"""
Automatic agent discovery and loading.

This module loads user's agent files and automatically finds Agent classes
without requiring any specific exports or naming conventions.
"""

import importlib.util
import inspect
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def load_module_from_file(file_path: str | Path) -> Any:
    """
    Dynamically load a Python module from a file path.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        The loaded module
        
    Raises:
        ImportError: If the file cannot be loaded
    """
    file_path = Path(file_path).resolve()

    if not file_path.exists():
        raise FileNotFoundError(f"Agent file not found: {file_path}")

    if not file_path.suffix == '.py':
        raise ValueError(f"File must be a Python file (.py): {file_path}")

    # Generate module name from file
    module_name = file_path.stem

    # Load the module
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {file_path}")

    module = importlib.util.module_from_spec(spec)

    # Add parent directory to sys.path so relative imports work
    parent_dir = str(file_path.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    # Execute the module
    spec.loader.exec_module(module)

    logger.info(f"✅ Loaded module: {module_name} from {file_path}")
    return module


def find_agent_classes(module: Any) -> list[type]:
    """
    Find all Agent subclasses in a module.
    
    Args:
        module: The module to search
        
    Returns:
        List of Agent classes found
    """
    try:
        from livekit.agents import Agent
    except ImportError:
        logger.error("livekit-agents not installed")
        return []

    agent_classes = []

    for name, obj in inspect.getmembers(module):
        # Skip private members
        if name.startswith('_'):
            continue

        # Check if it's a class
        if not inspect.isclass(obj):
            continue

        # Check if it's an Agent subclass (but not Agent itself)
        if issubclass(obj, Agent) and obj is not Agent:
            agent_classes.append(obj)
            logger.info(f"Found agent class: {obj.__name__}")

    return agent_classes


def load_agent_from_file(file_path: str | Path, agent_class_name: str | None = None) -> type:
    """
    Load an Agent class from a file.
    
    Args:
        file_path: Path to the Python file containing the agent
        agent_class_name: Optional specific class name to load.
                         If None, will auto-discover and use the first Agent found.
        
    Returns:
        The Agent class
        
    Raises:
        ValueError: If no Agent class is found or if specified class is not found
    """
    # Load the module
    module = load_module_from_file(file_path)

    # Find agent classes
    agent_classes = find_agent_classes(module)

    if not agent_classes:
        raise ValueError(
            f"No Agent classes found in {file_path}. "
            "Make sure your file contains a class that inherits from livekit.agents.Agent"
        )

    # If specific class name provided, find it
    if agent_class_name:
        for cls in agent_classes:
            if cls.__name__ == agent_class_name:
                logger.info(f"✅ Selected agent class: {cls.__name__}")
                return cls

        # Not found
        available = ", ".join(cls.__name__ for cls in agent_classes)
        raise ValueError(
            f"Agent class '{agent_class_name}' not found in {file_path}. "
            f"Available classes: {available}"
        )

    # Auto-select
    if len(agent_classes) == 1:
        agent_class = agent_classes[0]
        logger.info(f"✅ Auto-selected agent class: {agent_class.__name__}")
        return agent_class
    else:
        # Multiple agents found
        class_names = ", ".join(cls.__name__ for cls in agent_classes)
        logger.warning(
            f"Multiple agent classes found: {class_names}. "
            f"Using first one: {agent_classes[0].__name__}. "
            "Specify --agent-class to choose a different one."
        )
        return agent_classes[0]


def create_agent_instance(agent_class: type, **kwargs: Any) -> Any:
    """
    Create an instance of an agent class.
    
    Args:
        agent_class: The Agent class to instantiate
        **kwargs: Additional arguments to pass to the constructor
        
    Returns:
        The agent instance
    """
    try:
        agent = agent_class(**kwargs)
        logger.info(f"✅ Created agent instance: {agent_class.__name__}")
        return agent
    except Exception as e:
        logger.error(f"Failed to create agent instance: {e}", exc_info=True)
        raise


def load_and_create_agent(
    file_path: str | Path,
    agent_class_name: str | None = None,
    **kwargs: Any
) -> Any:
    """
    Convenience function to load and instantiate an agent in one step.
    
    Args:
        file_path: Path to the Python file containing the agent
        agent_class_name: Optional specific class name to load
        **kwargs: Additional arguments to pass to the agent constructor
        
    Returns:
        The agent instance
    """
    agent_class = load_agent_from_file(file_path, agent_class_name)
    return create_agent_instance(agent_class, **kwargs)

"""
Pytest configuration for LiveTxt tests.

This sets up the test environment for both sync and async tests.
"""

import logging
import warnings
import sys

import pytest
import anyio


@pytest.fixture
def anyio_backend():
    """Use asyncio as the backend for anyio tests."""
    return "asyncio"


def pytest_configure(config):
    """Register custom markers and configure logging."""
    config.addinivalue_line(
        "markers", "anyio: mark test as an anyio test (async)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    
    # Configure logging to reduce noise
    # Completely silence the livekit loggers that generate TTS errors
    logging.getLogger("livekit").setLevel(logging.CRITICAL)  # More aggressive
    logging.getLogger("livekit.agents.utils.log").setLevel(logging.CRITICAL)
    logging.getLogger("livekit.agents.voice.generation").setLevel(logging.CRITICAL)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Suppress warnings about TTS errors (expected in text-only mode)
    warnings.filterwarnings("ignore", message=".*tts_node called but no TTS node is available.*")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        # Add anyio marker to async tests
        if "anyio" in item.keywords or hasattr(item, 'callspec') and 'anyio_backend' in item.callspec.params:
            item.add_marker(pytest.mark.anyio)

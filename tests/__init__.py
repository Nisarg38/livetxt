"""
LiveTxt Test Suite

Comprehensive tests for LiveTxt - validating that LiveKit agents
work in text-only, stateless mode with ZERO code changes.

Test Organization:
- fixtures/ - Reusable test agents
- helpers/ - Test utilities and mock objects
- test_*.py - Individual test modules

Quick Start:
    pytest tests/ -v                    # Run all tests
    pytest tests/test_weather_agent.py  # Run specific test file

See tests/README.md for detailed documentation.
"""

__all__ = ["fixtures", "helpers"]

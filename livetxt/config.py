"""Configuration for LiveTxt runtime."""

import os

from pydantic import BaseModel


class LiveTxtConfig(BaseModel):
    """Configuration for LiveTxt runtime."""

    gateway_url: str
    api_key: str
    reconnect_attempts: int = 5
    reconnect_delay: float = 2.0
    heartbeat_interval: float = 30.0

    @classmethod
    def from_env(cls) -> "LiveTxtConfig":
        """Load configuration from environment variables."""
        gateway_url = os.getenv("LIVETXT_GATEWAY_URL")
        api_key = os.getenv("LIVETXT_API_KEY")

        if not gateway_url:
            raise ValueError("LIVETXT_GATEWAY_URL environment variable not set")
        if not api_key:
            raise ValueError("LIVETXT_API_KEY environment variable not set")

        return cls(gateway_url=gateway_url, api_key=api_key)

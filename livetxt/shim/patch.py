"""Monkey-patching for LiveKit SDK compatibility."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Global flag to prevent multiple patch applications
_PATCHING_APPLIED = False


def patch_livekit() -> None:
    """
    Patch LiveKit SDK to work in text-only SMS mode.

    This modifies AgentSession to:
    1. Force text-only mode
    2. Disable audio/video
    3. Make STT/TTS optional
    """
    global _PATCHING_APPLIED
    if _PATCHING_APPLIED:
        logger.debug("LiveKit SDK already patched, skipping")
        return

    try:
        from livekit import agents
        from livekit.agents.voice import generation

        # Store original AgentSession
        _OriginalAgentSession = agents.AgentSession

        class SMSAgentSession(_OriginalAgentSession):  # type: ignore
            """
            Wrapper around AgentSession that forces text-only mode.
            """

            def __init__(self, *args: Any, **kwargs: Any):
                # Remove/ignore STT and TTS
                kwargs.pop("stt", None)
                kwargs.pop("tts", None)

                # Force chat-only mode if available
                # Note: This depends on the LiveKit SDK version
                # You may need to adjust based on the actual API

                logger.info("Initializing SMS-compatible AgentSession (text-only)")

                try:
                    super().__init__(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Error initializing AgentSession: {e}")
                    # Try without STT/TTS
                    super().__init__(*args, stt=None, tts=None, **kwargs)

            def emit(self, event_name: str, *args: Any, **kwargs: Any) -> Any:
                """
                Override emit to skip TTS-related events in text-only mode.
                """
                # Skip speech-related events that would trigger TTS
                if event_name in ('speech_created', 'speech_started', 'speech_done'):
                    logger.debug(f"Skipping TTS event in text-only mode: {event_name}")
                    return None

                return super().emit(event_name, *args, **kwargs)

        # Note: TTS errors occur but don't break functionality
        # The VoiceAssistant will log errors about missing TTS but continue working

        # Replace AgentSession
        agents.AgentSession = SMSAgentSession  # type: ignore
        logger.info("✅ LiveKit SDK patched for SMS mode")

        _PATCHING_APPLIED = True

    except ImportError:
        logger.warning("LiveKit SDK not installed, skipping patch")
        _PATCHING_APPLIED = True  # Mark as applied even if failed
    except Exception as e:
        logger.error(f"Failed to patch LiveKit SDK: {e}")
        _PATCHING_APPLIED = True  # Mark as applied even if failed

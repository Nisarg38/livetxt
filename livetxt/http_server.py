"""
FastAPI HTTP server for livetxt worker (Phase 1 HTTP integration).
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .loader import load_agent_from_file
from .shim.auto_patch import (
    get_agent_state,
    install_agent_hooks,
    patch_livekit_auto,
    set_execution_context,
)

logger = logging.getLogger(__name__)


class AgentStateModel(BaseModel):
    chat_context: dict[str, Any] | None = None
    function_calls: list[dict[str, Any]] = []
    user_state: str = "listening"
    agent_state: str = "idle"


class SimpleExecuteRequest(BaseModel):
    request_id: str
    session_id: str
    user_id: str
    message: str
    agent_state: AgentStateModel | None = None


class ExecuteResponseMetadata(BaseModel):
    processing_time_ms: float


class SimpleExecuteResponse(BaseModel):
    request_id: str
    status: str
    response: str | None = None
    updated_state: AgentStateModel | None = None
    error: str | None = None
    metadata: ExecuteResponseMetadata | None = None


class LoadAgentRequest(BaseModel):
    agent_file: str = Field(description="Path to agent Python file")
    agent_class: str | None = Field(default=None, description="Optional agent class name")


def create_app() -> FastAPI:
    app = FastAPI(title="LiveTxt Worker", version="0.0.1")

    # Globals
    state: dict[str, Any] = {"agent_class": None, "agent_file": None}

    @app.on_event("startup")
    async def on_startup() -> None:
        patch_livekit_auto()
        logger.info("✅ LiveKit auto-patching applied")

    @app.post("/load_agent")
    async def load_agent(agent_file: str, agent_class: str | None = None) -> dict[str, Any]:
        try:
            agent_cls = load_agent_from_file(agent_file, agent_class)
            state["agent_class"] = agent_cls
            state["agent_file"] = agent_file
            logger.info(f"✅ Loaded agent: {agent_cls.__name__} from {agent_file}")
            return {"status": "loaded", "agent_class": agent_cls.__name__}
        except Exception as e:
            logger.error(f"Failed to load agent: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/execute", response_model=SimpleExecuteResponse)
    async def execute(req: SimpleExecuteRequest) -> SimpleExecuteResponse:
        start = time.time()

        if state["agent_class"] is None:
            return SimpleExecuteResponse(
                request_id=req.request_id, status="error", error="Agent not loaded"
            )

        try:
            # Provide previous state to auto-patch layer
            prev_state = req.agent_state.model_dump() if req.agent_state else None
            set_execution_context({"previous_state": prev_state, "user_id": req.user_id})

            # Create agent instance and install hooks
            agent_cls = state["agent_class"]
            agent = agent_cls()
            install_agent_hooks(agent)
        except Exception as e:
            logger.error(f"Error creating agent: {e}", exc_info=True)
            return SimpleExecuteResponse(
                request_id=req.request_id,
                status="error",
                error=f"Agent creation failed: {str(e)}"
            )

        # Minimal processing: inject user message and a simple echo response
        try:
            from livekit.agents import llm

            if hasattr(agent, "chat_ctx") and agent.chat_ctx is not None:
                # Add user message
                agent.chat_ctx.add_message(
                    llm.ChatMessage(role="user", content=[{"type": "text", "text": req.message}])
                )

                # Create a simple echo response (placeholder for real LLM processing)
                reply_text = f"You said: {req.message}"
                agent.chat_ctx.add_message(
                    llm.ChatMessage(
                        role="assistant", content=[{"type": "text", "text": reply_text}]
                    )
                )

                # Let auto-capture run when chat_ctx accessed
                _ = agent.chat_ctx
                response_text = reply_text
            else:
                response_text = f"You said: {req.message}"
        except Exception as e:
            logger.warning(f"ChatContext manipulation failed: {e}")
            response_text = f"You said: {req.message}"

        # Collect state
        captured = get_agent_state(agent)
        updated_state = AgentStateModel(**captured)

        return SimpleExecuteResponse(
            request_id=req.request_id,
            status="success",
            response=response_text,
            updated_state=updated_state,
            metadata=ExecuteResponseMetadata(processing_time_ms=(time.time() - start) * 1000),
        )

    return app

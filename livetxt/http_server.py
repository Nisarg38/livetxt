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


def create_app(agent_file: str | None = None, agent_class: str | None = None) -> FastAPI:
    app = FastAPI(title="LiveTxt Worker", version="0.0.1")

    # Globals
    state: dict[str, Any] = {"agent_class": None, "agent_file": None}

    @app.on_event("startup")
    async def on_startup() -> None:
        patch_livekit_auto()
        logger.info("✅ LiveKit auto-patching applied")

        # Auto-load agent if provided
        if agent_file:
            try:
                agent_cls = load_agent_from_file(agent_file, agent_class)
                state["agent_class"] = agent_cls
                state["agent_file"] = agent_file
                logger.info(f"✅ Auto-loaded agent: {agent_cls.__name__} from {agent_file}")
            except Exception as e:
                logger.error(f"❌ Failed to auto-load agent: {e}")
                raise

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
            raise HTTPException(status_code=400, detail=str(e)) from e

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

        # Process message through agent's LLM
        try:

            if not hasattr(agent, "chat_ctx") or agent.chat_ctx is None:
                logger.error("Agent does not have chat_ctx initialized")
                return SimpleExecuteResponse(
                    request_id=req.request_id,
                    status="error",
                    error="Agent chat_ctx not initialized"
                )

            # Copy chat context (it's read-only), add user message, then update agent
            chat_ctx = agent.chat_ctx.copy()
            chat_ctx.add_message(role="user", content=req.message)
            await agent.update_chat_ctx(chat_ctx)
            logger.debug(f"Added user message: {req.message[:50]}...")

            # Run LLM to get response
            if not hasattr(agent, "llm") or agent.llm is None:
                # Fallback if no LLM configured
                reply_text = f"Echo: {req.message}"
                logger.warning("No LLM configured, using echo response")
            else:
                # Run LLM chat completion
                try:
                    # Call LLM with chat context
                    response_stream = agent.llm.chat(chat_ctx=agent.chat_ctx)

                    # Collect response using to_str_iterable() for simple text
                    reply_text = ""
                    async for text_chunk in response_stream.to_str_iterable():
                        reply_text += text_chunk

                    logger.info(f"LLM response: {reply_text[:100]}...")

                except Exception as llm_error:
                    logger.error(f"LLM execution failed: {llm_error}", exc_info=True)
                    return SimpleExecuteResponse(
                        request_id=req.request_id,
                        status="error",
                        error=f"LLM execution failed: {str(llm_error)}"
                    )

            # Add assistant response to context using copy() and update_chat_ctx()
            if reply_text:
                chat_ctx = agent.chat_ctx.copy()
                chat_ctx.add_message(role="assistant", content=reply_text)
                await agent.update_chat_ctx(chat_ctx)

            # Trigger auto-capture by accessing chat_ctx
            _ = agent.chat_ctx
            response_text = reply_text

        except Exception as e:
            logger.error(f"Message processing failed: {e}", exc_info=True)
            return SimpleExecuteResponse(
                request_id=req.request_id,
                status="error",
                error=f"Message processing failed: {str(e)}"
            )

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

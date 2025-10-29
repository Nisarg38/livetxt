"""
LiveKit Customer Support Agent Example - Works with LiveTxt!

This demonstrates:
- Multi-turn conversations with memory
- Complex business logic
- Context-aware responses

🎯 ZERO CODE CHANGES from original LiveKit agent!
"""

import logging
from typing import Optional

from dotenv import load_dotenv

from livekit.agents import Agent, AgentSession, JobContext, RunContext, WorkerOptions, cli
from livekit.agents.llm import function_tool
from livekit.plugins import openai

# livetxt imports
from livetxt import cli as livetxt_cli

logger = logging.getLogger("customer-support-agent")
logger.setLevel(logging.INFO)

load_dotenv()


class CustomerSupportAgent(Agent):
    """A customer support agent for a fictional e-commerce store."""
    
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a helpful customer support representative for TechStore. "
                "You can help with order status, returns, and general questions. "
                "Be professional, empathetic, and solution-oriented. "
                "Always confirm the user's information before taking actions."
            ),
            llm=openai.LLM(model="gpt-4.1-mini"),
        )
        self.customer_email: Optional[str] = None
        self.order_number: Optional[str] = None
    
    @function_tool
    async def check_order_status(self, order_number: str, email: str) -> dict:
        """
        Check the status of a customer's order.
        
        Args:
            order_number: The order number (e.g., "ORD-12345")
            email: Customer's email address for verification
        """
        logger.info(f"Checking order {order_number} for {email}")
        
        # Mock order data
        order_data = {
            "order_number": order_number,
            "status": "Shipped",
            "tracking_number": "1Z999AA10123456784",
            "estimated_delivery": "Tomorrow, 3-5 PM",
            "items": ["Laptop", "Wireless Mouse"],
            "total": "$1,249.99"
        }
        
        self.customer_email = email
        self.order_number = order_number
        
        return order_data
    
    @function_tool
    async def initiate_return(self, order_number: str, reason: str) -> str:
        """
        Start the return process for an order.
        
        Args:
            order_number: The order number to return
            reason: Reason for the return
        """
        logger.info(f"Initiating return for {order_number}: {reason}")
        
        return (
            f"I've started a return for order {order_number}. "
            f"You'll receive a return label at your email within 24 hours. "
            f"The refund will be processed once we receive the item."
        )
    
    @function_tool
    async def update_shipping_address(self, order_number: str, new_address: str) -> str:
        """
        Update the shipping address for an order (if not yet shipped).
        
        Args:
            order_number: The order number
            new_address: The new shipping address
        """
        logger.info(f"Updating address for {order_number} to {new_address}")
        
        return (
            f"I've updated the shipping address for order {order_number} to: {new_address}. "
            f"Your order will be delivered to the new address."
        )


async def entrypoint(ctx: JobContext):
    """
    Standard LiveKit agent entrypoint.
    
    ✅ Works with both LiveKit (voice) and LiveTxt (text) unchanged!
    """
    session = AgentSession()
    
    await session.start(
        agent=CustomerSupportAgent(),
        room=ctx.room,
    )


if __name__ == "__main__":
    ## Run with LiveKit CLI (Voice Mode) ##
    # cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

    ### Run with LiveTxt CLI (SMS Mode) ###
    ## Set these environment variables: ##
    ## export LIVETXT_GATEWAY_URL=http://localhost:8000 ##
    ## export LIVETXT_API_KEY=sk_live_1234567890 ##
    livetxt_cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        ws_url="http://localhost:8000",
        api_key="test_key_123"
    ))


"""Order operations functions for calculating totals and creating orders."""

from loguru import logger
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams

from functions.base import AgentFunction
from models.session_state import SessionState
from services.burger_api import BurgerAPIClient


class CalculateOrderTotalFunction(AgentFunction):
    """Function to calculate the total price of the current order."""

    def __init__(self, session_state: SessionState):
        """Initialize the calculate total function.

        Args:
            session_state: The session state containing order_items
        """
        self.session_state = session_state

    def get_schema(self) -> FunctionSchema:
        """Create the function schema for calculating order total."""
        return FunctionSchema(
            name="calculate_order_total",
            description="Calculate the total price of the current order. Use this when the customer asks about the price or total.",
            properties={},
            required=[],
        )

    def get_handler(self):
        """Get the handler function for calculating order total."""
        return self._handle_calculate_total

    async def _handle_calculate_total(self, params: FunctionCallParams) -> str:
        """Calculate the total price of the current order."""
        if not self.session_state.order_items:
            return "Your order is empty. Please add some items first."

        # Format breakdown
        lines = ["Here's the breakdown of your order:"]
        for item in self.session_state.order_items:
            item_total = item.price * item.quantity
            lines.append(
                f"  {item.quantity}x {item.name} @ ${item.price:.2f} each = ${item_total:.2f}"
            )

        total = self.session_state.calculate_total()
        lines.append(f"\nTotal: ${total:.2f}")

        logger.info(f"Calculated order total: ${total:.2f}")
        response = "\n".join(lines)
        await params.result_callback(response)
        return response


class CreateOrderFunction(AgentFunction):
    """Function to finalize and submit the order."""

    def __init__(self, session_state: SessionState, api_client: BurgerAPIClient):
        """Initialize the create order function.

        Args:
            session_state: The session state containing order_items
            api_client: The burger API client for submitting orders
        """
        self.session_state = session_state
        self.api_client = api_client

    def get_schema(self) -> FunctionSchema:
        """Create the function schema for creating an order."""
        return FunctionSchema(
            name="create_order",
            description="Finalize and submit the order to the burger joint. Use this when the customer confirms they are ready to place their order.",
            properties={},
            required=[],
        )

    def get_handler(self):
        """Get the handler function for creating an order."""
        return self._handle_create_order

    async def _handle_create_order(self, params: FunctionCallParams) -> str:
        """Create and submit the order."""
        if not self.session_state.order_items:
            return "Error: Your order is empty. Please add some items before placing your order."

        try:
            # Prepare items for API
            api_items = [
                {"item_id": item.item_id, "quantity": item.quantity} for item in self.session_state.order_items
            ]

            # Submit order to API
            order_response = await self.api_client.create_order(api_items)

            # Clear the order from session state
            self.session_state.clear_order()

            logger.info(f"Order created successfully: {order_response.order_id}")
            response = (
                f"Order confirmed! Your order ID is {order_response.order_id}. "
                f"Total: ${order_response.total:.2f}. "
                f"Thank you for your order!"
            )
            await params.result_callback(response)
            return response
        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            # Don't clear the order if it failed - customer can try again
            response = (
                f"Sorry, there was an error processing your order. "
                f"Your items are still in your cart. Please try again in a moment."
            )
            await params.result_callback(response)
            return response

"""Reusable state management functions for order operations."""

from typing import List

from loguru import logger
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams

from functions.base import AgentFunction
from models.session_state import OrderItem, SessionState
from services.models import MenuItem


class AddItemToOrderFunction(AgentFunction):
    """Function to add items to the customer's order."""

    def __init__(self, session_state: SessionState, catalog: List[MenuItem]):
        """Initialize the add item function.

        Args:
            session_state: The session state containing order_items
            catalog: List of menu items from the catalog
        """
        self.session_state = session_state
        self.catalog = catalog

    def get_schema(self) -> FunctionSchema:
        """Create the function schema for adding items to order."""
        return FunctionSchema(
            name="add_item_to_order",
            description="Add menu items to the customer's order. Use this when the customer wants to order something.",
            properties={
                "item_id": {
                    "type": "string",
                    "description": "The ID of the menu item to add (e.g., 'burger-001', 'side-001', 'drink-001')",
                },
                "quantity": {
                    "type": "integer",
                    "description": "The number of items to add (default: 1)",
                    "default": 1,
                },
            },
            required=["item_id"],
        )

    def get_handler(self):
        """Get the handler function for adding items to order."""
        return self._handle_add_item

    async def _handle_add_item(self, params: FunctionCallParams) -> str:
        """Add an item to the order."""
        item_id = params.arguments.get("item_id")
        quantity = params.arguments.get("quantity", 1)

        if not item_id:
            return "Error: item_id is required"

        if quantity < 1:
            return "Error: quantity must be at least 1"

        # Find the item in catalog
        menu_item = next((item for item in self.catalog if item.id == item_id), None)
        if not menu_item:
            available_ids = ", ".join([item.id for item in self.catalog[:5]])
            return f"Error: Item '{item_id}' not found in menu. Available items include: {available_ids}"

        # Create order item
        order_item = OrderItem(
            item_id=item_id,
            quantity=quantity,
            name=menu_item.name,
            price=menu_item.price,
        )

        # Add to order (will update quantity if item already exists)
        self.session_state.add_item(order_item)

        # Calculate total
        total = self.session_state.calculate_total()

        logger.info(f"Added {quantity}x {menu_item.name} to order")
        response = (
            f"Added {quantity} {menu_item.name}(s) to your order. Current order total: ${total:.2f}"
        )
        await params.result_callback(response)
        return response


class RemoveItemFromOrderFunction(AgentFunction):
    """Function to remove items from the customer's order."""

    def __init__(self, session_state: SessionState):
        """Initialize the remove item function.

        Args:
            session_state: The session state containing order_items
        """
        self.session_state = session_state

    def get_schema(self) -> FunctionSchema:
        """Create the function schema for removing items from order."""
        return FunctionSchema(
            name="remove_item_from_order",
            description="Remove items from the customer's order. Use this when the customer wants to remove or change items.",
            properties={
                "item_id": {
                    "type": "string",
                    "description": "The ID of the menu item to remove",
                },
                "quantity": {
                    "type": "integer",
                    "description": "The number of items to remove. If not specified, removes all of that item.",
                },
            },
            required=["item_id"],
        )

    def get_handler(self):
        """Get the handler function for removing items from order."""
        return self._handle_remove_item

    async def _handle_remove_item(self, params: FunctionCallParams) -> str:
        """Remove an item from the order."""
        item_id = params.arguments.get("item_id")
        quantity = params.arguments.get("quantity")

        if not item_id:
            return "Error: item_id is required"

        # Find the item to get its name
        item_to_remove = next((item for item in self.session_state.order_items if item.item_id == item_id), None)

        if not item_to_remove:
            return f"Error: Item '{item_id}' not found in your order"

        item_name = item_to_remove.name
        current_quantity = item_to_remove.quantity

        if quantity is not None and quantity < 1:
            return "Error: quantity to remove must be at least 1"

        # Remove the item (or reduce quantity)
        removed = self.session_state.remove_item(item_id, quantity)

        if not removed:
            return f"Error: Item '{item_id}' not found in your order"

        logger.info(f"Removed {quantity if quantity and quantity < current_quantity else 'all'} {item_name} from order")

        if not self.session_state.order_items:
            return f"Removed all {item_name} from your order. Your order is now empty."

        total = self.session_state.calculate_total()
        if quantity is None or quantity >= current_quantity:
            response = f"Removed all {item_name} from your order. Current order total: ${total:.2f}"
        else:
            response = f"Removed {quantity} {item_name}(s) from your order. Current order total: ${total:.2f}"

        await params.result_callback(response)
        return response


class ReadCurrentOrderFunction(AgentFunction):
    """Function to read back the current order."""

    def __init__(self, session_state: SessionState):
        """Initialize the read order function.

        Args:
            session_state: The session state containing order_items
        """
        self.session_state = session_state

    def get_schema(self) -> FunctionSchema:
        """Create the function schema for reading the current order."""
        return FunctionSchema(
            name="read_current_order",
            description="Read back the current order to confirm what the customer has ordered. Use this when the customer asks to review their order or when you need to confirm items.",
            properties={},
            required=[],
        )

    def get_handler(self):
        """Get the handler function for reading the current order."""
        return self._handle_read_order

    async def _handle_read_order(self, params: FunctionCallParams) -> str:
        """Read back the current order."""
        if not self.session_state.order_items:
            return "Your order is currently empty."

        # Format order summary
        lines = ["Here's your current order:"]

        for item in self.session_state.order_items:
            item_total = item.price * item.quantity
            lines.append(f"  {item.quantity}x {item.name} - ${item_total:.2f}")

        total = self.session_state.calculate_total()
        lines.append(f"\nTotal: ${total:.2f}")

        logger.info(f"Read current order: {len(self.session_state.order_items)} items, total ${total:.2f}")
        response = "\n".join(lines)
        await params.result_callback(response)
        return response

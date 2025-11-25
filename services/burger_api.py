"""Mock burger joint API client."""

import uuid
from typing import List

from loguru import logger

from services.mock_data import MENU_ITEMS
from services.models import (
    CreateOrderResponse,
    MenuItem,
)


class BurgerAPIClient:
    """Mock client for burger joint operations."""

    def __init__(self):
        """Initialize the mock API client."""
        pass

    async def get_catalog(self) -> List[MenuItem]:
        """Get the menu catalog from mock data.

        Returns:
            List of menu items
        """
        items = [MenuItem(**item) for item in MENU_ITEMS]
        logger.info(f"Loaded {len(items)} items from mock catalog")
        return items

    async def create_order(self, items: List[dict]) -> CreateOrderResponse:
        """Create a new order using mock data.

        Args:
            items: List of order items with 'item_id' and 'quantity' keys

        Returns:
            Order response with order_id, total, and status
        """
        # Calculate total from mock menu data
        total = 0.0
        menu_dict = {item["id"]: item for item in MENU_ITEMS}

        for order_item in items:
            if order_item["item_id"] in menu_dict:
                item_price = menu_dict[order_item["item_id"]]["price"]
                total += item_price * order_item["quantity"]

        # Generate mock order response
        order_id = str(uuid.uuid4())
        order_response = CreateOrderResponse(
            order_id=order_id,
            total=round(total, 2),
            status="confirmed",
        )

        logger.info(f"Created mock order {order_response.order_id} with total ${order_response.total}")
        return order_response

    async def close(self):
        """Close the client (no-op for mock client)."""
        pass


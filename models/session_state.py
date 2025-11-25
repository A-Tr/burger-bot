"""Session state models for the burger joint agent."""

from typing import List

from pydantic import BaseModel, Field


class OrderItem(BaseModel):
    """Represents an item in the customer's order."""

    item_id: str = Field(..., description="The ID of the menu item")
    quantity: int = Field(..., ge=1, description="The quantity of this item")
    name: str = Field(..., description="The name of the menu item")
    price: float = Field(..., ge=0, description="The price per unit of the item")


class SessionState(BaseModel):
    """Session state for tracking the customer's order."""

    order_items: List[OrderItem] = Field(default_factory=list, description="List of items in the current order")

    def clear_order(self) -> None:
        """Clear all items from the order."""
        self.order_items = []

    def add_item(self, item: OrderItem) -> None:
        """Add an item to the order, or update quantity if item already exists."""
        existing_item = next((i for i in self.order_items if i.item_id == item.item_id), None)
        if existing_item:
            existing_item.quantity += item.quantity
        else:
            self.order_items.append(item)

    def remove_item(self, item_id: str, quantity: int | None = None) -> bool:
        """Remove an item from the order.
        
        Args:
            item_id: The ID of the item to remove
            quantity: The quantity to remove. If None, removes all of that item.
            
        Returns:
            True if item was found and removed, False otherwise
        """
        item_to_remove = next((item for item in self.order_items if item.item_id == item_id), None)
        if not item_to_remove:
            return False

        if quantity is None or quantity >= item_to_remove.quantity:
            # Remove all of this item
            self.order_items.remove(item_to_remove)
        else:
            # Remove specified quantity
            item_to_remove.quantity -= quantity

        return True

    def calculate_total(self) -> float:
        """Calculate the total price of all items in the order."""
        return sum(item.price * item.quantity for item in self.order_items)


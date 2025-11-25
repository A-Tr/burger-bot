"""API models for the burger joint service."""

from typing import List

from pydantic import BaseModel


class MenuItem(BaseModel):
    """Menu item model."""

    id: str
    name: str
    description: str
    price: float
    category: str


class CatalogResponse(BaseModel):
    """Response model for catalog endpoint."""

    items: List[MenuItem]


class OrderItem(BaseModel):
    """Order item model."""

    item_id: str
    quantity: int


class CreateOrderRequest(BaseModel):
    """Request model for creating an order."""

    items: List[OrderItem]


class CreateOrderResponse(BaseModel):
    """Response model for order creation."""

    order_id: str
    total: float
    status: str

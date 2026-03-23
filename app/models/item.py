from typing import Optional

from pydantic import BaseModel


class Item(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    price: float


class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float

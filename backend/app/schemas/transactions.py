from datetime import datetime
from typing import Any

from pydantic import BaseModel


class TransactionItem(BaseModel):
    description: str
    amount: float


class CreateTransactionRequest(BaseModel):
    transaction_id: str
    transaction_code: int
    date: str
    merchant: str
    amount: float
    currency: str = "CAD"
    employee: str = ""
    transaction_category: int = 1
    description: str = ""
    merchant_category_code: int | None = None
    merchant_city: str = ""
    merchant_state: str = ""
    merchant_country: str = ""
    conversion_rate: float = 1.0
    items: list[TransactionItem] = []

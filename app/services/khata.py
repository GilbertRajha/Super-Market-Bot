from __future__ import annotations

from typing import Any

from ..database.repositories.customers import CustomerRepository


class KhataService:
    def __init__(self) -> None:
        self._customers = CustomerRepository()

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        return self._customers.search(query, limit=limit)

    def get(self, customer_id: int) -> dict[str, Any] | None:
        return self._customers.get(customer_id)

    def create(self, name: str, phone: str | None = None) -> dict[str, Any]:
        return self._customers.create(name, phone)

    def record_payment(self, customer_id: int, amount: float, method: str = "cash") -> dict[str, Any]:
        return self._customers.record_payment(customer_id, amount, method)

    def balance(self, customer_id: int) -> float:
        return float(self._customers.get_balance(customer_id).get("balance", 0))

    def history(self, customer_id: int, limit: int = 20) -> list[dict[str, Any]]:
        return self._customers.history(customer_id, limit=limit)
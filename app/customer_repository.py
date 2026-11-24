"""Read-only access to the static customer fixture database."""

import json
from pathlib import Path
from typing import Any


class CustomerRepository:
    def __init__(self, database_path: Path | None = None) -> None:
        self.database_path = database_path or Path(__file__).resolve().parent.parent / "data" / "customers.json"

    def get_customer(self, client_id: int) -> dict[str, Any] | None:
        """Return a new customer dictionary, or None when it does not exist.

        The file is opened read-only for each lookup. Returning a fresh decoded
        object prevents request processing from mutating the static fixture.
        """
        with self.database_path.open("r", encoding="utf-8") as database:
            customers = json.load(database)

        for customer in customers["customers"]:
            if customer["clientId"] == client_id:
                return customer
        return None

    def get_customer_by_email(self, email: str) -> dict[str, Any] | None:
        """Return a customer dictionary matching email (case-insensitive), or None."""
        with self.database_path.open("r", encoding="utf-8") as database:
            customers = json.load(database)

        target = email.strip().lower()
        for customer in customers["customers"]:
            if customer.get("email", "").strip().lower() == target:
                return customer
        return None


repository = CustomerRepository()

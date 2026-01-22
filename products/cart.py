from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterable, List, Tuple

from django.db.models import Min

from .models import Product


SESSION_KEY = "cart"


@dataclass(frozen=True)
class CartLine:
    product: Product
    quantity: int
    unit_price: Decimal

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity


class Cart:
    def __init__(self, request):
        self._session = request.session
        self._data: Dict[str, int] = self._session.get(SESSION_KEY, {})

    def __contains__(self, product_id: object) -> bool:
        try:
            return str(int(product_id)) in self._data
        except (TypeError, ValueError):
            return False

    def save(self) -> None:
        self._session[SESSION_KEY] = self._data
        self._session.modified = True

    def clear(self) -> None:
        self._data = {}
        self.save()

    def has(self, product_id: int) -> bool:
        return str(product_id) in self._data

    def quantity_for(self, product_id: int) -> int:
        return int(self._data.get(str(product_id), 0))

    def add(self, product_id: int, quantity: int = 1) -> None:
        key = str(product_id)
        self._data[key] = int(self._data.get(key, 0)) + int(quantity)
        if self._data[key] <= 0:
            self._data.pop(key, None)
        self.save()

    def remove(self, product_id: int) -> None:
        self._data.pop(str(product_id), None)
        self.save()

    def toggle(self, product_id: int) -> bool:
        """Returns True if item is now in cart, False otherwise."""
        if self.has(product_id):
            self.remove(product_id)
            return False
        self.add(product_id, 1)
        return True

    @property
    def count(self) -> int:
        return sum(int(qty) for qty in self._data.values())

    @property
    def product_ids(self) -> List[int]:
        return [int(pid) for pid in self._data.keys()]

    def lines(self) -> List[CartLine]:
        ids = self.product_ids
        if not ids:
            return []

        products = list(Product.objects.filter(id__in=ids).prefetch_related("variants"))
        products_by_id = {p.id: p for p in products}

        # Preserve insertion order of the session dict.
        ordered: List[Tuple[int, int]] = [(int(pid), int(qty)) for pid, qty in self._data.items()]

        lines: List[CartLine] = []
        for product_id, quantity in ordered:
            product = products_by_id.get(product_id)
            if not product:
                continue

            min_price = product.variants.aggregate(min_price=Min("price")).get("min_price")
            unit_price = Decimal(str(min_price)) if min_price is not None else Decimal("0")

            lines.append(CartLine(product=product, quantity=quantity, unit_price=unit_price))

        return lines

    def subtotal(self) -> Decimal:
        return sum((line.line_total for line in self.lines()), Decimal("0"))

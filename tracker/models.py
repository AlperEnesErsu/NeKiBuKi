from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class Product:
    product_id: str
    name: str
    url: str
    target_price: float
    check_interval_hours: float = 2.0
    notify_desktop: bool = True
    notify_email: bool = False
    email_to: str = ""
    last_price: Optional[float] = None
    last_stock_in: Optional[bool] = None
    last_checked_at: str = ""
    last_status_message: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Product":
        return cls(
            product_id=str(data.get("product_id", "")),
            name=str(data.get("name", "")),
            url=str(data.get("url", "")),
            target_price=float(data.get("target_price", 0.0)),
            check_interval_hours=float(data.get("check_interval_hours", 2.0)),
            notify_desktop=bool(data.get("notify_desktop", True)),
            notify_email=bool(data.get("notify_email", False)),
            email_to=str(data.get("email_to", "")),
            last_price=data.get("last_price"),
            last_stock_in=data.get("last_stock_in"),
            last_checked_at=str(data.get("last_checked_at", "")),
            last_status_message=str(data.get("last_status_message", "")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HistoryPoint:
    product_id: str
    checked_at: str
    price: Optional[float]
    stock_in: Optional[bool]

    @classmethod
    def now(cls, product_id: str, price: Optional[float], stock_in: Optional[bool]) -> "HistoryPoint":
        return cls(
            product_id=product_id,
            checked_at=datetime.now().isoformat(timespec="seconds"),
            price=price,
            stock_in=stock_in,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HistoryPoint":
        return cls(
            product_id=str(data.get("product_id", "")),
            checked_at=str(data.get("checked_at", "")),
            price=data.get("price"),
            stock_in=data.get("stock_in"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScrapeResult:
    price: Optional[float]
    stock_in: Optional[bool]
    status_message: str

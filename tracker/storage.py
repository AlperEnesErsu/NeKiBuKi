from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, List

from .models import HistoryPoint, Product


class JsonStorage:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self._lock = threading.Lock()
        self._ensure_file()

    def _ensure_file(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.file_path.write_text(
                json.dumps({"products": [], "history": []}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    def _load_raw(self) -> Dict:
        try:
            return json.loads(self.file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"products": [], "history": []}

    def _save_raw(self, data: Dict) -> None:
        self.file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def list_products(self) -> List[Product]:
        with self._lock:
            data = self._load_raw()
            return [Product.from_dict(item) for item in data.get("products", [])]

    def get_product(self, product_id: str) -> Product | None:
        products = self.list_products()
        for product in products:
            if product.product_id == product_id:
                return product
        return None

    def upsert_product(self, product: Product) -> None:
        with self._lock:
            data = self._load_raw()
            items = data.get("products", [])
            replaced = False
            for index, item in enumerate(items):
                if item.get("product_id") == product.product_id:
                    items[index] = product.to_dict()
                    replaced = True
                    break
            if not replaced:
                items.append(product.to_dict())
            data["products"] = items
            self._save_raw(data)

    def delete_product(self, product_id: str) -> None:
        with self._lock:
            data = self._load_raw()
            data["products"] = [p for p in data.get("products", []) if p.get("product_id") != product_id]
            data["history"] = [h for h in data.get("history", []) if h.get("product_id") != product_id]
            self._save_raw(data)

    def append_history(self, point: HistoryPoint) -> None:
        with self._lock:
            data = self._load_raw()
            history = data.get("history", [])
            history.append(point.to_dict())
            data["history"] = history[-1000:]
            self._save_raw(data)

    def get_history(self, product_id: str) -> List[HistoryPoint]:
        with self._lock:
            data = self._load_raw()
            values = [h for h in data.get("history", []) if h.get("product_id") == product_id]
            return [HistoryPoint.from_dict(h) for h in values]

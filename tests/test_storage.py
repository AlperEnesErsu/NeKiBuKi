from pathlib import Path
from tracker.storage import JsonStorage
from tracker.models import Product, HistoryPoint

def test_json_storage_operations(tmp_path):
    file_path = tmp_path / "products.json"
    storage = JsonStorage(file_path)

    # Verify initial files are created
    assert file_path.exists()
    assert storage.list_products() == []

    # Create test product
    product = Product(
        product_id="test-uuid",
        name="Sek Quark",
        url="https://www.carrefoursa.com/sek-quark-sade-140-g-p-30162892",
        target_price=50.0
    )

    # Save product
    storage.upsert_product(product)
    
    # Retrieve product
    products = storage.list_products()
    assert len(products) == 1
    assert products[0].product_id == "test-uuid"
    assert products[0].name == "Sek Quark"

    # Get product by ID
    retrieved = storage.get_product("test-uuid")
    assert retrieved is not None
    assert retrieved.name == "Sek Quark"

    # Append history
    point1 = HistoryPoint("test-uuid", "2026-07-01T10:00:00", 45.0, True)
    point2 = HistoryPoint("test-uuid", "2026-07-01T11:00:00", 44.0, True)
    storage.append_history(point1)
    storage.append_history(point2)

    history = storage.get_history("test-uuid")
    assert len(history) == 2
    assert history[0].price == 45.0
    assert history[1].price == 44.0

    # Delete product
    storage.delete_product("test-uuid")
    assert storage.list_products() == []
    assert storage.get_history("test-uuid") == []

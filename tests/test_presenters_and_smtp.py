from tracker.models import Product
from tracker.presenters import parse_product_form, product_row
from tracker.smtp_config import (
    current_smtp_values,
    export_smtp_env,
    has_required_fields,
    load_smtp_config,
    save_smtp_config,
)


def test_product_row_formats_each_cell():
    p = Product(product_id="1", name="Quark", url="u", target_price=50,
                last_price=42.5, last_stock_in=False, last_checked_at="2026-10-15T12:34:56")
    assert product_row(p) == ("Quark", "50.00", "42.50", "Yok", "2026-10-15 12:34")
    fresh = Product(product_id="2", name="New", url="u", target_price=10)
    assert product_row(fresh) == ("New", "10.00", "-", "?", "-")


def test_parse_product_form_trims_and_validates():
    form = parse_product_form("  Quark ", " https://example.test ", " 49.9 ", "3")
    assert (form.name, form.url, form.target_price, form.check_interval_hours) == (
        "Quark", "https://example.test", 49.9, 3.0)
    assert parse_product_form("", "u", "1", "1") == "Urun adi ve URL zorunludur."
    assert parse_product_form("a", "u", "x", "1") == "Hedef fiyat ve aralik sayi olmali."
    assert parse_product_form("a", "u", "1", "-1") == "Kontrol araligi sifirdan buyuk olmali."


def test_smtp_config_round_trip_and_missing_or_broken_file(tmp_path):
    path = tmp_path / "config.json"
    assert load_smtp_config(path) == {}
    path.write_text("{not json", encoding="utf-8")
    assert load_smtp_config(path) == {}
    save_smtp_config(path, {"smtp_host": "h", "smtp_user": "ü@example.test"})
    assert load_smtp_config(path) == {"smtp_host": "h", "smtp_user": "ü@example.test"}


def test_export_skips_empty_values_and_can_clear_the_sender():
    env = {"NEKIBUKI_SMTP_FROM": "old@example.test"}
    export_smtp_env({"smtp_host": "h", "smtp_port": 25, "smtp_user": "u", "smtp_pass": "p", "smtp_from": ""}, env)
    assert env == {"NEKIBUKI_SMTP_HOST": "h", "NEKIBUKI_SMTP_PORT": "25", "NEKIBUKI_SMTP_USER": "u",
                   "NEKIBUKI_SMTP_PASS": "p", "NEKIBUKI_SMTP_FROM": "old@example.test"}
    export_smtp_env({"smtp_from": ""}, env, clear_missing_from=True)
    assert "NEKIBUKI_SMTP_FROM" not in env


def test_required_fields_and_dialog_defaults():
    assert has_required_fields({"smtp_host": "h", "smtp_user": "u", "smtp_pass": "p"})
    assert not has_required_fields({"smtp_host": "h", "smtp_user": " ", "smtp_pass": "p"})
    values = current_smtp_values({"smtp_host": "from-file"}, {"NEKIBUKI_SMTP_USER": "from-env"})
    assert values["smtp_host"] == "from-file"
    assert values["smtp_user"] == "from-env"
    assert values["smtp_port"] == "587"

"""GUI smoke tests: build the real Tk window (hidden) and drive the form.

Skipped automatically where no display / Tk is available.
"""

import json
import os
import tkinter as tk

import pytest

from tracker.models import ScrapeResult


@pytest.fixture
def app(tmp_path, monkeypatch):
    try:
        probe = tk.Tk()
        probe.destroy()
    except tk.TclError:
        pytest.skip("Tk/display not available")

    from tracker import gui

    shown = []
    for name in ("showerror", "showinfo", "showwarning"):
        monkeypatch.setattr(gui.messagebox, name, lambda *a, _n=name, **k: shown.append((_n, a)))
    window = gui.App(data_file=tmp_path / "products.json")
    window.withdraw()
    window.shown = shown
    yield window
    window._on_close()


def _fill(app, name="Sek Quark", url="https://example.test/p-1", target="50", interval="2"):
    app.name_var.set(name)
    app.url_var.set(url)
    app.target_var.set(target)
    app.interval_var.set(interval)


def test_save_adds_a_row_and_persists(app):
    _fill(app)
    app._save_product()

    rows = app.tree.get_children()
    assert len(rows) == 1
    assert app.tree.item(rows[0], "values")[:2] == ("Sek Quark", "50.00")
    assert [p.name for p in app.storage.list_products()] == ["Sek Quark"]
    # Form is cleared and the compare box gets the product name
    assert app.name_var.get() == ""
    assert app.compare_query_var.get() == "Sek Quark"


@pytest.mark.parametrize(
    ("fields", "expected_error"),
    [
        ({"name": ""}, "Urun adi ve URL zorunludur."),
        ({"target": "abc"}, "Hedef fiyat ve aralik sayi olmali."),
        ({"interval": "0"}, "Kontrol araligi sifirdan buyuk olmali."),
    ],
)
def test_invalid_form_shows_an_error_and_saves_nothing(app, fields, expected_error):
    _fill(app, **fields)
    app._save_product()
    assert app.tree.get_children() == ()
    assert ("showerror", ("Hata", expected_error)) in app.shown


def test_selecting_fills_the_form_and_delete_removes_the_row(app):
    _fill(app)
    app._save_product()
    (row,) = app.tree.get_children()

    app.tree.selection_set(row)
    app._on_select_product(None)
    assert app.name_var.get() == "Sek Quark"
    assert app.target_var.get() == "50.0"

    app._delete_selected()
    assert app.tree.get_children() == ()
    assert app.storage.list_products() == []


@pytest.mark.parametrize(
    ("price", "stock", "target", "text", "color"),
    [
        (40.0, True, 50.0, "Stok: Var | Fiyat: 40.00 TL | Hedef alti: Evet (Hedef 50.00 TL)", "#34d399"),
        (60.0, True, 50.0, "Stok: Var | Fiyat: 60.00 TL | Hedef alti: Hayir (Hedef 50.00 TL)", "#fbbf24"),
        (None, False, 50.0, "Stok: Yok | Fiyat bulunamadi | Hedef durumu: Belirsiz", "#f87171"),
        (40.0, None, None, "Stok: Belirsiz | Fiyat: 40.00 TL | Hedef durumu: Hedef fiyat girilmedi", "#f87171"),
    ],
)
def test_check_alert_text_and_colour(app, price, stock, target, text, color):
    result = ScrapeResult(price=price, stock_in=stock, status_message="ok")
    app._set_check_alert(result, target)
    assert app.check_alert_var.get() == text
    assert str(app.check_alert_label.cget("fg")) == color


def test_smtp_settings_in_config_json_are_exported_to_the_environment(tmp_path, monkeypatch):
    try:
        probe = tk.Tk()
        probe.destroy()
    except tk.TclError:
        pytest.skip("Tk/display not available")
    from tracker import gui

    for key in ("HOST", "PORT", "USER", "PASS", "FROM"):
        monkeypatch.delenv(f"NEKIBUKI_SMTP_{key}", raising=False)
    (tmp_path / "config.json").write_text(
        json.dumps({"smtp_host": "smtp.example.test", "smtp_port": 2525, "smtp_user": "u@example.test",
                    "smtp_pass": "secret", "smtp_from": ""}),
        encoding="utf-8",
    )
    window = gui.App(data_file=tmp_path / "products.json")
    window.withdraw()
    try:
        assert os.environ["NEKIBUKI_SMTP_HOST"] == "smtp.example.test"
        assert os.environ["NEKIBUKI_SMTP_PORT"] == "2525"
        assert os.environ["NEKIBUKI_SMTP_USER"] == "u@example.test"
        assert os.environ["NEKIBUKI_SMTP_PASS"] == "secret"
        assert "NEKIBUKI_SMTP_FROM" not in os.environ  # empty value is not exported
    finally:
        window._on_close()

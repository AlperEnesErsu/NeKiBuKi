"""SMTP ayarları: config.json okuma/yazma ve ortam değişkenlerine aktarma (Tk yok).

`Notifier` ayarları ortam değişkenlerinden okur; arayüz ise kullanıcının girdiği
değerleri `data/config.json` dosyasında saklar. Bu modül ikisi arasındaki tek köprü.
"""

from __future__ import annotations

import json
import os
from collections.abc import MutableMapping
from pathlib import Path

# config.json anahtarı -> Notifier'ın okuduğu ortam değişkeni
SMTP_ENV = {
    "smtp_host": "NEKIBUKI_SMTP_HOST",
    "smtp_port": "NEKIBUKI_SMTP_PORT",
    "smtp_user": "NEKIBUKI_SMTP_USER",
    "smtp_pass": "NEKIBUKI_SMTP_PASS",
    "smtp_from": "NEKIBUKI_SMTP_FROM",
}
DEFAULT_PORT = "587"


def config_path_for(data_file: Path) -> Path:
    """SMTP ayarlarının saklandığı dosya (ürün verisiyle aynı klasörde)."""
    return data_file.parent / "config.json"


def load_smtp_config(path: Path) -> dict:
    """Dosya yoksa ya da bozuksa boş sözlük."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_smtp_config(path: Path, config: dict) -> None:
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def export_smtp_env(
    config: dict, environ: MutableMapping[str, str] | None = None, *, clear_missing_from: bool = False
) -> None:
    """Dolu ayarları ortam değişkenlerine yazar; boş değerler atlanır.

    `clear_missing_from`: gönderen adresi boşsa eski değeri de sil (kaydetme akışı).
    """
    env = os.environ if environ is None else environ
    for key, var in SMTP_ENV.items():
        value = config.get(key)
        if value:
            env[var] = str(value)
        elif key == "smtp_from" and clear_missing_from:
            env.pop(var, None)


def has_required_fields(config: dict) -> bool:
    """Sunucu, kullanıcı ve şifre olmadan e-posta gönderilemez."""
    return all(str(config.get(k, "")).strip() for k in ("smtp_host", "smtp_user", "smtp_pass"))


def current_smtp_values(config: dict, environ: MutableMapping[str, str] | None = None) -> dict:
    """Diyalog açılırken gösterilecek değerler: önce config.json, yoksa ortam."""
    env = os.environ if environ is None else environ
    values = {key: str(config.get(key, env.get(var, ""))) for key, var in SMTP_ENV.items()}
    if not values["smtp_port"]:
        values["smtp_port"] = DEFAULT_PORT
    return values

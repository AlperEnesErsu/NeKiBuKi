"""SMTP (e-posta) ayarları penceresi."""

from __future__ import annotations

from pathlib import Path
from tkinter import BOTH, LEFT, RIGHT, W, messagebox, ttk
import tkinter as tk

from .notifier import Notifier
from .smtp_config import (
    current_smtp_values,
    export_smtp_env,
    has_required_fields,
    load_smtp_config,
    save_smtp_config,
)


def open_smtp_settings(parent: tk.Misc, config_path: Path, notifier: Notifier) -> tk.Toplevel:
    dialog = tk.Toplevel(parent)
    dialog.title("SMTP (E-posta) Ayarlari")
    dialog.geometry("450x330")
    dialog.configure(bg="#0f172a")
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(False, False)

    initial = current_smtp_values(load_smtp_config(config_path))
    fields = {key: tk.StringVar(value=value) for key, value in initial.items()}

    frame = ttk.Frame(dialog, padding=15, style="App.TFrame")
    frame.pack(fill=BOTH, expand=True)

    rows = [
        ("SMTP Sunucu (Host):", "smtp_host", 25, None),
        ("SMTP Port:", "smtp_port", 10, None),
        ("SMTP Kullanici (E-posta):", "smtp_user", 25, None),
        ("SMTP Sifre / Uygulama Sifresi:", "smtp_pass", 25, "*"),
        ("Gonderen E-posta (Opsiyonel):", "smtp_from", 25, None),
    ]
    for row, (label, key, width, show) in enumerate(rows):
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky=W, padx=5, pady=5)
        entry = ttk.Entry(frame, textvariable=fields[key], width=width)
        if show:
            entry.configure(show=show)
        entry.grid(row=row, column=1, sticky=W, padx=5, pady=5)

    btn_frame = ttk.Frame(frame, style="App.TFrame")
    btn_frame.grid(row=len(rows), column=0, columnspan=2, pady=15, sticky="ew")

    def values() -> dict:
        return {key: var.get().strip() for key, var in fields.items()}

    def save_smtp() -> None:
        config = values()
        if not has_required_fields(config):
            messagebox.showerror("Hata", "Sunucu, kullanici ve sifre alanlari zorunludur.")
            return
        try:
            save_smtp_config(config_path, config)
        except OSError as e:
            messagebox.showerror("Hata", f"Ayarlar kaydedilemedi: {e}")
            return
        export_smtp_env(config, clear_missing_from=True)
        messagebox.showinfo("Basarili", "SMTP ayarları kaydedildi.")
        dialog.destroy()

    def test_smtp() -> None:
        config = values()
        if not has_required_fields(config):
            messagebox.showerror("Hata", "Test icin sunucu, kullanici ve sifre gereklidir.")
            return
        export_smtp_env(config)

        user = config["smtp_user"]
        if messagebox.askquestion("SMTP Test", f"Test e-postasi {user} adresine gonderilsin mi?") != "yes":
            return
        dialog.title("SMTP (E-posta) Ayarlari - Test ediliyor...")
        success = notifier.send_email(
            to_email=user,
            subject="NeKiBuKi SMTP Test",
            message="NeKiBuKi uygulaması SMTP ayarları basariyla test edildi!",
        )
        dialog.title("SMTP (E-posta) Ayarlari")
        if success:
            messagebox.showinfo("Basarili", f"Test e-postasi {user} adresine basariyla gonderildi.")
        else:
            messagebox.showerror("Hata", "E-posta gonderimi basarisiz. Lutfen ayarlari kontrol edin.")

    ttk.Button(btn_frame, text="Kaydet", command=save_smtp, style="Primary.TButton").pack(side=LEFT, padx=5)
    ttk.Button(btn_frame, text="Test Et", command=test_smtp).pack(side=LEFT, padx=5)
    ttk.Button(btn_frame, text="Iptal", command=dialog.destroy).pack(side=RIGHT, padx=5)
    return dialog

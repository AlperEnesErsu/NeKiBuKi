from __future__ import annotations

import queue
import threading
import time
import uuid
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, TOP, VERTICAL, W, X, Y, ttk
import tkinter as tk
from tkinter import messagebox
from urllib.parse import unquote, urlparse
import webbrowser

import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import schedule

from .models import Product
from .notifier import Notifier
from .scraper import ProductScraper
from .service import TrackerService
from .storage import JsonStorage


class App(tk.Tk):
    def __init__(self, data_file: Path) -> None:
        super().__init__()
        self.title("NeKiBuKi - Fiyat Takibi")
        self.geometry("1400x750")
        self.configure(bg="#f5f7fa")

        self.storage = JsonStorage(data_file)
        self.service = TrackerService(self.storage, ProductScraper(), Notifier())

        self.scheduler = schedule.Scheduler()
        self.scheduler_stop = threading.Event()
        self.event_queue: queue.Queue[tuple[str, object]] = queue.Queue()

        self.selected_product_id: str | None = None
        self.show_chart = False

        self._configure_style()
        self._build_ui()
        self._load_products()
        self._rebuild_schedule_jobs()
        self._start_scheduler_thread()
        self.after(400, self._poll_events)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("App.TFrame", background="#f2f5f9")
        style.configure("Card.TLabelframe", background="#ffffff", borderwidth=1)
        style.configure("Card.TLabelframe.Label", background="#ffffff", foreground="#16324f", font=("Segoe UI Semibold", 10))
        style.configure("Title.TLabel", background="#f2f5f9", foreground="#0f2740", font=("Segoe UI Semibold", 17))
        style.configure("Hint.TLabel", background="#f2f5f9", foreground="#4c6176", font=("Segoe UI", 10))
        style.configure("Primary.TButton", font=("Segoe UI Semibold", 10), padding=(12, 7))
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 10))

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12, style="App.TFrame")
        root.pack(fill=BOTH, expand=True)

        header = ttk.Frame(root, style="App.TFrame")
        header.pack(fill=X, pady=(0, 12))
        ttk.Label(header, text="NeKiBuKi - Fiyat Takip ve Karsilastirma", style="Title.TLabel").pack(anchor=W)

        body = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        body.pack(fill=BOTH, expand=True)

        left_col = ttk.Frame(body, style="App.TFrame")
        right_col = ttk.Frame(body, style="App.TFrame")
        body.add(left_col, weight=4)
        body.add(right_col, weight=5)

        self._build_form(left_col)
        self._build_table(left_col)
        self._build_log_and_chart(left_col)
        self._build_compare(right_col)

    def _build_form(self, parent: ttk.Frame) -> None:
        form = ttk.LabelFrame(parent, text="Urun Ekle / Guncelle", padding=10, style="Card.TLabelframe")
        form.pack(fill=X, pady=(0, 8))

        self.name_var = tk.StringVar()
        self.url_var = tk.StringVar()
        self.target_var = tk.StringVar(value="100")
        self.interval_var = tk.StringVar(value="2")
        self.desktop_var = tk.BooleanVar(value=True)

        ttk.Label(form, text="Urun Adi").grid(row=0, column=0, sticky=W, padx=5, pady=5)
        ttk.Entry(form, textvariable=self.name_var, width=25).grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        ttk.Label(form, text="URL").grid(row=1, column=0, sticky=W, padx=5, pady=5)
        entry_url = ttk.Entry(form, textvariable=self.url_var)
        entry_url.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Hedef Fiyat").grid(row=2, column=0, sticky=W, padx=5, pady=5)
        ttk.Entry(form, textvariable=self.target_var, width=12).grid(row=2, column=1, sticky=W, padx=5, pady=5)

        ttk.Label(form, text="Kontrol (saat)").grid(row=2, column=2, sticky=W, padx=5, pady=5)
        ttk.Entry(form, textvariable=self.interval_var, width=8).grid(row=2, column=3, sticky=W, padx=5, pady=5)

        ttk.Checkbutton(form, text="Masaustu Uyarisi", variable=self.desktop_var).grid(
            row=3, column=0, columnspan=2, sticky=W, padx=5, pady=5
        )

        button_row = ttk.Frame(form)
        button_row.grid(row=4, column=0, columnspan=4, sticky="ew", padx=5, pady=(8, 4))
        button_row.columnconfigure(3, weight=1)

        ttk.Button(button_row, text="Kaydet", command=self._save_product, style="Primary.TButton").pack(side=LEFT, padx=2)
        ttk.Button(button_row, text="Sil", command=self._delete_selected).pack(side=LEFT, padx=2)
        ttk.Button(button_row, text="Kontrol Et", command=self._check_selected).pack(side=LEFT, padx=2)
        ttk.Button(button_row, text="Hepsini Kontrol Et", command=self._check_all).pack(side=LEFT, padx=2)

        self.check_alert_var = tk.StringVar(value="Kontrol sonucu burada gorunur.")
        self.check_alert_label = tk.Label(
            form,
            textvariable=self.check_alert_var,
            anchor="w",
            justify="left",
            fg="#1f3349",
            bg="#ffffff",
            font=("Segoe UI", 9, "bold"),
        )
        self.check_alert_label.grid(row=5, column=0, columnspan=4, sticky="ew", padx=5, pady=(6, 2))

    def _build_table(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Takip Listesi", padding=8, style="Card.TLabelframe")
        frame.pack(fill=BOTH, expand=True, pady=(0, 8))

        columns = ("name", "target", "price", "stock", "checked")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=20)

        self.tree.heading("name", text="Urun")
        self.tree.heading("target", text="Hedef")
        self.tree.heading("price", text="Fiyat")
        self.tree.heading("stock", text="Stok")
        self.tree.heading("checked", text="Son Kontrol")

        self.tree.column("name", width=200, anchor=W)
        self.tree.column("target", width=70, anchor=W)
        self.tree.column("price", width=70, anchor=W)
        self.tree.column("stock", width=60, anchor=W)
        self.tree.column("checked", width=120, anchor=W)

        scrollbar = ttk.Scrollbar(frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.tree.bind("<<TreeviewSelect>>", self._on_select_product)

    def _build_log_and_chart(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Aktivite Logu", padding=8, style="Card.TLabelframe")
        frame.pack(fill=X, pady=(0, 0))

        self.log = tk.Text(frame, height=4, wrap="word", bd=0, padx=6, pady=6, bg="#f8fafc", fg="#1f3349")
        self.log.pack(fill=X)

        chart_frame = ttk.LabelFrame(parent, text="Fiyat Grafigi", padding=8, style="Card.TLabelframe")
        chart_frame.pack(fill=BOTH, expand=False, pady=(8, 0))

        self.figure = Figure(figsize=(4, 2.5), dpi=80)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Trend", fontsize=9)
        self.ax.set_xlabel("Tarih", fontsize=8)
        self.ax.set_ylabel("Fiyat (TL)", fontsize=8)

        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill=BOTH, expand=True)

    def _build_compare(self, parent: ttk.Frame) -> None:
        wrapper = ttk.LabelFrame(parent, text="Benzer Urunleri Tara", padding=10, style="Card.TLabelframe")
        wrapper.pack(fill=BOTH, expand=True)

        top = ttk.Frame(wrapper)
        top.pack(fill=X, pady=(0, 10))

        self.compare_query_var = tk.StringVar()
        self.compare_general_var = tk.BooleanVar(value=True)
        ttk.Label(top, text="Ara:").pack(side=LEFT, padx=5)
        ttk.Entry(top, textvariable=self.compare_query_var, width=50).pack(side=LEFT, padx=5, fill=X, expand=True)
        ttk.Checkbutton(top, text="Genel Arama", variable=self.compare_general_var).pack(side=LEFT, padx=5)
        ttk.Button(top, text="Ara", command=self._start_market_search, style="Primary.TButton").pack(side=LEFT, padx=5)

        self.compare_best_var = tk.StringVar(value="Henuz sonuc yok")
        best_label = ttk.Label(wrapper, textvariable=self.compare_best_var, foreground="#0b5d3f", font=("Segoe UI", 9, "bold"))
        best_label.pack(anchor=W, pady=(0, 8))

        columns = ("site", "price", "title")
        self.compare_tree = ttk.Treeview(wrapper, columns=columns, show="headings", height=24)
        self.compare_tree.heading("site", text="Site")
        self.compare_tree.heading("price", text="Fiyat")
        self.compare_tree.heading("title", text="Urun")

        self.compare_tree.column("site", width=80, anchor=W)
        self.compare_tree.column("price", width=90, anchor=W)
        self.compare_tree.column("title", width=350, anchor=W)

        compare_scroll = ttk.Scrollbar(wrapper, orient=VERTICAL, command=self.compare_tree.yview)
        self.compare_tree.configure(yscrollcommand=compare_scroll.set)
        self.compare_tree.pack(side=LEFT, fill=BOTH, expand=True)
        compare_scroll.pack(side=RIGHT, fill=Y)

        self.compare_tree.bind("<Double-1>", self._open_selected_offer)

    def _load_products(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        for product in self.service.list_products():
            self._insert_or_update_tree(product)

    def _insert_or_update_tree(self, product: Product) -> None:
        stock_label = "?" if product.last_stock_in is None else ("Var" if product.last_stock_in else "Yok")
        price_label = "-" if product.last_price is None else f"{product.last_price:.2f}"
        checked_label = product.last_checked_at.replace("T", " ")[:16] if product.last_checked_at else "-"

        values = (
            product.name,
            f"{product.target_price:.2f}",
            price_label,
            stock_label,
            checked_label,
        )

        if self.tree.exists(product.product_id):
            self.tree.item(product.product_id, values=values)
        else:
            self.tree.insert("", END, iid=product.product_id, values=values)

    def _save_product(self) -> None:
        name = self.name_var.get().strip()
        url = self.url_var.get().strip()

        if not name or not url:
            messagebox.showerror("Hata", "Urun adi ve URL zorunludur.")
            return

        try:
            target_price = float(self.target_var.get().strip())
            check_interval = float(self.interval_var.get().strip())
        except ValueError:
            messagebox.showerror("Hata", "Hedef fiyat ve aralik sayi olmali.")
            return

        if check_interval <= 0:
            messagebox.showerror("Hata", "Kontrol araligi sifirdan buyuk olmali.")
            return

        product_id = self.selected_product_id or str(uuid.uuid4())
        existing = self.storage.get_product(product_id)

        product = Product(
            product_id=product_id,
            name=name,
            url=url,
            target_price=target_price,
            check_interval_hours=check_interval,
            notify_desktop=self.desktop_var.get(),
            notify_email=False,
            email_to="",
            last_price=existing.last_price if existing else None,
            last_stock_in=existing.last_stock_in if existing else None,
            last_checked_at=existing.last_checked_at if existing else "",
            last_status_message=existing.last_status_message if existing else "",
        )

        self.service.save_product(product)
        self._insert_or_update_tree(product)
        self._rebuild_schedule_jobs()
        self._clear_form()
        self.compare_query_var.set(product.name)
        self._log(f"Kaydedildi: {product.name}")

    def _delete_selected(self) -> None:
        product_id = self._selected_tree_id()
        if not product_id:
            messagebox.showinfo("Bilgi", "Silmek icin bir urun sec.")
            return

        product = self.storage.get_product(product_id)
        self.service.delete_product(product_id)
        self.tree.delete(product_id)
        self._rebuild_schedule_jobs()
        self._clear_form()
        self._log(f"Silindi: {product.name if product else product_id}")

    def _check_selected(self) -> None:
        product_id = self._selected_tree_id()
        url_in_form = self.url_var.get().strip()

        selected_product = self.storage.get_product(product_id) if product_id else None

        # Form URL varsa, secim olmasa bile direkt kontrol et.
        if url_in_form:
            if selected_product and selected_product.url.strip() == url_in_form:
                result = self.service.check_product_by_id(product_id)
                updated = self.storage.get_product(product_id)
                if result and updated:
                    self._insert_or_update_tree(updated)
                    self.compare_query_var.set(updated.name)
                    self._set_check_alert(result, updated.target_price)
                    self._log(f"Manuel kontrol: {updated.name} -> {result.status_message}")
                return

            result = self.service.scraper.scrape(url_in_form)
            name = self.name_var.get().strip() or "Form URL"
            target_price = self._parse_target_price()
            self._set_check_alert(result, target_price)
            self.compare_query_var.set(self.name_var.get().strip() or self._guess_query_from_form())
            self._log(f"URL kontrol: {name} -> {result.status_message}")
            messagebox.showinfo("Kontrol Sonucu", result.status_message)
            return

        if not product_id:
            messagebox.showinfo("Bilgi", "Kontrol icin bir urun sec veya URL gir.")
            return

        result = self.service.check_product_by_id(product_id)
        updated = self.storage.get_product(product_id)
        if result and updated:
            self._insert_or_update_tree(updated)
            self.compare_query_var.set(updated.name)
            self._set_check_alert(result, updated.target_price)
            self._log(f"Manuel kontrol: {updated.name} -> {result.status_message}")

    def _parse_target_price(self) -> float | None:
        try:
            return float(self.target_var.get().strip())
        except (ValueError, TypeError):
            return None

    def _set_check_alert(self, result, target_price: float | None) -> None:
        stock_text = "Belirsiz"
        if result.stock_in is True:
            stock_text = "Var"
        elif result.stock_in is False:
            stock_text = "Yok"

        if result.price is None:
            price_text = "Fiyat bulunamadi"
            target_text = "Hedef durumu: Belirsiz"
            below_target = False
        else:
            price_text = f"Fiyat: {result.price:.2f} TL"
            if target_price is None or target_price <= 0:
                target_text = "Hedef durumu: Hedef fiyat girilmedi"
                below_target = False
            else:
                below_target = result.price <= target_price
                target_text = (
                    f"Hedef alti: {'Evet' if below_target else 'Hayir'} "
                    f"(Hedef {target_price:.2f} TL)"
                )

        message = f"Stok: {stock_text} | {price_text} | {target_text}"
        self.check_alert_var.set(message)

        if result.stock_in is True and below_target:
            self.check_alert_label.configure(fg="#0b5d3f")
        elif result.stock_in is True:
            self.check_alert_label.configure(fg="#7a5a00")
        else:
            self.check_alert_label.configure(fg="#8b1e2d")

    def _check_all(self) -> None:
        all_results = self.service.check_all_products()
        for product, result in all_results:
            current = self.storage.get_product(product.product_id)
            if current:
                self._insert_or_update_tree(current)
            self._log(f"Toplu kontrol: {product.name} -> {result.status_message}")

    def _on_select_product(self, _event: object) -> None:
        product_id = self._selected_tree_id()
        if not product_id:
            return

        product = self.storage.get_product(product_id)
        if not product:
            return

        self.selected_product_id = product_id
        self.name_var.set(product.name)
        self.url_var.set(product.url)
        self.target_var.set(str(product.target_price))
        self.interval_var.set(str(product.check_interval_hours))
        self.desktop_var.set(product.notify_desktop)
        self.compare_query_var.set(product.name)
        self._draw_history(product_id)

    def _draw_history(self, product_id: str | None) -> None:
        self.ax.clear()
        self.ax.set_title("Fiyat Trendi", fontsize=10)
        self.ax.set_xlabel("Tarih", fontsize=9)
        self.ax.set_ylabel("Fiyat (TL)", fontsize=9)
        self.figure.tight_layout()

        if not product_id:
            self.canvas.draw_idle()
            return

        history = self.service.get_history(product_id)
        points = [p for p in history if p.price is not None]

        if not points:
            self.ax.text(0.5, 0.5, "Henuz veri yok", ha="center", va="center", transform=self.ax.transAxes, fontsize=10)
            self.canvas.draw_idle()
            return

        dates = [mdates.datestr2num(p.checked_at.replace("T", " ")) for p in points]
        prices = [p.price for p in points]

        self.ax.plot_date(dates, prices, "-", linewidth=2, markersize=4)
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m %H:%M"))
        self.ax.tick_params(axis='both', labelsize=8)
        self.figure.autofmt_xdate(rotation=30)
        self.canvas.draw_idle()

    def _rebuild_schedule_jobs(self) -> None:
        self.scheduler.clear()
        for product in self.service.list_products():
            interval = max(0.05, product.check_interval_hours)
            self.scheduler.every(interval).hours.do(self._scheduled_check, product.product_id).tag(product.product_id)

    def _scheduled_check(self, product_id: str) -> None:
        result = self.service.check_product_by_id(product_id)
        product = self.storage.get_product(product_id)
        if product and result:
            self.event_queue.put(("log", f"Oto kontrol: {product.name} -> {result.status_message}"))

    def _start_scheduler_thread(self) -> None:
        def worker() -> None:
            while not self.scheduler_stop.is_set():
                self.scheduler.run_pending()
                time.sleep(1)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _poll_events(self) -> None:
        changed = False
        while not self.event_queue.empty():
            event_type, payload = self.event_queue.get()
            if event_type == "log":
                self._log(str(payload))
                changed = True
            elif event_type == "offers":
                self._render_market_offers(payload if isinstance(payload, dict) else {"offers": []})

        if changed:
            self._load_products()
            if self.selected_product_id:
                self._draw_history(self.selected_product_id)

        self.after(500, self._poll_events)

    def _selected_tree_id(self) -> str | None:
        selected = self.tree.selection()
        return selected[0] if selected else None

    def _clear_form(self) -> None:
        self.selected_product_id = None
        self.name_var.set("")
        self.url_var.set("")
        self.target_var.set("100")
        self.interval_var.set("2")
        self.desktop_var.set(True)

    def _log(self, text: str) -> None:
        self.log.insert(END, f"{time.strftime('%H:%M:%S')} - {text}\n")
        self.log.see(END)

    def _start_market_search(self) -> None:
        query = self.compare_query_var.get().strip() or self._guess_query_from_form()
        if not query:
            messagebox.showinfo("Bilgi", "Karsilastirma icin urun adi veya URL gir.")
            return

        self.compare_query_var.set(query)
        self.compare_best_var.set("Araniyor...")
        general_mode = self.compare_general_var.get()
        mode_text = "genel" if general_mode else "marka odakli"
        self._log(f"Piyasa aramasi basladi ({mode_text}): {query}")
        thread = threading.Thread(target=self._market_search_worker, args=(query, general_mode), daemon=True)
        thread.start()

    def _market_search_worker(self, query: str, general_mode: bool) -> None:
        offers = self.service.find_market_alternatives(query, limit=15, general_mode=general_mode)
        self.event_queue.put(("offers", {"query": query, "offers": offers}))
        self.event_queue.put(("log", f"Piyasa aramasi tamamlandi: {len(offers)} sonuc"))

    def _render_market_offers(self, payload: dict) -> None:
        offers = payload.get("offers", []) if isinstance(payload, dict) else []

        for item in self.compare_tree.get_children():
            self.compare_tree.delete(item)

        if not offers:
            self.compare_best_var.set("Sonuc bulunamadi. Daha net bir urun adi deneyin.")
            return

        priced_offers = [o for o in offers if isinstance(o.get("price"), (int, float))]
        if priced_offers:
            best = min(priced_offers, key=lambda x: x.get("price", float("inf")))
            self.compare_best_var.set(f"En iyi: {best['price']:.2f} TL @ {best['site']}")
        else:
            self.compare_best_var.set("Bu agda fiyat cekilemedi, site arama linkleri gosteriliyor.")

        for idx, offer in enumerate(offers):
            price_value = offer.get("price")
            if isinstance(price_value, (int, float)):
                price_label = f"{price_value:.2f} TL"
            else:
                price_label = "Siteye git"

            site_label = str(offer.get("site", "-"))
            target_site = str(offer.get("target_site", "")).strip()
            if target_site and target_site != site_label:
                site_label = f"{site_label} -> {target_site}"

            self.compare_tree.insert(
                "",
                END,
                iid=f"offer-{idx}",
                values=(
                    site_label,
                    price_label,
                    offer.get("title", "-"),
                ),
                tags=(offer.get("url", ""),),
            )

    def _open_selected_offer(self, _event: object) -> None:
        selected = self.compare_tree.selection()
        if not selected:
            return

        item = selected[0]
        tags = self.compare_tree.item(item, "tags")
        if tags:
            url = str(tags[0])
            if url.startswith("http"):
                webbrowser.open(url)

    def _guess_query_from_form(self) -> str:
        if self.name_var.get().strip():
            return self.name_var.get().strip()

        url = self.url_var.get().strip()
        if not url:
            return ""

        path_parts = [p for p in urlparse(url).path.split("/") if p]
        if not path_parts:
            return ""

        candidate = unquote(path_parts[-1])
        candidate = candidate.replace("-", " ").replace("_", " ").strip()
        return " ".join(candidate.split())[:80]

    def _on_close(self) -> None:
        self.scheduler_stop.set()
        self.destroy()

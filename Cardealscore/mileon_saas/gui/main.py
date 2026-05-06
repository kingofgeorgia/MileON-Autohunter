import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tkinter import messagebox, ttk

import httpx

from mileon_saas.config import settings
from mileon_saas.db import init_db, close_engine
from mileon_saas.services.full_site_parser import FullSiteParser


# Загружаем локации из JSON
def load_locations():
    """Загружает локации из locations.json."""
    locations_path = Path(__file__).parent.parent.parent / "locations.json"
    if locations_path.exists():
        with locations_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return {int(k): v for k, v in data.items()}
    return {}

LOCATIONS = load_locations()


class ToolTip:
    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tip_window: tk.Toplevel | None = None
        self.widget.bind("<Enter>", self._show)
        self.widget.bind("<Leave>", self._hide)

    def _show(self, _event=None) -> None:
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.tip_window,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Arial", 9),
        )
        label.pack(ipadx=6, ipady=4)

    def _hide(self, _event=None) -> None:
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class HeaderToolTip:
    def __init__(self, tree: ttk.Treeview, column_help: dict[str, str]) -> None:
        self.tree = tree
        self.column_help = column_help
        self.tip_window: tk.Toplevel | None = None
        self.current_col: str | None = None
        self.tree.bind("<Motion>", self._on_motion)
        self.tree.bind("<Leave>", self._hide)

    def _on_motion(self, event) -> None:
        region = self.tree.identify_region(event.x, event.y)
        if region != "heading":
            self._hide()
            return

        col_id = self.tree.identify_column(event.x)
        try:
            col_index = int(col_id.replace("#", "")) - 1
        except ValueError:
            self._hide()
            return

        columns = list(self.tree["columns"])
        if col_index < 0 or col_index >= len(columns):
            self._hide()
            return

        col_name = columns[col_index]
        text = self.column_help.get(col_name)
        if not text:
            self._hide()
            return

        if self.tip_window and self.current_col == col_name:
            return

        self._show(event, text, col_name)

    def _show(self, event, text: str, col_name: str) -> None:
        self._hide()
        self.current_col = col_name
        self.tip_window = tk.Toplevel(self.tree)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
        label = tk.Label(
            self.tip_window,
            text=text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Arial", 9),
        )
        label.pack(ipadx=6, ipady=4)

    def _hide(self, _event=None) -> None:
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None
        self.current_col = None


class SaaSApp:
    def __init__(self, root: tk.Tk) -> None:
        logging.basicConfig(
            filename="app.log",
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
        )
        self.root = root
        self.root.title("Car Market Monitor - Рабочий стол")
        self.root.geometry("1200x720")
        self._center_window()

        self.ui_settings = self._load_ui_settings()
        self.currency_symbol = self.ui_settings.get("currency_symbol", "$")
        self.currency_rate = float(self.ui_settings.get("currency_rate", 1.0))
        self.default_min_roi = self.ui_settings.get("default_min_roi", "")
        self.default_min_net_profit = self.ui_settings.get("default_min_net_profit", "")
        self.source_filter = self.ui_settings.get("source_filter", "")
        self.repair_cost = float(self.ui_settings.get("repair_cost", 0.0))
        self.tax_rate = float(self.ui_settings.get("tax_rate", 0.02))
        self.monthly_capital_rate = float(self.ui_settings.get("monthly_capital_rate", 0.025))
        self.parking_daily = float(self.ui_settings.get("parking_daily", 4.0))
        self.insurance_daily = float(self.ui_settings.get("insurance_daily", 2.0))

        self.filters = {
            "brand": "",
            "min_roi": 0.0,
            "min_buy_score": 0.0,
            "min_risk": 0.0,
            "min_net_profit": 0.0,
        }
        self.rows = []
        self.status_var = tk.StringVar(value="Готово")
        self.last_error = ""
        self.api_process = None
        self.api_log_handle = None
        self.sort_column = "ROI"  # Default sort by ROI
        self.sort_reverse = True  # Descending order (highest first)
        self.full_parser_running = False
        self.full_cycle_running = False
        self.parser_start_time = 0
        self.parser_timer_id = None
        self.search_var = tk.StringVar()
        self.show_new_only_var = tk.BooleanVar(value=False)
        self.last_refresh_at: datetime | None = None
        self.prev_refresh_at: datetime | None = None
        self.reload_thread: threading.Thread | None = None
        self.reload_cancelled = False
        self.reload_lock = threading.Lock()  # Prevent concurrent reload starts
        self.api_cache_rows: list[dict] | None = None
        self.api_cache_time: float | None = None
        self.show_ingest_status = False
        self.keep_ingest_status_once = False
        self.last_full_parse_file: str | None = None

        self._build_ui()
        self._start_api_thread()
        # NOTE: Model sync disabled. Official Postman API provides same data statically.
        # self._maybe_sync_models()  # Commented: Unnecessary with official API docs
        self._toggle_reload()

    def _center_window(self) -> None:
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _format_time(self, seconds: float) -> str:
        """Format elapsed seconds as HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _load_ui_settings(self) -> dict:
        path = Path("ui_settings.json")
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_ui_settings(self) -> None:
        path = Path("ui_settings.json")
        payload = {
            "currency_symbol": self.currency_symbol,
            "currency_rate": self.currency_rate,
            "default_min_roi": self.default_min_roi,
            "default_min_net_profit": self.default_min_net_profit,
            "source_filter": self.source_filter,
            "repair_cost": self.repair_cost,
            "tax_rate": self.tax_rate,
            "monthly_capital_rate": self.monthly_capital_rate,
            "parking_daily": self.parking_daily,
            "insurance_daily": self.insurance_daily,
        }
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def open_settings(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Настройки")
        dialog.resizable(False, False)

        tk.Label(dialog, text="Валюта (символ)").grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
        currency_symbol_var = tk.StringVar(value=self.currency_symbol)
        tk.Entry(dialog, textvariable=currency_symbol_var, width=8).grid(row=0, column=1, padx=10, pady=5)

        tk.Label(dialog, text="Курс обмена").grid(row=1, column=0, padx=10, pady=5, sticky=tk.W)
        currency_rate_var = tk.StringVar(value=str(self.currency_rate))
        tk.Entry(dialog, textvariable=currency_rate_var, width=8).grid(row=1, column=1, padx=10, pady=5)

        tk.Label(dialog, text="Мин. ROI для фильтра").grid(row=2, column=0, padx=10, pady=5, sticky=tk.W)
        default_roi_var = tk.StringVar(value=str(self.default_min_roi))
        tk.Entry(dialog, textvariable=default_roi_var, width=8).grid(row=2, column=1, padx=10, pady=5)

        tk.Label(dialog, text="Мин. чистая прибыль для фильтра").grid(row=3, column=0, padx=10, pady=5, sticky=tk.W)
        default_net_profit_var = tk.StringVar(value=str(self.default_min_net_profit))
        tk.Entry(dialog, textvariable=default_net_profit_var, width=8).grid(row=3, column=1, padx=10, pady=5)

        tk.Label(dialog, text="Фильтр источника").grid(row=4, column=0, padx=10, pady=5, sticky=tk.W)
        source_filter_var = tk.StringVar(value=self.source_filter)
        tk.Entry(dialog, textvariable=source_filter_var, width=18).grid(row=4, column=1, padx=10, pady=5)

        tk.Label(dialog, text="Стоимость ремонта ($)").grid(row=5, column=0, padx=10, pady=5, sticky=tk.W)
        repair_cost_var = tk.StringVar(value=str(self.repair_cost))
        tk.Entry(dialog, textvariable=repair_cost_var, width=8).grid(row=5, column=1, padx=10, pady=5)

        tk.Label(dialog, text="Налоговая ставка (0-1)").grid(row=6, column=0, padx=10, pady=5, sticky=tk.W)
        tax_rate_var = tk.StringVar(value=str(self.tax_rate))
        tk.Entry(dialog, textvariable=tax_rate_var, width=8).grid(row=6, column=1, padx=10, pady=5)

        tk.Label(dialog, text="Ставка капитала / месяц").grid(row=7, column=0, padx=10, pady=5, sticky=tk.W)
        capital_rate_var = tk.StringVar(value=str(self.monthly_capital_rate))
        tk.Entry(dialog, textvariable=capital_rate_var, width=8).grid(row=7, column=1, padx=10, pady=5)

        tk.Label(dialog, text="Парковка в день").grid(row=8, column=0, padx=10, pady=5, sticky=tk.W)
        parking_daily_var = tk.StringVar(value=str(self.parking_daily))
        tk.Entry(dialog, textvariable=parking_daily_var, width=8).grid(row=8, column=1, padx=10, pady=5)

        tk.Label(dialog, text="Страховка в день").grid(row=9, column=0, padx=10, pady=5, sticky=tk.W)
        insurance_daily_var = tk.StringVar(value=str(self.insurance_daily))
        tk.Entry(dialog, textvariable=insurance_daily_var, width=8).grid(row=9, column=1, padx=10, pady=5)

        def on_save() -> None:
            try:
                currency_rate = float(currency_rate_var.get().strip() or "1")
            except ValueError:
                messagebox.showerror("Ошибка", "Курс должен быть числом")
                return

            try:
                repair_cost = float(repair_cost_var.get().strip() or "0")
                tax_rate = float(tax_rate_var.get().strip() or "0")
                capital_rate = float(capital_rate_var.get().strip() or "0")
                parking_daily = float(parking_daily_var.get().strip() or "0")
                insurance_daily = float(insurance_daily_var.get().strip() or "0")
            except ValueError:
                messagebox.showerror("Ошибка", "Значения расходов должны быть числами")
                return

            self.currency_symbol = currency_symbol_var.get().strip() or "$"
            self.currency_rate = currency_rate
            self.default_min_roi = default_roi_var.get().strip()
            self.default_min_net_profit = default_net_profit_var.get().strip()
            self.source_filter = source_filter_var.get().strip()
            self.repair_cost = repair_cost
            self.tax_rate = tax_rate
            self.monthly_capital_rate = capital_rate
            self.parking_daily = parking_daily
            self.insurance_daily = insurance_daily

            self.roi_var.set(self.default_min_roi)
            self.net_profit_var.set(self.default_min_net_profit)
            self._save_ui_settings()
            self.apply_filters()
            dialog.destroy()

        tk.Button(dialog, text="Сохранить", command=on_save).grid(row=10, column=0, padx=10, pady=10)
        tk.Button(dialog, text="Отмена", command=dialog.destroy).grid(row=10, column=1, padx=10, pady=10)

    def _build_ui(self) -> None:
        filter_frame = tk.LabelFrame(self.root, text="Фильтры")
        filter_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(filter_frame, text="Марка").grid(row=0, column=0, padx=5, pady=5)
        self.brand_var = tk.StringVar()
        tk.Entry(filter_frame, textvariable=self.brand_var, width=16).grid(row=0, column=1)

        tk.Label(filter_frame, text="ROI >=").grid(row=0, column=2, padx=5)
        roi_default = str(self.default_min_roi) if self.default_min_roi != "" else "0"
        self.roi_var = tk.StringVar(value=roi_default)
        tk.Entry(filter_frame, textvariable=self.roi_var, width=8).grid(row=0, column=3)

        tk.Label(filter_frame, text="Оценка покупки >=").grid(row=0, column=4, padx=5)
        self.buy_score_var = tk.StringVar(value="")
        tk.Entry(filter_frame, textvariable=self.buy_score_var, width=8).grid(row=0, column=5)

        tk.Label(filter_frame, text="Риск >=").grid(row=0, column=6, padx=5)
        self.risk_var = tk.StringVar(value="")
        tk.Entry(filter_frame, textvariable=self.risk_var, width=8).grid(row=0, column=7)

        tk.Label(filter_frame, text="Чистая прибыль >=").grid(row=0, column=8, padx=5)
        net_profit_default = str(self.default_min_net_profit) if self.default_min_net_profit != "" else "0"
        self.net_profit_var = tk.StringVar(value=net_profit_default)
        tk.Entry(filter_frame, textvariable=self.net_profit_var, width=10).grid(row=0, column=9)

        tk.Label(filter_frame, text="Поиск (VIN/тел/ID)").grid(row=1, column=0, padx=5, pady=5)
        self.search_var.trace_add("write", lambda *args: self.apply_filters())
        tk.Entry(filter_frame, textvariable=self.search_var, width=24).grid(row=1, column=1, columnspan=3, sticky=tk.W)

        self.show_new_only_var.set(False)
        tk.Checkbutton(
            filter_frame,
            text="Только новые",
            variable=self.show_new_only_var,
            command=self.apply_filters,
        ).grid(row=1, column=4, padx=5, sticky=tk.W)

        apply_btn = tk.Button(filter_frame, text="Применить", command=self.apply_filters)
        apply_btn.grid(row=0, column=10, padx=10)
        reload_filter_btn = tk.Button(filter_frame, text="Обновить", command=self._toggle_reload)
        reload_filter_btn.grid(row=0, column=11, padx=5)

        hint_label = tk.Label(filter_frame, text="?", fg="#0b5ed7", cursor="question_arrow")
        hint_label.grid(row=0, column=12, padx=6)
        ToolTip(
            hint_label,
            "ROI = (ожид. прибыль / цена покупки) * 100\n"
            "Ожид. продажа: медианная цена по рынку с поправками (пробег, состояние, ликвидность)\n"
            "Чистая прибыль: Ожид. продажа - цена - налоги - удержание - ремонт\n"
            "Статус: BUY WITHOUT DOUBT / BUY NOW / CONSIDER / SKIP\n"
            "Порог BUY зависит от ROI, риска и политики бренда\n\n"
            "По умолчанию показываются только авто с ROI >= 0 и прибылью >= 0",
        )

        status_frame = tk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        tk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.db_count_label = tk.Label(status_frame, text="В базе: 0", fg="#555")
        self.db_count_label.pack(side=tk.RIGHT, padx=(10, 0))
        self.ingest_label = tk.Label(status_frame, text="", fg="green", font=("Arial", 9, "bold"))
        self.ingest_label.pack(side=tk.RIGHT, padx=(20, 0))

        controls_frame = tk.Frame(self.root)
        controls_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

        parser_btn = tk.Button(controls_frame, text="Запустить парсер", command=self.run_parser)
        parser_btn.pack(side=tk.LEFT, padx=5)
        full_cycle_btn = tk.Button(controls_frame, text="Полный цикл", command=self.run_full_cycle)
        full_cycle_btn.pack(side=tk.LEFT, padx=5)
        recreate_db_btn = tk.Button(controls_frame, text="Пересоздать БД", command=self.recreate_database)
        recreate_db_btn.pack(side=tk.LEFT, padx=5)
        self.reload_btn = tk.Button(controls_frame, text="Обновить", command=self._toggle_reload)
        self.reload_btn.pack(side=tk.LEFT, padx=5)
        self.full_parse_btn = tk.Button(controls_frame, text="Парсить весь сайт", command=self.full_site_parse)
        self.full_parse_btn.pack(side=tk.LEFT, padx=5)
        import_db_btn = tk.Button(controls_frame, text="Импорт в БД", command=self.import_full_site_file)
        import_db_btn.pack(side=tk.LEFT, padx=5)
        compare_btn = tk.Button(controls_frame, text="Сравнить", command=self.compare_full_site_file)
        compare_btn.pack(side=tk.LEFT, padx=5)
        settings_btn = tk.Button(controls_frame, text="Настройки", command=self.open_settings)
        settings_btn.pack(side=tk.LEFT, padx=5)
        telegram_top5_btn = tk.Button(controls_frame, text="Отправить ТОП-5 в Telegram", command=self._send_top5_telegram)
        telegram_top5_btn.pack(side=tk.LEFT, padx=5)

        ToolTip(apply_btn, "Применить фильтры к текущему списку")
        ToolTip(reload_filter_btn, "Обновить данные из базы через API")
        ToolTip(parser_btn, "Запустить parser.py и импортировать новые объявления")
        ToolTip(full_cycle_btn, "Обновить справочник, запустить парсер, импортировать и обновить")
        ToolTip(recreate_db_btn, "Пересоздать базу данных (с резервной копией)")
        ToolTip(self.reload_btn, "Обновить данные из базы")
        ToolTip(self.full_parse_btn, "Парсинг всего сайта с текущими фильтрами")
        ToolTip(import_db_btn, "Импортировать промежуточный файл в БД")
        ToolTip(compare_btn, "Сравнить промежуточный файл с данными в БД")
        ToolTip(settings_btn, "Открыть настройки расчета")
        ToolTip(telegram_top5_btn, "Отправить 5 лучших предложений в Telegram")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.parser_tab = tk.Frame(self.notebook, bg="#f0f0f0")
        self.risks_tab = tk.Frame(self.notebook, bg="#f0f0f0")

        self.notebook.add(self.parser_tab, text="Главная / Решения")
        self.notebook.add(self.risks_tab, text="Риски")

        self._build_parser_tab()
        self._build_risks_tab()

    def _build_parser_tab(self) -> None:
        self.count_label = tk.Label(self.parser_tab, text="Объявлений: 0", bg="#f0f0f0")
        self.count_label.pack(anchor=tk.W, padx=10, pady=(5, 0))
        
        # Progress bar for full site parser
        progress_frame = tk.Frame(self.parser_tab, bg="#f0f0f0")
        progress_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        self.progress_label = tk.Label(progress_frame, text="", bg="#f0f0f0")
        self.progress_label.pack(anchor=tk.W)
        
        self.progress_bar = ttk.Progressbar(
            progress_frame, mode='indeterminate', length=400
        )
        self.progress_bar.pack(fill=tk.X, pady=(5, 0))
        
        self.parser_status_label = tk.Label(progress_frame, text="", bg="#f0f0f0")
        self.parser_status_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Таблица решений на главной вкладке
        table_frame = tk.Frame(self.parser_tab, bg="#f0f0f0")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = (
            "Оценка сделки",
            "Оценка покупки",
            "Ожид. продажа",
            "Чистая прибыль",
            "ROI",
            "Статус",
            "Марка",
            "Модель",
            "Год",
            "Цена",
        )

        # Scrollbar для таблицы решений
        tree_scroll = ttk.Scrollbar(table_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(
            table_frame, 
            columns=columns, 
            show="headings",
            yscrollcommand=tree_scroll.set
        )
        tree_scroll.config(command=self.tree.yview)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=110, anchor=tk.CENTER)

        self.tree.column("Марка", width=140, anchor=tk.W)
        self.tree.column("Модель", width=160, anchor=tk.W)

        self.tree.tag_configure("decision_buy", background="#d9f6d9")
        self.tree.tag_configure("decision_hold", background="#fff3cd")
        self.tree.tag_configure("decision_pass", background="#f8d7da")

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Button-1>", self._on_column_header_click)
        self.decisions_empty_label = tk.Label(self.parser_tab, text="Нет данных для отображения")
        self.decisions_empty_label.pack(anchor=tk.CENTER, pady=5)

        self.decisions_header_tip = HeaderToolTip(
            self.tree,
            {
                "Оценка сделки": "Итоговая оценка качества сделки",
                "Оценка покупки": "Buy score: ROI, риск, ликвидность, сделка",
                "Ожид. продажа": "Оценка цены продажи с поправками",
                "Чистая прибыль": "Ожид. продажа - цена - налоги - удержание",
                "ROI": "ROI = (прибыль / цена покупки) * 100",
                "Статус": "BUY WITHOUT DOUBT / BUY NOW / CONSIDER / SKIP",
            },
        )

    def _build_risks_tab(self) -> None:
        table_frame = tk.Frame(self.risks_tab, bg="#f0f0f0")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = (
            "Оценка риска",
            "Флаги риска",
            "Решение",
            "Марка",
            "Модель",
            "Год",
            "Цена",
            "ROI",
        )

        # Scrollbar для таблицы рисков
        risk_scroll = ttk.Scrollbar(table_frame)
        risk_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.risk_tree = ttk.Treeview(
            table_frame, 
            columns=columns, 
            show="headings",
            yscrollcommand=risk_scroll.set
        )
        risk_scroll.config(command=self.risk_tree.yview)
        
        for col in columns:
            self.risk_tree.heading(col, text=col)
            self.risk_tree.column(col, width=130, anchor=tk.CENTER)

        self.risk_tree.column("Флаги риска", width=260, anchor=tk.W)
        self.risk_tree.column("Марка", width=140, anchor=tk.W)
        self.risk_tree.column("Модель", width=160, anchor=tk.W)

        self.risk_tree.tag_configure("risk_low", background="#d9f6d9")
        self.risk_tree.tag_configure("risk_med", background="#fff3cd")
        self.risk_tree.tag_configure("risk_high", background="#f8d7da")

        self.risk_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.risk_tree.bind("<Button-1>", self._on_column_header_click)
        self.risks_empty_label = tk.Label(self.risks_tab, text="Нет данных для отображения", bg="#f0f0f0")
        self.risks_empty_label.pack(anchor=tk.CENTER, pady=5)

        self.risks_header_tip = HeaderToolTip(
            self.risk_tree,
            {
                "Оценка риска": "Чем выше, тем ниже риск",
                "Флаги риска": "Причины повышения риска",
                "Решение": "BUY WITHOUT DOUBT / BUY NOW / CONSIDER / SKIP",
                "ROI": "ROI = (прибыль / цена покупки) * 100",
            },
        )

    def _toggle_reload(self) -> None:
        # Prevent concurrent access
        if not self.reload_lock. acquire(blocking=False):
            logging.warning("Reload already in progress, ignoring click")
            return
        
        try:
            # Check if already running
            if self.reload_thread and self.reload_thread.is_alive():
                self.reload_cancelled = True
                self.reload_btn.config(text="Обновить")
                self.status_var.set("Загрузка отменена")
                return

            # Clean up completed thread
            if self.reload_thread is not None:
                try:
                    self.reload_thread.join(timeout=0.1)
                except Exception:
                    pass

            if self.keep_ingest_status_once:
                self.keep_ingest_status_once = False
            else:
                self.show_ingest_status = False
            
            self.reload_cancelled = False
            self.status_var.set("Загрузка данных...")
            
            try:
                self.reload_thread = threading.Thread(target=self._reload_data_thread, daemon=True)
                self.reload_thread.start()
                self.reload_btn.config(text="Отменить", state=tk.NORMAL)
            except Exception as e:
                logging.exception("Failed to start reload thread")
                self.status_var.set(f"Ошибка запуска загрузки: {e}")
                self.reload_thread = None
        finally:
            self.reload_lock.release()

    def _reload_data_thread(self) -> None:
        logging.info("Starting reload from API")
        try:
            rows = self._fetch_rows()
            logging.info(f"Fetched {len(rows)} rows from API")
        except httpx.HTTPError as exc:
            self.last_error = str(exc)
            self.root.after(0, lambda: self.status_var.set(f"Ошибка API: {exc}"))
            logging.exception("API error on reload")
            self.rows = []
            self.root.after(0, self.apply_filters)
            return

        if self.reload_cancelled:
            logging.info("Reload cancelled by user")
            return

        self.prev_refresh_at = self.last_refresh_at
        self.last_refresh_at = datetime.now(timezone.utc)
        self.rows = rows
        total = len(self.rows)
        logging.info(f"Setting {total} rows to self.rows")
        self.root.after(0, lambda: self.status_var.set(f"Загружено объявлений: {total}"))
        if hasattr(self, "count_label"):
            self.root.after(0, lambda: self.count_label.config(text=f"Объявлений: {total}"))
        if hasattr(self, "db_count_label"):
            self.root.after(0, lambda: self.db_count_label.config(text=f"В базе: {total}"))
        if hasattr(self, "notebook"):
            self.root.after(0, lambda: self.notebook.select(self.parser_tab))
        logging.info("Loaded %s listings, calling apply_filters", len(self.rows))
        self.root.after(0, self.apply_filters)

    def _fetch_rows(self) -> list[dict]:
        now = time.time()
        if self.api_cache_time and self.api_cache_rows is not None:
            if now - self.api_cache_time < 5:
                logging.info("Using cached API response")
                return list(self.api_cache_rows)

        url = f"{settings.api_base_url}/api/listings"
        params = {
            "company_id": settings.default_company_id,
            "with_scores": True,
            "limit": 500,  # Load latest 500 records (newest first)
            "offset": 0,
        }
        logging.info(f"Fetching from {url} with params {params}")
        with httpx.Client(timeout=60.0) as client:  # Increased timeout for large datasets
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        logging.info(f"API returned {len(payload) if isinstance(payload, list) else 'non-list'} items")
        rows = []
        for item in payload:
            rows.append({
                "listing": item["listing"],
                "scores": item["scores"],
            })

        self.api_cache_rows = list(rows)
        self.api_cache_time = now
        return rows

    def run_parser(self) -> None:
        self.status_var.set("Запуск парсера...")
        logging.info("Starting parser")
        thread = threading.Thread(target=self._run_parser_thread, daemon=True)
        thread.start()

    def run_full_cycle(self) -> None:
        if self.full_cycle_running:
            self.status_var.set("Полный цикл уже запущен")
            return

        self.full_cycle_running = True
        self.status_var.set("Полный цикл: запуск...")
        thread = threading.Thread(target=self._full_cycle_thread, daemon=True)
        thread.start()

    def _maybe_sync_models(self) -> None:
        """DISABLED: Automatic model sync removed. Official Postman API docs provide same data.
        
        Models/manufacturers are static and don't require daily updates.
        See: MyAuto API Documentation.postman_collection.json
        """
        pass

    def _full_cycle_thread(self) -> None:
        try:
            if not self.api_process or self.api_process.poll() is not None:
                self._start_api_thread()

            result = subprocess.run(
                [sys.executable, "parser.py"],
                capture_output=False,
            )
            if result.returncode != 0:
                self.root.after(0, lambda: self.status_var.set("Парсер завершился с ошибкой"))
                logging.error("Parser failed with code %s", result.returncode)
                return

            ingested = self._ingest_via_api()
            self.last_ingest_count = ingested
            self.show_ingest_status = True
            self.keep_ingest_status_once = True
            self.ingest_label.config(text=f"✓ Импорт: {ingested} записей")
            self.root.after(0, lambda: self.status_var.set(f"Импорт завершён: {ingested} записей"))
            self.root.after(0, self._toggle_reload)
            self.root.after(0, lambda: self.status_var.set(
                f"Полный цикл завершён | Импорт завершён: {ingested} записей"
            ))
        except httpx.HTTPError as exc:
            self.last_error = str(exc)
            self.root.after(0, lambda: self.status_var.set(f"Ошибка API: {exc}"))
        finally:
            self.full_cycle_running = False

    def recreate_database(self) -> None:
        db_path = Path("mileon_saas.db")
        confirm = messagebox.askyesno(
            "Пересоздать базу данных",
            "Удалить и пересоздать mileon_saas.db? Все данные объявлений будут потеряны.",
        )
        if not confirm:
            return

        self.status_var.set("Остановка API и закрытие БД...")
        self._stop_api_process(force=True)
        
        # Close database connections before deleting
        try:
            asyncio.run(close_engine())
            logging.info("Database engine closed")
        except Exception as exc:
            logging.warning("Failed to close engine: %s", exc)
        
        # Wait for all processes to fully release the database file
        time.sleep(3)  # Increased wait from 2s to 3s
        
        # Kill related Python processes that might hold DB locks (exclude current PID)
        try:
            killed = self._kill_related_processes()
            if killed:
                logging.info("Killed related processes: %s", ", ".join(killed))
        except Exception as exc:
            logging.warning("Failed to kill related processes: %s", exc)
        
        time.sleep(2)  # Increased wait from 1s to 2s

        if db_path.exists():
            backup_dir = Path("backups")
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"mileon_saas_{timestamp}.db"
            try:
                shutil.copy2(db_path, backup_path)
                self.status_var.set(f"Резервная копия создана: {backup_path.name}")
                logging.info("Backup created: %s", backup_path)
            except OSError as exc:
                self.status_var.set(f"Ошибка резервного копирования: {exc}")
                logging.warning("Backup failed: %s", exc)
                return

        # Try to delete the database file and WAL/SHM lock files multiple times with increasing delays
        max_attempts = 6
        for attempt in range(max_attempts):
            try:
                # Delete main database file
                if db_path.exists():
                    db_path.unlink()
                    logging.info("Database file deleted successfully on attempt %d", attempt + 1)
                
                # Delete WAL (Write-Ahead Log) file if it exists
                wal_path = db_path.with_name(db_path.name + "-wal")
                if wal_path.exists():
                    wal_path.unlink()
                    logging.info("WAL file deleted: %s", wal_path.name)
                
                # Delete SHM (Shared Memory) file if it exists
                shm_path = db_path.with_name(db_path.name + "-shm")
                if shm_path.exists():
                    shm_path.unlink()
                    logging.info("SHM file deleted: %s", shm_path.name)
                
                # If all deletions successful, break
                if not db_path.exists() and not wal_path.exists() and not shm_path.exists():
                    break
            except OSError as exc:
                logging.warning("Attempt %d to delete DB/WAL/SHM failed: %s", attempt + 1, exc)
                if attempt == max_attempts - 1:
                    self.status_var.set(f"Ошибка удаления базы: {exc}")
                    messagebox.showerror(
                        "Не удалось удалить базу",
                        "Файл занят другим процессом.\n\n"
                        "Пожалуйста, закройте вручную все запуски Python/API через:\n"
                        "Диспетчер задач → Завершить процесс\n\n"
                        "Затем повторите попытку.",
                    )
                    # Try to rename the file instead if deletion fails
                    try:
                        temp_path = db_path.with_name(db_path.name + ".old")
                        if temp_path.exists():
                            temp_path.unlink()
                        db_path.rename(temp_path)
                        self.status_var.set(f"Файл переименован в {temp_path.name}")
                        logging.info("Database file renamed to %s", temp_path.name)
                    except OSError as rename_exc:
                        logging.error("Failed to rename database: %s", rename_exc)
                        return
                else:
                    wait_time = 1.0 * (attempt + 1)  # 1s, 2s, 3s, 4s, 5s, 6s
                    time.sleep(wait_time)

        self.rows = []
        self.apply_filters()
        self.status_var.set("База данных удалена, пересоздаю...")
        thread = threading.Thread(target=self._init_db_thread, daemon=True)
        thread.start()

    def _init_db_thread(self) -> None:
        try:
            # First, close all existing connections
            asyncio.run(close_engine())
            time.sleep(1)  # Give connections time to close
            
            # Then recreate the database
            asyncio.run(init_db())
            logging.info("Database successfully recreated")
        except Exception as exc:
            logging.exception("Error recreating database")
            error_msg = f"Ошибка создания БД: {exc}"
            self.root.after(0, lambda msg=error_msg: self.status_var.set(msg))
            return
        self.root.after(0, lambda: self.status_var.set("База данных пересоздана, запускаю API..."))
        time.sleep(2)  # Give DB time to be fully ready
        self._start_api_thread()

    def _stop_api_process(self, force: bool = False) -> None:
        terminated: list[dict[str, str]] = []
        
        # First, try to terminate our own API process
        if self.api_process and self.api_process.poll() is None:
            self.status_var.set("Остановка API...")
            try:
                self.api_process.terminate()
                self.api_process.wait(timeout=2)
                if self.api_process.pid:
                    terminated.append({
                        "pid": str(self.api_process.pid),
                        "name": Path(sys.executable).name,
                    })
            except subprocess.TimeoutExpired:
                try:
                    self.api_process.kill()
                    self.api_process.wait(timeout=2)
                except Exception:
                    pass
                if self.api_process.pid:
                    terminated.append({
                        "pid": str(self.api_process.pid),
                        "name": Path(sys.executable).name,
                    })
            except OSError:
                pass

            time.sleep(0.5)

        # If force mode, also kill all uvicorn processes by command line
        if force:
            extra_items = self._kill_api_by_cmdline()
            for item in extra_items:
                if item not in terminated:
                    terminated.append(item)

        if terminated:
            pid_list = ", ".join(f"{item['name']}({item['pid']})" for item in terminated)
            self.status_var.set(f"Завершены процессы: {pid_list}")
            logging.info("Terminated processes: %s", pid_list)

    def _kill_api_by_cmdline(self) -> list[dict[str, str]]:
        list_command = (
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.CommandLine -match 'uvicorn' -and "
            "$_.CommandLine -match 'mileon_saas.api.main:app' } | "
            "Select-Object ProcessId,Name | ConvertTo-Json -Compress"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", list_command],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return []

        payload = result.stdout.strip()
        if not payload:
            return []

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return []

        if isinstance(data, dict):
            items = [data]
        elif isinstance(data, list):
            items = data
        else:
            return []

        pids = [item.get("ProcessId") for item in items if item.get("ProcessId")]
        if not pids:
            return []

        stop_command = "Stop-Process -Id " + ",".join(str(pid) for pid in pids) + " -Force"
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", stop_command],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return []

        result_items = []
        for item in items:
            pid = item.get("ProcessId")
            name = item.get("Name") or "process"
            if pid:
                result_items.append({"pid": str(pid), "name": str(name)})
        return result_items

    def _kill_related_processes(self) -> list[str]:
        current_pid = os.getpid()
        list_command = (
            f"$currentPid = {current_pid}; "
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.CommandLine -and $_.ProcessId -ne $currentPid -and "
            "$_.CommandLine -match 'uvicorn|mileon_saas|parser.py|full_site_parser|gui|main.py' } | "
            "Select-Object ProcessId,Name | ConvertTo-Json -Compress"
        )

        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", list_command],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return []

        payload = result.stdout.strip()
        if not payload:
            return []

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return []

        items = [data] if isinstance(data, dict) else data if isinstance(data, list) else []
        pids = [item.get("ProcessId") for item in items if item.get("ProcessId")]
        if not pids:
            return []

        stop_command = "Stop-Process -Id " + ",".join(str(pid) for pid in pids) + " -Force"
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", stop_command],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return []

        return [f"{item.get('Name','process')}({item.get('ProcessId')})" for item in items]

    def _start_api_thread(self) -> None:
        # Close any existing log handle first
        if self.api_log_handle:
            try:
                self.api_log_handle.close()
            except OSError:
                pass
            self.api_log_handle = None

        # Start the API process with stdout/stderr going to DEVNULL
        # Logging is already handled by Python's logging module -> app.log
        self.api_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "mileon_saas.api.main:app",
                "--reload",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if self._wait_for_api():
            self.root.after(0, lambda: self.status_var.set("API запущен"))
            logging.info("API started successfully")
        else:
            self.root.after(0, lambda: self.status_var.set("API не запустился (см. app.log)"))
            logging.error("API failed to start")

    def _wait_for_api(self, timeout_seconds: int = 15) -> bool:
        deadline = time.time() + timeout_seconds
        url = f"{settings.api_base_url}/health"
        while time.time() < deadline:
            try:
                response = httpx.get(url, timeout=3.0)
                if response.status_code == 200:
                    return True
            except httpx.HTTPError:
                logging.warning("API not ready yet")
                time.sleep(1.0)
        return False

    def _run_parser_thread(self) -> None:
        result = subprocess.run(
            [sys.executable, "parser.py"],
            capture_output=False,
        )
        if result.returncode != 0:
            self.root.after(0, lambda: self.status_var.set("Парсер завершился с ошибкой"))
            logging.error("Parser failed with code %s", result.returncode)
            return

        try:
            ingested = self._ingest_via_api()
            self.last_ingest_count = ingested
            self.show_ingest_status = True
            self.keep_ingest_status_once = True
            self.ingest_label.config(text=f"✓ Импорт: {ingested} записей")
            self.root.after(0, lambda: self.status_var.set(f"Импорт завершён: {ingested} записей"))
            self.root.after(0, self._toggle_reload)
        except httpx.HTTPError as exc:
            message = str(exc)
            self.last_error = message
            self.root.after(0, lambda: self.status_var.set(f"Ошибка импорта: {message}"))
            logging.exception("Ingest failed after parser")

    def _ingest_via_api(self, path: str = "cars_data.json") -> int:
        if not self._wait_for_api():
            logging.error("API unavailable for ingest")
            raise httpx.ConnectError("API недоступен", request=None)
        url = f"{settings.api_base_url}/api/listings/ingest"
        params = {
            "path": path,
            "company_id": settings.default_company_id,
        }
        # Increase timeout for large file imports (28MB+ files can take 60+ seconds)
        with httpx.Client(timeout=120.0) as client:
            response = client.post(url, params=params)
            response.raise_for_status()
            payload = response.json()
        ingested = payload.get("ingested", 0) if isinstance(payload, dict) else 0
        return ingested if isinstance(ingested, int) else 0

    def import_full_site_file(self) -> None:
        file_path = self.last_full_parse_file or "full_site_merged.json"
        if not Path(file_path).exists():
            self.status_var.set(f"Файл не найден: {file_path}")
            return

        self.status_var.set("Импортирую файл в БД...")
        thread = threading.Thread(target=self._import_full_site_thread, args=(file_path,), daemon=True)
        thread.start()

    def _import_full_site_thread(self, file_path: str) -> None:
        try:
            ingested = self._ingest_via_api(file_path)
            self.last_ingest_count = ingested
            self.show_ingest_status = True
            self.keep_ingest_status_once = True
            self.root.after(0, lambda: self.ingest_label.config(text=f"✓ Импорт: {ingested} записей"))
            self.root.after(0, lambda: self.status_var.set(f"Импорт завершён: {ingested} записей"))
            self.root.after(0, self._toggle_reload)
        except httpx.HTTPError as exc:
            message = str(exc)
            self.last_error = message
            self.root.after(0, lambda: self.status_var.set(f"Ошибка импорта: {message}"))
            logging.exception("Manual ingest failed")

    def compare_full_site_file(self) -> None:
        file_path = self.last_full_parse_file or "full_site_merged.json"
        if not Path(file_path).exists():
            self.status_var.set(f"Файл не найден: {file_path}")
            return

        self.status_var.set("Сравниваю файл с БД...")
        thread = threading.Thread(target=self._compare_full_site_thread, args=(file_path,), daemon=True)
        thread.start()

    def _compare_full_site_thread(self, file_path: str) -> None:
        compare = self._compare_db_with_file(file_path)
        if not compare:
            return

        compare_msg = (
            f"Сравнение: файл {compare['file_count']} | БД {compare['db_count']} "
            f"| нет в БД {compare['missing']} | лишние {compare['extra']}"
        )
        self.root.after(0, lambda: self.parser_status_label.config(text=compare_msg))
        self.root.after(0, lambda: self.status_var.set(compare_msg))

    def _compare_db_with_file(self, file_path: str) -> dict[str, int] | None:
        file_ids: set[str] = set()
        try:
            payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logging.exception("Failed to read intermediate file")
            self.root.after(0, lambda: self.status_var.set(f"Ошибка чтения файла: {exc}"))
            return None

        if isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict):
                    continue
                car_id = item.get("car_id")
                if car_id is not None:
                    file_ids.add(str(car_id))

        if not file_ids:
            self.root.after(0, lambda: self.status_var.set("Файл не содержит объявлений"))
            return None

        try:
            url = f"{settings.api_base_url}/api/listings"
            params = {
                "company_id": settings.default_company_id,
                "with_scores": False,
            }
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                db_payload = response.json()
        except httpx.HTTPError as exc:
            logging.exception("Failed to fetch listings for comparison")
            self.root.after(0, lambda: self.status_var.set(f"Ошибка сравнения: {exc}"))
            return None

        db_ids: set[str] = set()
        if isinstance(db_payload, list):
            for item in db_payload:
                if not isinstance(item, dict):
                    continue
                listing = item.get("listing") if "listing" in item else item
                if isinstance(listing, dict):
                    source_id = listing.get("source_listing_id") or listing.get("car_id")
                    if source_id is not None:
                        db_ids.add(str(source_id))

        missing_in_db = file_ids - db_ids
        extra_in_db = db_ids - file_ids
        return {
            "file_count": len(file_ids),
            "db_count": len(db_ids),
            "missing": len(missing_in_db),
            "extra": len(extra_in_db),
        }

    def _send_top5_telegram(self) -> None:
        """Send TOP-5 best deals to Telegram subscribers."""
        self.status_var.set("Отправка ТОП-5 в Telegram...")
        thread = threading.Thread(target=self._send_top5_telegram_thread, daemon=True)
        thread.start()

    def _send_top5_telegram_thread(self) -> None:
        """Background thread for sending TOP-5 to Telegram."""
        try:
            url = f"{settings.api_base_url}/api/listings/send-top5-telegram"
            params = {
                "company_id": settings.default_company_id,
            }
            logging.info(f"Sending TOP-5 to Telegram via {url}")
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, params=params)
                response.raise_for_status()
                result = response.json()
                
                sent = result.get("sent", 0)
                status_msg = f"✓ ТОП-5 отправлено подписчикам: {sent}"
                logging.info(status_msg)
                self.root.after(0, lambda: self.status_var.set(status_msg))
        except httpx.HTTPError as exc:
            logging.exception("Failed to send TOP-5 to Telegram")
            error_msg = f"Ошибка отправки в Telegram: {exc}"
            self.root.after(0, lambda: self.status_var.set(error_msg))

    def apply_filters(self) -> None:
        logging.info(f"apply_filters called with {len(self.rows)} rows")
        self.filters["brand"] = self.brand_var.get().strip().lower()
        self.filters["min_roi"] = None
        if self.roi_var.get().strip():
            try:
                self.filters["min_roi"] = float(self.roi_var.get())
            except ValueError:
                self.filters["min_roi"] = None

        self.filters["min_buy_score"] = None
        if self.buy_score_var.get().strip():
            try:
                self.filters["min_buy_score"] = float(self.buy_score_var.get())
            except ValueError:
                self.filters["min_buy_score"] = None

        self.filters["min_risk"] = None
        if self.risk_var.get().strip():
            try:
                self.filters["min_risk"] = float(self.risk_var.get())
            except ValueError:
                self.filters["min_risk"] = None

        self.filters["min_net_profit"] = None
        if self.net_profit_var.get().strip():
            try:
                self.filters["min_net_profit"] = float(self.net_profit_var.get())
            except ValueError:
                self.filters["min_net_profit"] = None

        logging.info(f"Active filters: brand='{self.filters['brand']}', roi>={self.filters['min_roi']}, buy_score>={self.filters['min_buy_score']}, risk>={self.filters['min_risk']}, net_profit>={self.filters['min_net_profit']}, source_filter='{self.source_filter}', search='{self.search_var.get().strip()}', show_new_only={self.show_new_only_var.get()}")
        filtered = []
        for row in self.rows:
            listing = row["listing"]
            scores = row["scores"]

            brand_value = (listing.get("brand") or "").lower()
            if self.filters["brand"] and self.filters["brand"] not in brand_value:
                continue
            if self.source_filter:
                source_value = (listing.get("source") or "").lower()
                if self.source_filter.lower() not in source_value:
                    continue
            if self.filters["min_roi"] is not None and scores["roi_percent"] < self.filters["min_roi"]:
                continue
            if self.filters["min_buy_score"] is not None and scores["buy_score"] < self.filters["min_buy_score"]:
                continue
            if self.filters["min_risk"] is not None and scores["risk_score"] < self.filters["min_risk"]:
                continue
            if self.filters["min_net_profit"] is not None and scores.get("net_profit", 0) < self.filters["min_net_profit"]:
                continue

            search_text = self.search_var.get().strip().lower()
            if search_text and not self._matches_search(listing, search_text):
                continue

            if self.show_new_only_var.get() and self.prev_refresh_at:
                if not self._is_new_listing(listing, self.prev_refresh_at):
                    continue

            filtered.append(row)

        logging.info(f"After filtering: {len(filtered)} / {len(self.rows)} rows")
        status_text = f"Показано: {len(filtered)} / {len(self.rows)}"
        if self.show_ingest_status and self.last_ingest_count is not None:
            status_text = f"{status_text} | Импорт завершён: {self.last_ingest_count} записей"
        self.status_var.set(status_text)
        logging.info(f"Rendering {len(filtered)} rows to table")
        self._render_table(filtered)

    def _parse_listing_time(self, value) -> datetime | None:
        if isinstance(value, datetime):
            if value.tzinfo:
                return value.astimezone(timezone.utc).replace(tzinfo=None)
            return value
        if not value:
            return None
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo:
                    return parsed.astimezone(timezone.utc).replace(tzinfo=None)
                return parsed
            except ValueError:
                return None
        return None

    def _is_new_listing(self, listing: dict, since: datetime) -> bool:
        created_at = self._parse_listing_time(listing.get("created_at"))
        if not created_at:
            return False
        return created_at > since

    def _format_money(self, value) -> str:
        if value is None:
            return ""
        try:
            amount = float(value) * float(self.currency_rate)
        except (TypeError, ValueError):
            return ""
        return f"{self.currency_symbol}{amount:.0f}"

    def _matches_search(self, listing: dict, search_text: str) -> bool:
        candidates = [
            listing.get("vin"),
            listing.get("source_listing_id"),
            listing.get("id"),
            listing.get("car_id"),
            listing.get("phone"),
            listing.get("client_phone"),
        ]
        for value in candidates:
            if value is None:
                continue
            if search_text in str(value).lower():
                return True
        return False

    def _decision_tag(self, decision: str | None) -> str | None:
        if not decision:
            return None
        value = decision.strip().lower()
        if value == "buy":
            return "decision_buy"
        if value == "hold":
            return "decision_hold"
        if value == "pass":
            return "decision_pass"
        return None

    def _risk_tag(self, risk_score: float | None) -> str | None:
        if not isinstance(risk_score, (int, float)):
            return None
        if risk_score >= 70:
            return "risk_high"
        if risk_score >= 40:
            return "risk_med"
        return "risk_low"

    def full_site_parse(self) -> None:
        """Start full site parsing in background thread."""
        if self.full_parser_running:
            self.status_var.set("Парсинг уже запущен")
            return
        
        self.full_parser_running = True
        self.full_parse_btn.config(state=tk.DISABLED)
        self.parser_start_time = time.time()
        
        thread = threading.Thread(target=self._full_parse_thread, daemon=True)
        thread.start()
        
        # Start timer for progress updates
        self._update_parser_timer()

    def _full_parse_thread(self) -> None:
        """Thread function for parsing full site."""
        try:
            def progress_cb(count: int, elapsed: float):
                """Callback for progress updates."""
                self.root.after(0, lambda: self._update_parser_ui(count, elapsed))
            
            full_site_params = {
                "vehicleType": 0,
                "hideDealPrice": 1,
                "bargainType": 0,
                "ForRent": "",
                "Mans": "",
                "PriceFrom": "",
                "PriceTo": "",
                "CurrencyID": 1,
                "MileageType": 1,
                "Customs": "",
            }
            allowed_locations = {
                2, 3, 4, 7, 15, 30, 113, 53, 39, 38, 37, 36, 40, 41, 44, 31,
                5, 47, 48, 52, 8, 54, 16, 6, 14, 13, 12, 11, 10, 9, 55, 56,
                57, 59, 58, 61, 62, 63, 64, 66, 71, 72, 74, 75, 76, 77, 78,
                80, 81, 82, 83, 84, 85, 86, 87, 88, 91, 96, 97, 101, 109,
                116, 119, 122, 127, 131, 133, 137, 139, 143,
            }
            parser = FullSiteParser(
                delay_seconds=2.0,
                progress_callback=progress_cb,
                query_params=full_site_params,
                allowed_locations=allowed_locations,
            )

            # Parse all pages without deduplication to refresh full data
            parser.parse_all_pages(max_pages=None, skip_existing=False)
            
            # Save to file
            output_file = parser.save_to_file()
            self.last_full_parse_file = output_file

            # Import parsed data into DB and refresh UI
            try:
                ingested = self._ingest_via_api(output_file)
                self.last_ingest_count = ingested
                self.show_ingest_status = True
                self.keep_ingest_status_once = True
                self.ingest_label.config(text=f"✓ Импорт: {ingested} записей")
                self.root.after(0, lambda: self.status_var.set(f"Импорт завершён: {ingested} записей"))
                self.root.after(0, self._toggle_reload)
            except httpx.HTTPError as exc:
                self.last_error = str(exc)
                self.root.after(0, lambda: self.status_var.set(f"Ошибка импорта: {exc}"))
                logging.exception("Ingest failed after full site parse")

            compare = self._compare_db_with_file(output_file)
            if compare:
                compare_msg = (
                    f"Сравнение: файл {compare['file_count']} | БД {compare['db_count']} "
                    f"| нет в БД {compare['missing']} | лишние {compare['extra']}"
                )
                self.root.after(0, lambda: self.parser_status_label.config(text=compare_msg))
                self.root.after(0, lambda: self.status_var.set(compare_msg))
            
            elapsed = time.time() - self.parser_start_time
            
            # Calculate skipped count
            skipped_count = 0
            
            self.root.after(0, lambda: self._finish_parsing(
                parser.new_listings_count, 
                output_file, 
                elapsed,
                total_checked=len(parser.all_listings) + skipped_count,
                skipped=skipped_count
            ))
        except Exception as e:
            self.last_error = str(e)
            self.root.after(0, lambda: self._finish_parsing_error(str(e)))

    def _update_parser_ui(self, count: int, elapsed: float) -> None:
        """Update progress bar UI."""
        elapsed_str = self._format_time(elapsed)
        self.progress_label.config(text=f"Загружено: {count} объявлений | Время: {elapsed_str}")
        
        # Animate progress bar
        if not self.progress_bar.winfo_exists():
            return
        
        if self.progress_bar['value'] == 100:
            self.progress_bar['value'] = 0
        else:
            self.progress_bar['value'] += 1

    def _update_parser_timer(self) -> None:
        """Update elapsed time display."""
        if not self.full_parser_running:
            return
        
        elapsed = time.time() - self.parser_start_time
        elapsed_str = self._format_time(elapsed)
        
        # Update status if no callback has updated recently
        if not self.progress_label.cget("text"):
            self.progress_label.config(text=f"Парсинг... | Время: {elapsed_str}")
        
        self.parser_timer_id = self.root.after(1000, self._update_parser_timer)

    def _finish_parsing(self, total_items: int, output_file: str, elapsed: float, total_checked: int = 0, skipped: int = 0) -> None:
        """Handle successful parsing completion."""
        self.full_parser_running = False
        self.full_parse_btn.config(state=tk.NORMAL)
        self.progress_bar.stop()
        
        elapsed_str = self._format_time(elapsed)
        
        # Format message with deduplication info
        if skipped > 0:
            msg = f"✓ Парсинг завершен: {total_items} новых + {skipped} пропущено (дубли) | Время: {elapsed_str}"
            status_msg = f"Новых: {total_items} | Пропущено: {skipped} | Файл: {output_file}"
            status_summary = f"Парсинг завершен: {total_items} новых объявлений, {skipped} дубликатов пропущено"
        else:
            msg = f"✓ Парсинг завершен: {total_items} объявлений | Время: {elapsed_str}"
            status_msg = f"Сохранено в: {output_file}"
            status_summary = f"Парсинг завершен: {total_items} объявлений загружено"
        
        self.progress_label.config(text=msg)
        self.parser_status_label.config(text=status_msg)
        if self.show_ingest_status and self.last_ingest_count is not None:
            status_summary = f"{status_summary} | Импорт завершён: {self.last_ingest_count} записей"
        self.status_var.set(status_summary)
        logging.info(f"Full site parsing completed: {total_items} new items, {skipped} duplicates skipped in {elapsed_str}")

    def _finish_parsing_error(self, error_msg: str) -> None:
        """Handle parsing error."""
        self.full_parser_running = False
        self.full_parse_btn.config(state=tk.NORMAL)
        self.progress_bar.stop()
        
        self.progress_label.config(text="✗ Ошибка при парсинге")
        self.parser_status_label.config(text=error_msg, foreground="red")
        self.status_var.set("Ошибка парсинга")
        logging.exception("Full site parsing failed")

    def _sort_rows_by_column(self, rows: list[dict], column: str, reverse: bool = False) -> list[dict]:
        """Sort rows by column value."""
        sort_keys = {
            "Оценка сделки": lambda r: r["scores"]["deal_score"],
            "Оценка покупки": lambda r: r["scores"]["buy_score"],
            "Ожид. продажа": lambda r: r["scores"]["expected_sell_price"],
            "Чистая прибыль": lambda r: r["scores"]["net_profit"],
            "ROI": lambda r: (r["scores"]["roi_percent"], r["scores"]["net_profit"]),  # Sort by ROI, then profit
            "Статус": lambda r: r["scores"]["decision"],
            "Оценка риска": lambda r: r["scores"]["risk_score"],
            "Марка": lambda r: (r["listing"].get("brand") or "").lower(),
            "Модель": lambda r: (r["listing"].get("model") or "").lower(),
            "Год": lambda r: r["listing"].get("year") or 0,
            "Цена": lambda r: r["listing"].get("price_usd") or 0,
        }
        
        if column not in sort_keys:
            return rows
        
        return sorted(rows, key=sort_keys[column], reverse=reverse)

    def _on_tree_double_click(self, event) -> None:
        """Navigate to listing URL on double-click."""
        selection = self.tree.selection()
        if not selection:
            return

        item_id = selection[0]
        tags = self.tree.item(item_id, "tags")
        if tags and len(tags) > 0:
            source_listing_id = tags[0]
            url = f"https://www.myauto.ge/ka/pr/{source_listing_id}"
            try:
                webbrowser.open(url)
                logging.info(f"Opened URL: {url}")
            except Exception as exc:
                self.last_error = str(exc)
                logging.exception("Failed to open browser")

    def _on_column_header_click(self, event) -> None:
        """Sort table by column on header click."""
        region = self.tree.identify_region(event.x, event.y)
        if region != "heading":
            return

        col = self.tree.identify_column(event.x)
        col_index = int(col[1:]) - 1
        
        columns = event.widget["columns"]
        
        if col_index < 0 or col_index >= len(columns):
            return

        column_name = columns[col_index]
        
        # Toggle sort direction if same column clicked
        if self.sort_column == column_name:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column_name
            self.sort_reverse = False
        
        self.apply_filters()

    def _render_table(self, rows: list[dict]) -> None:
        logging.info(f"_render_table called with {len(rows)} rows")
        for item in self.tree.get_children():
            self.tree.delete(item)

        for item in self.risk_tree.get_children():
            self.risk_tree.delete(item)

        if hasattr(self, "decisions_empty_label"):
            if rows:
                self.decisions_empty_label.pack_forget()
                logging.info("Hiding empty label")
            else:
                self.decisions_empty_label.pack(anchor=tk.CENTER, pady=5)
                logging.info("Showing 'No data' label")

        if hasattr(self, "risks_empty_label"):
            if rows:
                self.risks_empty_label.pack_forget()
            else:
                self.risks_empty_label.pack(anchor=tk.CENTER, pady=5)

        # Apply sorting if column is selected
        sorted_rows = rows
        if self.sort_column:
            sorted_rows = self._sort_rows_by_column(rows, self.sort_column, self.sort_reverse)

        for row in sorted_rows:
            listing = row["listing"]
            scores = row["scores"]
            source_listing_id = listing.get("source_listing_id", "")
            decision_tag = self._decision_tag(scores.get("decision"))
            decision_tags = [tag for tag in [source_listing_id, decision_tag] if tag]
            self.tree.insert(
                "",
                "end",
                values=(
                    f"{scores['deal_score']:.1f}",
                    f"{scores['buy_score']:.1f}",
                    self._format_money(scores.get("expected_sell_price")),
                    self._format_money(scores.get("net_profit")),
                    f"{scores['roi_percent']:.1f}%",
                    scores["decision"],
                    listing.get("brand", ""),
                    listing.get("model", ""),
                    listing.get("year") or "",
                    self._format_money(listing.get("price_usd")),
                ),
                tags=tuple(decision_tags),
            )
            risk_tag = self._risk_tag(scores.get("risk_score"))
            self.risk_tree.insert(
                "",
                "end",
                values=(
                    f"{scores['risk_score']:.1f}",
                    ", ".join(scores.get("risk_flags", [])),
                    scores["decision"],
                    listing.get("brand", ""),
                    listing.get("model", ""),
                    listing.get("year") or "",
                    self._format_money(listing.get("price_usd")),
                    f"{scores['roi_percent']:.1f}%",
                ),
                tags=(risk_tag,) if risk_tag else (),
            )


def main() -> None:
    root = tk.Tk()
    app = SaaSApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Графический интерфейс на tkinter для мониторинга автомобилей
Более стабильная версия с встроенными библиотеками
"""
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import threading
import subprocess
import sys
from datetime import datetime
from io import StringIO

# ==================== КОНФИГУРАЦИЯ ====================
DATA_FILE = 'cars_data.json'
HISTORY_FILE = 'cars_history.json'
# ======================================================

class CarMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title('🚗 Car Market Monitor - myauto.ge')
        self.root.geometry('1200x750')
        
        # Цветовая схема
        self.bg_dark = '#1a1a1a'
        self.bg_light = '#2a2a2a'
        self.text_color = '#ffffff'
        self.accent_color = '#00AAFF'
        
        self.root.configure(bg=self.bg_dark)
        
        self.cars_data = []
        self.filtered_cars = []
        self.parsing_thread = None
        
        self.create_ui()
        self.load_data()
        
    def create_ui(self):
        """Создает интерфейс приложения"""
        
        # ===== Шапка =====
        header_frame = tk.Frame(self.root, bg=self.accent_color, height=40)
        header_frame.pack(fill=tk.X)
        header_label = tk.Label(header_frame, text='🚗 ПАНЕЛЬ МОНИТОРИНГА АВТОМОБИЛЕЙ', 
                               font=('Arial', 14, 'bold'), bg=self.accent_color, fg='white')
        header_label.pack(pady=10)
        
        # ===== Фрейм с фильтрами =====
        filter_frame = tk.LabelFrame(self.root, text='🔍 ФИЛЬТРЫ', font=('Arial', 10, 'bold'),
                                    bg=self.bg_light, fg=self.text_color, padx=10, pady=10)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Фильтр по модели
        tk.Label(filter_frame, text='Модель:', bg=self.bg_light, fg=self.text_color).grid(row=0, column=0, sticky=tk.W)
        self.model_var = tk.StringVar()
        self.model_var.trace_add('write', lambda *args: self.apply_filters())
        tk.Entry(filter_frame, textvariable=self.model_var, width=15, bg=self.bg_dark, fg=self.text_color).grid(row=0, column=1, padx=5)
        
        # Фильтр по марке
        tk.Label(filter_frame, text='Марка:', bg=self.bg_light, fg=self.text_color).grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        self.make_var = tk.StringVar()
        self.make_var.trace_add('write', lambda *args: self.apply_filters())
        tk.Entry(filter_frame, textvariable=self.make_var, width=15, bg=self.bg_dark, fg=self.text_color).grid(row=0, column=3, padx=5)
        
        # Фильтр по цене
        tk.Label(filter_frame, text='Цена ($):', bg=self.bg_light, fg=self.text_color).grid(row=0, column=4, sticky=tk.W, padx=(10, 0))
        self.price_min_var = tk.StringVar()
        self.price_min_var.trace_add('write', lambda *args: self.apply_filters())
        tk.Entry(filter_frame, textvariable=self.price_min_var, width=8, bg=self.bg_dark, fg=self.text_color).grid(row=0, column=5, padx=2)
        
        tk.Label(filter_frame, text='-', bg=self.bg_light, fg=self.text_color).grid(row=0, column=6, padx=2)
        
        self.price_max_var = tk.StringVar()
        self.price_max_var.trace_add('write', lambda *args: self.apply_filters())
        tk.Entry(filter_frame, textvariable=self.price_max_var, width=8, bg=self.bg_dark, fg=self.text_color).grid(row=0, column=7, padx=2)
        
        # Фильтр по году
        tk.Label(filter_frame, text='Год:', bg=self.bg_light, fg=self.text_color).grid(row=0, column=8, sticky=tk.W, padx=(10, 0))
        self.year_min_var = tk.StringVar()
        self.year_min_var.trace_add('write', lambda *args: self.apply_filters())
        tk.Entry(filter_frame, textvariable=self.year_min_var, width=6, bg=self.bg_dark, fg=self.text_color).grid(row=0, column=9, padx=2)
        
        tk.Label(filter_frame, text='-', bg=self.bg_light, fg=self.text_color).grid(row=0, column=10, padx=2)
        
        self.year_max_var = tk.StringVar()
        self.year_max_var.trace_add('write', lambda *args: self.apply_filters())
        tk.Entry(filter_frame, textvariable=self.year_max_var, width=6, bg=self.bg_dark, fg=self.text_color).grid(row=0, column=11, padx=2)
        
        # Фильтр по рейтингу
        tk.Label(filter_frame, text='Рейтинг ≥:', bg=self.bg_light, fg=self.text_color).grid(row=0, column=12, sticky=tk.W, padx=(10, 0))
        self.rating_var = tk.StringVar(value='0')
        self.rating_var.trace_add('write', lambda *args: self.apply_filters())
        rating_combo = ttk.Combobox(filter_frame, textvariable=self.rating_var, 
                                    values=['0', '50', '60', '70', '80', '90'], 
                                    width=6, state='readonly')
        rating_combo.grid(row=0, column=13, padx=5)
        
        # ===== Фрейм с кнопками =====
        button_frame = tk.Frame(self.root, bg=self.bg_dark)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(button_frame, text='🔄 Обновить парсер', command=self.refresh_parser,
                 bg='#0066cc', fg='white', font=('Arial', 10, 'bold'), padx=10, pady=5).pack(side=tk.LEFT, padx=2)
        
        tk.Button(button_frame, text='🔄 Перезагрузить данные', command=self.load_data,
                 bg='#00cc66', fg='white', font=('Arial', 10, 'bold'), padx=10, pady=5).pack(side=tk.LEFT, padx=2)
        
        tk.Button(button_frame, text='� Открыть ссылку', command=self.open_link,
                 bg='#cc6600', fg='white', font=('Arial', 10, 'bold'), padx=10, pady=5).pack(side=tk.LEFT, padx=2)
        
        tk.Button(button_frame, text='📋 Копировать ссылку', command=self.copy_link,
                 bg='#cc9900', fg='white', font=('Arial', 10, 'bold'), padx=10, pady=5).pack(side=tk.LEFT, padx=2)
        
        tk.Button(button_frame, text='❌ Выход', command=self.root.quit,
                 bg='#cc0000', fg='white', font=('Arial', 10, 'bold'), padx=10, pady=5).pack(side=tk.RIGHT, padx=2)
        
        # ===== Статус =====
        self.status_var = tk.StringVar(value='💡 Подсказка: Двойной клик на автомобиль откроет ссылку в браузере')
        status_label = tk.Label(self.root, textvariable=self.status_var, bg=self.bg_dark, 
                               fg='yellow', font=('Arial', 9, 'bold'))
        status_label.pack(fill=tk.X, padx=10, pady=2)
        
        # ===== Таблица =====
        table_frame = tk.Frame(self.root, bg=self.bg_dark)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview
        self.tree = ttk.Treeview(table_frame, height=25,
                                columns=('Rating', 'Make', 'Model', 'Trim', 'Year', 'Price', 'Volume', 'Location', 'Phone'),
                                show='headings', yscrollcommand=scrollbar.set)
        
        # Определяем колонки
        self.tree.heading('Rating', text='Рейтинг')
        self.tree.heading('Make', text='Марка')
        self.tree.heading('Model', text='Модель')
        self.tree.heading('Trim', text='Комплектация')
        self.tree.heading('Year', text='Год')
        self.tree.heading('Price', text='Цена ($)')
        self.tree.heading('Volume', text='Объем (см³)')
        self.tree.heading('Location', text='Локация')
        self.tree.heading('Phone', text='Телефон')
        
        self.tree.column('Rating', width=70, anchor=tk.CENTER)
        self.tree.column('Make', width=120, anchor=tk.W)
        self.tree.column('Model', width=80, anchor=tk.CENTER)
        self.tree.column('Trim', width=180, anchor=tk.W)
        self.tree.column('Year', width=60, anchor=tk.CENTER)
        self.tree.column('Price', width=90, anchor=tk.E)
        self.tree.column('Volume', width=80, anchor=tk.CENTER)
        self.tree.column('Location', width=100, anchor=tk.CENTER)
        self.tree.column('Phone', width=120, anchor=tk.W)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)
        
        # Обработчик двойного клика для открытия ссылки
        self.tree.bind('<Double-Button-1>', lambda e: self.open_link())
        
        # Стиль
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', background=self.bg_light, foreground=self.text_color,
                       fieldbackground=self.bg_light, rowheight=25)
        style.configure('Treeview.Heading', background=self.accent_color, foreground='white')
        style.map('Treeview', background=[('selected', '#0066cc')])
        
    def load_data(self):
        """Загружает данные из JSON файла"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    self.cars_data = json.load(f)
                self.apply_filters()
                self.status_var.set(f'✅ Загружено {len(self.cars_data)} машин | 💡 Двойной клик = открыть ссылку ({datetime.now().strftime("%H:%M:%S")})')
            except Exception as e:
                messagebox.showerror('Ошибка', f'Ошибка загрузки данных: {e}')
        else:
            self.status_var.set('⚠️ Файл cars_data.json не найден. Запустите парсер!')
    
    def apply_filters(self):
        """Применяет фильтры к данным"""
        self.filtered_cars = self.cars_data.copy()
        
        # Фильтр по модели
        model = self.model_var.get().lower()
        if model:
            self.filtered_cars = [c for c in self.filtered_cars 
                                 if model in c.get('model', '').lower()]
        
        # Фильтр по марке
        make = self.make_var.get().lower()
        if make:
            self.filtered_cars = [c for c in self.filtered_cars 
                                 if make in c.get('make_name', '').lower()]
        
        # Фильтр по цене
        try:
            price_min = float(self.price_min_var.get()) if self.price_min_var.get() else 0
            self.filtered_cars = [c for c in self.filtered_cars if c.get('price_usd', 0) >= price_min]
        except ValueError:
            pass
        
        try:
            price_max = float(self.price_max_var.get()) if self.price_max_var.get() else float('inf')
            self.filtered_cars = [c for c in self.filtered_cars if c.get('price_usd', 0) <= price_max]
        except ValueError:
            pass
        
        # Фильтр по году
        try:
            year_min = int(self.year_min_var.get()) if self.year_min_var.get() else 0
            self.filtered_cars = [c for c in self.filtered_cars if c.get('year', 0) >= year_min]
        except ValueError:
            pass
        
        try:
            year_max = int(self.year_max_var.get()) if self.year_max_var.get() else 9999
            self.filtered_cars = [c for c in self.filtered_cars if c.get('year', 0) <= year_max]
        except ValueError:
            pass
        
        # Фильтр по рейтингу
        try:
            rating_min = float(self.rating_var.get())
            self.filtered_cars = [c for c in self.filtered_cars if c.get('rating', 0) >= rating_min]
        except ValueError:
            pass
        
        # Сортировка по рейтингу
        self.filtered_cars.sort(key=lambda x: x.get('rating', 0), reverse=True)
        
        # Обновляем таблицу
        self.update_table()
    
    def update_table(self):
        """Обновляет таблицу с отфильтрованными данными"""
        # Очищаем таблицу
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Добавляем строки
        for idx, car in enumerate(self.filtered_cars):
            rating = f"{car.get('rating', 0):.1f}"
            make = car.get('make_name', 'N/A')[:20]
            model_id = car.get('model_id', '')
            model_name = car.get('model', '').strip()  # Название модели из словаря
            # Показываем название модели, если есть, иначе #ID
            model = model_name[:15] if model_name else (f"#{model_id}" if model_id else 'N/A')
            trim = car.get('trim', '')[:30]
            year = car.get('year', 'N/A')
            price = f"${car.get('price_usd', 0):,}"
            volume = car.get('engine_volume', 0)
            location = car.get('location', 'N/A')
            phone = car.get('phone', 'N/A')[:10]
            
            # Цвет в зависимости от рейтинга
            rating_val = float(rating)
            if rating_val >= 80:
                tag = 'excellent'
            elif rating_val >= 70:
                tag = 'good'
            elif rating_val >= 60:
                tag = 'normal'
            else:
                tag = ''
            
            self.tree.insert('', 'end', values=(rating, make, model, trim, year, price, volume, location, phone), tags=(tag,))
        
        # Конфигурация тегов
        self.tree.tag_configure('excellent', foreground='#00FF00')
        self.tree.tag_configure('good', foreground='#FFFF00')
        self.tree.tag_configure('normal', foreground='#FFFFFF')
        
        self.status_var.set(f'🔍 Найдено {len(self.filtered_cars)} из {len(self.cars_data)} машин')
    
    def refresh_parser(self):
        """Запускает парсер в отдельном потоке"""
        if self.parsing_thread and self.parsing_thread.is_alive():
            messagebox.showwarning('Внимание', 'Парсер уже запущен!')
            return
        
        def run_parser():
            self.status_var.set('⏳ Парсер работает... (1-2 минуты)')
            self.root.update()
            try:
                result = subprocess.run(
                    [sys.executable, 'parser.py'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                self.load_data()
                self.status_var.set('✅ Парсер завершен!')
            except Exception as e:
                self.status_var.set(f'❌ Ошибка: {e}')
        
        self.parsing_thread = threading.Thread(target=run_parser, daemon=True)
        self.parsing_thread.start()
    
    def open_link(self):
        """Открывает ссылку выбранной машины в браузере"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning('Внимание', 'Выберите машину из таблицы!')
            return
        
        item = selection[0]
        index = self.tree.index(item)
        
        if index < len(self.filtered_cars):
            from telegram_bot import generate_listing_url
            import webbrowser
            
            car = self.filtered_cars[index]
            url = generate_listing_url(car)
            
            # Открываем в браузере
            webbrowser.open(url)
            
            make = car.get('make_name', 'N/A')
            model = car.get('model', 'N/A')[:20]
            self.status_var.set(f'🔗 Открыта ссылка: {make} {model}')
    
    def copy_link(self):
        """Копирует ссылку выбранной машины в буфер обмена"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning('Внимание', 'Выберите машину из таблицы!')
            return
        
        item = selection[0]
        index = self.tree.index(item)
        
        if index < len(self.filtered_cars):
            from telegram_bot import generate_listing_url
            car = self.filtered_cars[index]
            url = generate_listing_url(car)
            
            # Копируем в буфер обмена
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.root.update()
            
            self.status_var.set(f'✅ Ссылка скопирована!')


def main():
    root = tk.Tk()
    app = CarMonitorApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()

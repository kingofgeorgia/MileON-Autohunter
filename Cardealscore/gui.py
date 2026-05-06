#!/usr/bin/env python3
"""
Графический интерфейс для мониторинга автомобилей на myauto.ge
"""
import PySimpleGUI as sg
import json
import os
import threading
from datetime import datetime
import subprocess
import sys

# Настройки темы
sg.theme('DarkBlue3')
sg.set_options(font=('Arial', 11))

# ==================== КОНФИГУРАЦИЯ ====================
DATA_FILE = 'cars_data.json'
HISTORY_FILE = 'cars_history.json'
# ======================================================

class CarDashboard:
    def __init__(self):
        self.cars_data = self.load_data()
        self.filtered_cars = self.cars_data.copy()
        self.filters = {
            'model': '',
            'price_min': '',
            'price_max': '',
            'year_min': '',
            'year_max': '',
            'rating_min': 0
        }
        
    def load_data(self):
        """Загружает данные из JSON файла"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                sg.popup_error(f'Ошибка загрузки данных: {e}')
                return []
        return []
    
    def refresh_data(self):
        """Перезагружает данные из файла"""
        self.cars_data = self.load_data()
        self.apply_filters()
    
    def apply_filters(self):
        """Применяет фильтры к данным"""
        self.filtered_cars = self.cars_data.copy()
        
        # Фильтр по модели
        if self.filters['model']:
            model_lower = self.filters['model'].lower()
            self.filtered_cars = [c for c in self.filtered_cars 
                                 if model_lower in c.get('model', '').lower()]
        
        # Фильтр по цене
        if self.filters['price_min']:
            try:
                min_price = float(self.filters['price_min'])
                self.filtered_cars = [c for c in self.filtered_cars 
                                     if c.get('price_usd', 0) >= min_price]
            except ValueError:
                pass
        
        if self.filters['price_max']:
            try:
                max_price = float(self.filters['price_max'])
                self.filtered_cars = [c for c in self.filtered_cars 
                                     if c.get('price_usd', 0) <= max_price]
            except ValueError:
                pass
        
        # Фильтр по году
        if self.filters['year_min']:
            try:
                min_year = int(self.filters['year_min'])
                self.filtered_cars = [c for c in self.filtered_cars 
                                     if c.get('year', 0) >= min_year]
            except ValueError:
                pass
        
        if self.filters['year_max']:
            try:
                max_year = int(self.filters['year_max'])
                self.filtered_cars = [c for c in self.filtered_cars 
                                     if c.get('year', 0) <= max_year]
            except ValueError:
                pass
        
        # Фильтр по рейтингу
        rating_min = self.filters['rating_min']
        if rating_min > 0:
            self.filtered_cars = [c for c in self.filtered_cars 
                                 if c.get('rating', 0) >= rating_min]
        
        # Сортировка по рейтингу (по убыванию)
        self.filtered_cars.sort(key=lambda x: x.get('rating', 0), reverse=True)
    
    def get_table_data(self):
        """Возвращает данные для таблицы"""
        rows = []
        for car in self.filtered_cars:
            rows.append([
                f"{car.get('rating', 0):.1f}",
                car.get('model', 'N/A')[:30],
                car.get('year', 'N/A'),
                f"${car.get('price_usd', 0)}",
                car.get('engine_volume', 0),
                car.get('location', 'N/A'),
                car.get('phone', 'N/A')[:15]
            ])
        return rows


def run_parser_thread():
    """Запускает парсер в отдельном потоке"""
    try:
        result = subprocess.run(
            [sys.executable, 'parser.py'],
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.returncode == 0
    except Exception as e:
        print(f'Ошибка при запуске парсера: {e}')
        return False


def create_window(dashboard):
    """Создает главное окно приложения"""
    
    # Колонки для таблицы
    headings = ['Рейтинг', 'Модель', 'Год', 'Цена', 'Объем', 'Локация', 'Телефон']
    
    # Блок с фильтрами
    filter_frame = [
        [
            sg.Text('🔍 ФИЛЬТРЫ', font=('Arial', 12, 'bold')),
        ],
        [
            sg.Text('Модель:', size=(10, 1)),
            sg.InputText(size=(15, 1), key='-MODEL-', change_submits=True),
            sg.Text('Рейтинг ≥:', size=(10, 1)),
            sg.Combo(['0', '50', '60', '70', '80'], default_value='0', size=(10, 1), 
                    key='-RATING-', change_submits=True, readonly=True),
        ],
        [
            sg.Text('Цена ($):', size=(10, 1)),
            sg.InputText(size=(10, 1), key='-PRICE_MIN-', change_submits=True),
            sg.Text('-', size=(2, 1), justification='center'),
            sg.InputText(size=(10, 1), key='-PRICE_MAX-', change_submits=True),
        ],
        [
            sg.Text('Год:', size=(10, 1)),
            sg.InputText(size=(10, 1), key='-YEAR_MIN-', change_submits=True),
            sg.Text('-', size=(2, 1), justification='center'),
            sg.InputText(size=(10, 1), key='-YEAR_MAX-', change_submits=True),
        ],
    ]
    
    # Блок с кнопками
    button_frame = [
        [
            sg.Button('🔄 Обновить парсер', key='-REFRESH-', size=(20, 1), button_color=('white', '#0066cc')),
            sg.Button('🔄 Перезагрузить данные', key='-RELOAD-', size=(20, 1), button_color=('white', '#00cc66')),
            sg.Button('📋 Копировать ссылку', key='-COPY-', size=(15, 1)),
            sg.Button('❌ Выход', key='-EXIT-', size=(10, 1), button_color=('white', '#cc0000')),
        ],
        [
            sg.Text(f'Всего машин: {len(dashboard.cars_data)} | Найдено: {len(dashboard.filtered_cars)}', 
                   key='-STATUS-', font=('Arial', 10, 'bold'), text_color='yellow'),
        ],
    ]
    
    # Основная таблица
    table_frame = [
        [
            sg.Table(
                values=dashboard.get_table_data(),
                headings=headings,
                max_col_width=20,
                auto_size_columns=False,
                col_widths=[8, 25, 6, 12, 8, 12, 15],
                num_rows=20,
                key='-TABLE-',
                enable_events=True,
                vertical_scroll_only=False,
                select_mode=sg.TABLE_SELECT_MODE_BROWSE
            )
        ]
    ]
    
    # Главный лейаут
    layout = [
        [sg.Text('🚗 ПАНЕЛЬ МОНИТОРИНГА АВТОМОБИЛЕЙ (myauto.ge)', font=('Arial', 14, 'bold'), text_color='#00FFFF')],
        [sg.Column(filter_frame, background_color='#1e1e1e')],
        [sg.Column(button_frame, background_color='#1e1e1e')],
        [sg.Column(table_frame, size=(1000, 400), background_color='#1e1e1e', vertical_alignment='top')],
        [sg.Text('', size=(50, 1), key='-INFO-', font=('Arial', 9))]
    ]
    
    window = sg.Window(
        '🚗 Car Market Monitor',
        layout,
        size=(1100, 700),
        resizable=True,
        finalize=True
    )
    
    return window


def main():
    """Главная функция приложения"""
    dashboard = CarDashboard()
    window = create_window(dashboard)
    
    parsing_thread = None
    
    while True:
        event, values = window.read(timeout=100)
        
        if event == sg.WINDOW_CLOSED or event == '-EXIT-':
            break
        
        # Применение фильтров
        if event in ['-MODEL-', '-PRICE_MIN-', '-PRICE_MAX-', '-YEAR_MIN-', '-YEAR_MAX-', '-RATING-']:
            dashboard.filters['model'] = values['-MODEL-']
            dashboard.filters['price_min'] = values['-PRICE_MIN-']
            dashboard.filters['price_max'] = values['-PRICE_MAX-']
            dashboard.filters['year_min'] = values['-YEAR_MIN-']
            dashboard.filters['year_max'] = values['-YEAR_MAX-']
            dashboard.filters['rating_min'] = int(values['-RATING-'])
            
            dashboard.apply_filters()
            window['-TABLE-'].update(values=dashboard.get_table_data())
            window['-STATUS-'].update(
                f'Всего машин: {len(dashboard.cars_data)} | Найдено: {len(dashboard.filtered_cars)}'
            )
        
        # Обновление парсера (запуск в отдельном потоке)
        if event == '-REFRESH-':
            if parsing_thread is None or not parsing_thread.is_alive():
                window['-INFO-'].update('⏳ Запуск парсера... (это может занять 1-2 минуты)')
                window.refresh()
                
                parsing_thread = threading.Thread(
                    target=lambda: window.write_event_value('-PARSER_DONE-', None),
                    daemon=True
                )
                
                # Реально запускаем парсер
                def run_parser_and_signal():
                    result = run_parser_thread()
                    window.write_event_value('-PARSER_DONE-', result)
                
                parser_thread = threading.Thread(target=run_parser_and_signal, daemon=True)
                parser_thread.start()
            else:
                sg.popup_warning('Парсер уже запущен!')
        
        # Парсер завершился
        if event == '-PARSER_DONE-':
            dashboard.refresh_data()
            window['-TABLE-'].update(values=dashboard.get_table_data())
            window['-STATUS-'].update(
                f'Всего машин: {len(dashboard.cars_data)} | Найдено: {len(dashboard.filtered_cars)}'
            )
            window['-INFO-'].update(f'✅ Парсер завершен! Обновлено {len(dashboard.cars_data)} машин. ({datetime.now().strftime("%H:%M:%S")})')
        
        # Перезагрузка данных
        if event == '-RELOAD-':
            dashboard.refresh_data()
            window['-TABLE-'].update(values=dashboard.get_table_data())
            window['-STATUS-'].update(
                f'Всего машин: {len(dashboard.cars_data)} | Найдено: {len(dashboard.filtered_cars)}'
            )
            window['-INFO-'].update(f'✅ Данные перезагружены! ({datetime.now().strftime("%H:%M:%S")})')
        
        # Копирование ссылки выбранной машины
        if event == '-COPY-':
            selected = values['-TABLE-']
            if selected:
                row_idx = selected[0]
                if row_idx < len(dashboard.filtered_cars):
                    from telegram_bot import generate_listing_url
                    car = dashboard.filtered_cars[row_idx]
                    url = generate_listing_url(car)
                    
                    # Копируем в буфер обмена (Windows)
                    import tkinter as tk
                    root = tk.Tk()
                    root.withdraw()
                    root.clipboard_clear()
                    root.clipboard_append(url)
                    root.update()
                    root.destroy()
                    
                    window['-INFO-'].update(f'✅ Ссылка скопирована: {url}')
            else:
                sg.popup_warning('Выберите машину из таблицы!')
    
    window.close()


if __name__ == '__main__':
    main()

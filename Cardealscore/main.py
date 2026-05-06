#!/usr/bin/env python3
"""Главный файл приложения - запускает единый GUI."""
import sys


def main() -> None:
    """Главная функция - запускает единый GUI."""
    print("=" * 70)
    print("🚗 Запуск приложения мониторинга автомобилей")
    print("=" * 70)

    try:
        from mileon_saas.gui.main import main as gui_main
        gui_main()
    except Exception as exc:
        print(f"❌ Ошибка при запуске GUI: {exc}")
        sys.exit(1)


if __name__ == '__main__':
    # Исправляем кодировку для Windows PowerShell
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    main()

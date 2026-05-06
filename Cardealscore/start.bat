@echo off
REM Запуск приложения мониторинга автомобилей

echo.
echo ====================================
echo  Car Market Monitor
echo ====================================
echo.

REM Запускаем API в отдельном окне
cd /d "%~dp0"
set PYTHON_EXE=%~dp0.venv\Scripts\python.exe

start "MileON API" "%PYTHON_EXE%" -m uvicorn mileon_saas.api.main:app --reload

REM Запускаем парсер в отдельном окне, чтобы GUI не блокировался
start "MileON Parser" "%PYTHON_EXE%" parser.py

REM Запускаем GUI сразу
"%PYTHON_EXE%" -m mileon_saas.gui.main

pause

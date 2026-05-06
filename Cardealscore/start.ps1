# Запуск приложения Car Market Monitor

Write-Host "" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "🚗 Car Market Monitor" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "" -ForegroundColor Green

# Запускаем API в отдельном окне
$pythonExe = ".\.venv\Scripts\python.exe"
Start-Process -FilePath $pythonExe -ArgumentList "-m uvicorn mileon_saas.api.main:app --reload" -WindowStyle Normal

# Запускаем парсер в отдельном окне, чтобы GUI не блокировался
Start-Process -FilePath $pythonExe -ArgumentList "parser.py" -WindowStyle Normal

# Запускаем GUI сразу
& $pythonExe -m mileon_saas.gui.main

pause

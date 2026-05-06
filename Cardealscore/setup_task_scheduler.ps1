# Настройка автоматического ежедневного мониторинга myauto.ge
# Запускать с правами администратора: 
#   powershell -ExecutionPolicy Bypass -File setup_task_scheduler.ps1

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  НАСТРОЙКА АВТОМАТИЧЕСКОГО МОНИТОРИНГА MYAUTO.GE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Пути
$projectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $projectPath ".venv\Scripts\python.exe"
$scriptPath = Join-Path $projectPath "daily_tracking.py"
$logPath = Join-Path $projectPath "tracking.log"

# Проверка существования файлов
if (-not (Test-Path $pythonPath)) {
    Write-Host "❌ Ошибка: Python не найден в .venv" -ForegroundColor Red
    Write-Host "   Путь: $pythonPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Решение: Убедитесь, что виртуальное окружение создано:" -ForegroundColor Yellow
    Write-Host "   python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $scriptPath)) {
    Write-Host "❌ Ошибка: Скрипт daily_tracking.py не найден" -ForegroundColor Red
    Write-Host "   Путь: $scriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Файлы найдены:" -ForegroundColor Green
Write-Host "   Python: $pythonPath" -ForegroundColor Gray
Write-Host "   Скрипт: $scriptPath" -ForegroundColor Gray
Write-Host ""

# Запросить время запуска
$defaultTime = "02:00"
$time = Read-Host "Время ежедневного запуска (по умолчанию: $defaultTime)"
if ([string]::IsNullOrWhiteSpace($time)) {
    $time = $defaultTime
}

Write-Host ""
Write-Host "⏰ Задача будет запускаться каждый день в $time" -ForegroundColor Yellow
Write-Host ""

# Подтверждение
$confirm = Read-Host "Создать задачу? (y/n)"
if ($confirm -ne 'y' -and $confirm -ne 'Y') {
    Write-Host "❌ Отменено" -ForegroundColor Red
    exit 0
}

Write-Host ""
Write-Host "📝 Создание задачи в Task Scheduler..." -ForegroundColor Cyan

try {
    # Удалить существующую задачу (если есть)
    $existingTask = Get-ScheduledTask -TaskName "MyAutoTracking" -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "   ⚠️  Удаление существующей задачи..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName "MyAutoTracking" -Confirm:$false
    }
    
    # Создать действие
    $action = New-ScheduledTaskAction `
        -Execute $pythonPath `
        -Argument "`"$scriptPath`" --quiet" `
        -WorkingDirectory $projectPath
    
    # Создать триггер (ежедневно в указанное время)
    $trigger = New-ScheduledTaskTrigger -Daily -At $time
    
    # Настройки задачи
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable
    
    # Зарегистрировать задачу
    Register-ScheduledTask `
        -TaskName "MyAutoTracking" `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Description "Ежедневный мониторинг myauto.ge для ML модели" `
        -RunLevel Highest | Out-Null
    
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "✅ ЗАДАЧА УСПЕШНО СОЗДАНА" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Детали задачи:" -ForegroundColor Cyan
    Write-Host "   Название: MyAutoTracking" -ForegroundColor Gray
    Write-Host "   Расписание: Каждый день в $time" -ForegroundColor Gray
    Write-Host "   Команда: $pythonPath" -ForegroundColor Gray
    Write-Host "   Аргументы: `"$scriptPath`" --quiet" -ForegroundColor Gray
    Write-Host ""
    Write-Host "🔧 Управление задачей:" -ForegroundColor Cyan
    Write-Host "   Открыть Task Scheduler:" -ForegroundColor Yellow
    Write-Host "      taskschd.msc" -ForegroundColor White
    Write-Host ""
    Write-Host "   Запустить вручную:" -ForegroundColor Yellow
    Write-Host "      Start-ScheduledTask -TaskName 'MyAutoTracking'" -ForegroundColor White
    Write-Host ""
    Write-Host "   Проверить статус:" -ForegroundColor Yellow
    Write-Host "      Get-ScheduledTask -TaskName 'MyAutoTracking' | Get-ScheduledTaskInfo" -ForegroundColor White
    Write-Host ""
    Write-Host "   Удалить задачу:" -ForegroundColor Yellow
    Write-Host "      Unregister-ScheduledTask -TaskName 'MyAutoTracking' -Confirm:`$false" -ForegroundColor White
    Write-Host ""
    Write-Host "📊 Логи будут сохраняться в:" -ForegroundColor Cyan
    Write-Host "   $logPath" -ForegroundColor Gray
    Write-Host ""
    
    # Предложить тестовый запуск
    Write-Host "🧪 Хотите запустить задачу сейчас для проверки? (y/n)" -ForegroundColor Yellow
    $testRun = Read-Host
    
    if ($testRun -eq 'y' -or $testRun -eq 'Y') {
        Write-Host ""
        Write-Host "▶️  Запуск задачи..." -ForegroundColor Cyan
        Start-ScheduledTask -TaskName "MyAutoTracking"
        Start-Sleep -Seconds 2
        
        $taskInfo = Get-ScheduledTask -TaskName "MyAutoTracking" | Get-ScheduledTaskInfo
        Write-Host "   Статус: $($taskInfo.LastTaskResult)" -ForegroundColor Gray
        Write-Host "   Последний запуск: $($taskInfo.LastRunTime)" -ForegroundColor Gray
        Write-Host ""
        Write-Host "✅ Задача запущена! Проверьте логи через несколько секунд." -ForegroundColor Green
    }
    
} catch {
    Write-Host ""
    Write-Host "❌ ОШИБКА: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "💡 Решения:" -ForegroundColor Yellow
    Write-Host "   1. Запустите PowerShell с правами администратора" -ForegroundColor Gray
    Write-Host "   2. Убедитесь, что Task Scheduler включен" -ForegroundColor Gray
    Write-Host "   3. Проверьте пути к файлам" -ForegroundColor Gray
    exit 1
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Нажмите Enter для выхода..." -ForegroundColor Gray
Read-Host

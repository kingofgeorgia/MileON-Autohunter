# MileON Autohunter

MileON Autohunter — monorepo для набора инструментов вокруг поиска, оценки и расчёта импорта автомобилей с myauto.ge. В проекте собраны парсеры, Telegram-боты, веб-калькулятор, сервисы расчёта таможенных платежей и вспомогательные справочники.

## Что внутри

| Папка | Назначение |
|---|---|
| `Cardealscore/` | Мониторинг рынка myauto.ge, парсинг объявлений, скоринг выгодных предложений, Telegram-уведомления и локальный SaaS/API слой. |
| `georgiancarbenefits/` | Основное веб-приложение: FastAPI backend, Next.js frontend, PostgreSQL, расчёт стоимости покупки/импорта авто из Грузии в РФ. |
| `myauto_moscow_bot/` | Telegram-бот, который принимает ссылку или ID объявления myauto.ge и считает ориентировочную стоимость авто до Москвы. |
| `tks-api-main/` | Python-библиотека/модуль для расчёта таможенных платежей и утилизационного сбора. |
| `MILEON_AUTOHUNTER_WORK_PLAN.md` | Рабочий план развития проекта и заметки по архитектуре. |

## Основные возможности

- поиск и импорт объявлений с myauto.ge;
- расчёт полной стоимости автомобиля с учётом валюты, логистики, таможни и утильсбора;
- каталог авто с фильтрами и предварительным расчётом выгоды;
- история расчётов для авторизованных пользователей;
- Telegram-уведомления о новых интересных предложениях;
- отдельный Telegram-бот для быстрого расчёта по ссылке;
- справочники марок, моделей, характеристик и вспомогательные ML/аналитические скрипты.

## Быстрый старт

Клонировать репозиторий:

```bash
git clone https://github.com/kingofgeorgia/MileON-Autohunter.git
cd MileON-Autohunter
```

### Веб-приложение Georgian Car Benefits

Самый простой вариант запуска — через Docker:

```bash
cd georgiancarbenefits
cp .env.example .env
docker-compose up --build
```

После запуска:

| URL | Описание |
|---|---|
| `http://localhost:3000` | Frontend-приложение |
| `http://localhost:8000/docs` | Swagger-документация backend API |
| `http://localhost:8000/redoc` | ReDoc-документация backend API |

Применить миграции базы данных:

```bash
docker-compose exec backend alembic upgrade head
```

### Cardealscore

```bash
cd Cardealscore
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Для фонового запуска парсера:

```bash
python main.py
```

### Telegram-бот myauto до Москвы

```bash
cd myauto_moscow_bot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python bot.py
```

Перед запуском нужно заполнить `.env` токеном Telegram-бота.

### TKS API

```bash
cd tks-api-main
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest tests
```

## Стек

| Часть | Технологии |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy, Alembic |
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| База данных | PostgreSQL, SQLite для локальных сценариев |
| Боты | aiogram, Telethon |
| Интеграции | myauto.ge API, Telegram, внешние курсы валют |
| Инфраструктура | Docker, docker-compose |

## Конфигурация

В репозиторий добавлены только примеры конфигурации. Локальные секреты и окружения не коммитятся.

Основные файлы:

- `georgiancarbenefits/.env.example` — переменные для веб-приложения;
- `myauto_moscow_bot/.env.example` — переменные Telegram-бота;
- `myauto_moscow_bot/config.yaml` — бизнес-настройки расходов, маршрута и расчётов;
- `Cardealscore/ui_settings.json` — локальные настройки интерфейса.

## Что не хранится в Git

Корневой `.gitignore` исключает локальные и тяжёлые артефакты:

- `node_modules/`;
- `.venv/`, `venv/`, `env/`;
- `.next/`, `dist/`, `build/`;
- локальные базы `*.db`, `*.sqlite`, `*.sqlite3`;
- `backups/`;
- `.env` и `.env.local`.

Если нужны локальные базы или бэкапы, их нужно хранить отдельно от GitHub либо подключить Git LFS/внешнее хранилище.

## Полезные команды

```bash
# Проверить состояние репозитория
git status

# Обновить локальную копию
git pull

# Запушить изменения
git push

# Посмотреть последние коммиты
git log --oneline -5
```

## Статус

Проект находится в активной разработке. Сейчас это объединённый рабочий репозиторий для нескольких связанных модулей MileON Autohunter, поэтому перед изменениями в конкретном подпроекте лучше читать его локальный README и профильные документы в соответствующей папке.

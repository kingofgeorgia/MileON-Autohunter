# 🇬🇪 Georgian Car Benefits

Веб-приложение для расчёта и сравнения стоимости покупки автомобиля из Грузии с доставкой в Россию.

**Что делает приложение:**
- Считает таможенные пошлины РФ (по объёму двигателя, году выпуска, стоимости авто)
- Считает утилизационный сбор
- Переводит цены из USD / EUR / GEL в рубли по актуальному курсу
- Учитывает стоимость логистики Грузия → РФ
- Сравнивает итоговую стоимость с ценой аналогичного авто в РФ
- Показывает каталог авто с myauto.ge с фильтрами по марке/модели и предварительным расчётом для каждого
- Сохраняет историю расчётов для авторизованных пользователей

В backend также добавлена отдельная production-ready функция точного расчёта для сценария `физлицо / личное пользование`: `calculatePersonalImportCustoms(...)` в `backend/app/services/personal_import_customs.py`. Она считает по схеме `таможенный сбор + единая ставка + утилизационный сбор`, без НДС и акциза, и теперь автоматически определяет коэффициент утильсбора по таблицам 2026 с учётом возраста, объёма двигателя, мощности и типа силовой установки. Для объявлений myauto по ссылке поддерживается fallback-lookup мощности и типа силовой установки через внешний JSON-справочник `backend/app/data/vehicle_specs.json`, если данные объявления неполные.

Калькулятор теперь сохраняет в базе параметры, нужные для точного расчёта: обязательный `horse_power`, автоматически вычисленный `util_coefficient`, `powertrain_kind` и признак `is_personal_use`. Если расчёт был сделан для импортированного объявления myauto, введённая пользователем мощность дополнительно запоминается по связке `make + model + model_id` и затем подставляется из базы при следующем импорте такого же автомобиля. После импорта объявления myauto UI автоматически подставляет тип топлива и тип силовой установки из данных объявления. Для `Электромобиль` поле мощности во фронтенде отображается в `кВт`, а поле объёма двигателя отключается как неиспользуемое; перед отправкой в backend мощность автоматически конвертируется обратно в `л.с.`, а `engine_volume_cc` передаётся как `0`, что теперь поддерживается точным backend-расчётом для EV. Стандартная логистика во фронтенде теперь определяется по классу объявления: `200000 ₽` для внедорожников и кроссоверов (`category_id` myauto `5` и `66`), `170000 ₽` для остальных классов. Для поля `Цена аналога в РФ` временно добавлена кнопка, открывающая готовый path-based поиск на auto.ru по марке, модели и дополнительным фильтрам загруженного автомобиля.

Форма калькулятора теперь также нормализует пустые optional-поля (`Цена аналога в РФ`, `Заметка`) и показывает явную ошибку валидации вместо «тихого» игнорирования submit, если обязательные поля не заполнены.

---

## Стек технологий

| Слой | Технология |
|---|---|
| Backend | Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic |
| База данных | PostgreSQL 16 |
| Frontend | Next.js 16 + TypeScript + Tailwind CSS + shadcn/ui |
| Авторизация | JWT (python-jose) + bcrypt |
| i18n | next-intl — Русский / English / ქართული |
| Курсы валют | open.er-api.com (кэш 1 ч, без API-ключа) |
| Каталог авто | myauto.ge публичный API + справочники марок и моделей |
| Контейнеры | Docker + docker-compose |

---

## Быстрый старт (Docker)

### Требования
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### Запуск

```bash
git clone https://github.com/kingofgeorgia/georgiancarbenefits.git
cd georgiancarbenefits

# Скопировать конфиг
cp .env.example .env

# Запустить все сервисы
docker-compose up --build
```

### Применить миграции БД (первый запуск — в отдельном терминале)

```bash
docker-compose exec backend alembic revision --autogenerate -m "init"
docker-compose exec backend alembic upgrade head
```

### Открыть в браузере

| URL | Описание |
|---|---|
| http://localhost:3000 | Приложение |
| http://localhost:8000/docs | API документация (Swagger) |
| http://localhost:8000/redoc | API документация (ReDoc) |

---

## Структура проекта

```
georgiancarbenefits/
├── backend/
│   ├── app/
│   │   ├── api/          # Роутеры: auth, calculator, cars, history
│   │   ├── core/         # config, db, security (JWT)
│   │   ├── models/       # SQLAlchemy: User, Calculation
│   │   ├── schemas/      # Pydantic схемы
│   │   └── services/     # customs, recycling, currency, myauto
│   ├── alembic/          # Миграции БД
│   └── requirements.txt
├── frontend/
│   ├── messages/         # Переводы: ru.json, en.json, ka.json
│   └── src/
│       ├── app/[locale]/ # Next.js App Router с i18n
│       ├── components/   # Calculator, Auth, CarCatalog, History, Navbar
│       ├── i18n/         # next-intl конфигурация
│       └── lib/          # API клиент, типы, утилиты
├── docker-compose.yml
└── .env.example
```

---

## API эндпоинты

### Auth
| Метод | URL | Описание |
|---|---|---|
| POST | `/auth/register` | Регистрация |
| POST | `/auth/login` | Вход, возвращает JWT |
| GET | `/auth/me` | Текущий пользователь |

### Калькулятор
| Метод | URL | Описание |
|---|---|---|
| POST | `/calculator/total` | Полный расчёт стоимости ввоза |
| GET | `/calculator/rates` | Актуальные курсы валют |

Отдельно от API-роута доступен backend helper `calculatePersonalImportCustoms(...)` для детерминированного расчёта личного ввоза. `POST /calculator/total` и сохранение в историю теперь требуют `horse_power` и используют точный путь расчёта: коэффициент утильсбора определяется по таблицам, а `kW` автоматически пересчитываются из `horse_power`. Если расчёт пришёл из импортированного myauto-объявления, backend запоминает введённую мощность и связывает её с `source_make`, `source_model` и `source_model_id`. Внутренние manual override-пути для коэффициента и `kW` из helper удалены. JSON-справочник можно пополнять без правки Python-кода.

Во фронтенде блок результатов калькулятора дополнительно показывает суммарную строку `Общая растаможка` перед `Итого к оплате`: это сумма таможенного сбора, таможенной пошлины и утилизационного сбора.

### Каталог авто
| Метод | URL | Описание |
|---|---|---|
| GET | `/cars/search` | Поиск авто на myauto.ge с расчётом |
| GET | `/cars/makes` | Публичный список марок |
| GET | `/cars/models?make_id=3` | Публичный список моделей по марке |
| POST | `/cars/from-url` | Загрузить данные авто по ссылке myauto.ge |

`CarListing` в ответах каталога и загрузки по ссылке теперь содержит и каноничную `model`, и исходные поля `model_id` / `car_model` из объявления myauto, а также `image_urls`, `fuel_type` и `powertrain_kind` для автозаполнения калькулятора. Для `POST /cars/from-url` источник мощности теперь приоритетно определяется так: `listing hp` → запомненная мощность из БД → локальный JSON-справочник спецификаций. Фронтенд использует эти данные и в калькуляторе, и в карточках каталога: можно листать фото и открывать полноэкранный просмотр по клику.

### История
| Метод | URL | Описание |
|---|---|---|
| POST | `/history/` | Сохранить расчёт |
| GET | `/history/` | Список расчётов пользователя |
| DELETE | `/history/{id}` | Удалить расчёт |

---

## Переменные окружения (.env)

```env
POSTGRES_USER=gcb_user
POSTGRES_PASSWORD=gcb_password
POSTGRES_DB=gcb_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

SECRET_KEY=your_secret_key_min_32_chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

FRONTEND_ORIGIN=http://localhost:3000

EXCHANGE_API_URL=https://open.er-api.com/v6/latest/USD
EXCHANGE_CACHE_TTL_SECONDS=3600
```

---

## Разработка без Docker

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Запустить (нужен запущенный PostgreSQL)
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

В dev-режиме frontend очищает `.next` перед запуском `next dev`, чтобы stale Turbopack cache не вызывал ложные `404` на локализованных маршрутах вроде `/ru`.

---

## Полезные команды

```bash
# Остановить контейнеры
docker-compose down

# Остановить и удалить данные БД
docker-compose down -v

# Логи конкретного сервиса
docker-compose logs -f backend
docker-compose logs -f frontend

# Пересобрать после изменений
docker-compose up --build
```

# MileON Autohunter: план объединения проектов

## 1. Цель проекта

**MileON Autohunter** - единый SaaS для поиска, расчета и отбора выгодных автомобилей с грузинского рынка, в первую очередь myauto.ge, для покупателей, брокеров, перекупов и небольших импортных команд.

Продукт должен отвечать на три главных вопроса:

1. Сколько реально будет стоить автомобиль "под ключ" после покупки, логистики, таможни и оформления.
2. Насколько объявление выгодно относительно рынка, риска, ликвидности и ожидаемой маржи.
3. Какие автомобили нужно брать в работу прямо сейчас, а какие лучше пропустить.

## 2. Что берем из текущих 4 проектов

### 2.1. `georgiancarbenefits`

Использовать как основной каркас нового SaaS.

Что переносим в ядро:

- FastAPI backend.
- PostgreSQL + SQLAlchemy + Alembic.
- JWT auth.
- Next.js frontend.
- Docker Compose.
- Каталог myauto.ge.
- Калькулятор стоимости ввоза.
- Историю расчетов.
- i18n: RU / EN / KA.
- Точный расчет личного ввоза из `personal_import_customs.py`.

### 2.2. `Cardealscore`

Использовать как источник B2B-логики отбора сделок.

Что переносим:

- `Company`, `BrandPolicy`, `TechnicalBlacklist`, `MarketStats`, `ClosedDeal`.
- `decision_engine.py`.
- `scoring.py`.
- `risk.py`.
- `pricing.py`.
- `decision.py`.
- TOP-5 Telegram alerts.
- Ингест объявлений и дедупликацию по `source_listing_id`.
- Логику ROI, expected sell price, hold days, buy/skip/watch decisions.

### 2.3. `myauto_moscow_bot`

Использовать как UX-прототип Telegram-канала.

Что переносим:

- Сценарий "пользователь отправляет ID или ссылку myauto.ge".
- Быстрый ответ с полной стоимостью до Москвы.
- Конфигурируемые расходы: логистика, брокер, СБКТС, ЭПТС, терминал, прочее.
- Форматирование Telegram-ответа.

Важно: формулы из бота не должны жить отдельно. Telegram должен вызывать общий backend-сервис расчета.

### 2.4. `tks-api-main`

Использовать как справочный и частично расчетный модуль.

Что переносим осторожно:

- Структуру ETC / CTP расчетов.
- Поддержку юрлиц, НДС, акциза.
- Тестовые сценарии.

Что не делаем:

- Не заменяем полностью текущий `personal_import_customs.py`, потому что в `georgiancarbenefits` уже есть более свежая логика личного ввоза 2026 с учетом мощности, EV и hybrid.

## 3. Целевая архитектура

### 3.1. Рекомендуемый тип репозитория

Новый проект лучше вести как монорепозиторий:

```text
MileON Autohunter/
  apps/
    backend/
      app/
        main.py
        api/
        core/
        domains/
        integrations/
        jobs/
        models/
        schemas/
        services/
        tests/
      alembic/
      Dockerfile
    frontend/
      src/
      messages/
      Dockerfile
  packages/
    customs_engine/
    myauto_client/
    scoring_engine/
  docs/
  docker-compose.yml
  README.md
```

На первом этапе можно не выносить `packages/` физически. Но логически эти границы нужны сразу.

### 3.2. Backend-модули

```text
backend/app/
  api/
    auth.py
    companies.py
    cars.py
    calculator.py
    deals.py
    alerts.py
    history.py
    admin.py

  domains/
    auth/
    companies/
    vehicles/
    calculations/
    customs/
    scoring/
    risks/
    alerts/
    market/

  integrations/
    myauto/
    telegram/
    currency/
    auto_ru/

  jobs/
    parse_myauto.py
    refresh_market_stats.py
    recalculate_scores.py
    send_alerts.py
    cleanup_old_data.py

  core/
    config.py
    db.py
    security.py
    permissions.py
    logging.py
```

Главный принцип: API-роуты должны быть тонкими. Бизнес-логика живет в сервисах и domain-модулях.

### 3.3. Frontend-модули

```text
frontend/src/
  app/[locale]/
    page.tsx
    catalog/page.tsx
    deals/page.tsx
    calculator/page.tsx
    history/page.tsx
    settings/page.tsx
    admin/page.tsx

  components/
    cars/
    calculator/
    deals/
    history/
    layout/
    settings/
    ui/

  lib/
    api.ts
    types.ts
    auth.ts
    money.ts
```

Главные экраны MVP:

- Каталог.
- Лучшие сделки.
- Калькулятор.
- История расчетов.
- Настройки компании.
- Telegram-подписки.

### 3.4. База данных

Минимальная целевая схема:

```text
companies
users
user_company_memberships
telegram_subscriptions

vehicle_listings
vehicle_listing_snapshots
vehicle_price_history
vehicle_images

calculations
calculation_cost_items

market_stats
brand_policies
technical_blacklist
closed_deals

deal_scores
listing_actions

tariff_versions
tariff_rules
logistics_profiles
exchange_rates_cache
```

Критичные ограничения:

- `vehicle_listings(source, source_listing_id)` должен быть уникальным.
- Все пользовательские данные должны иметь `company_id`.
- Все запросы SaaS должны фильтроваться по компании текущего пользователя.
- Расчеты должны сохранять snapshot тарифов и курсов, чтобы история не менялась задним числом.

### 3.5. Поток данных

```text
myauto.ge API
  -> myauto_client
  -> normalize vehicle listing
  -> upsert vehicle_listings
  -> save price snapshot
  -> calculate import cost
  -> calculate deal score
  -> rank deals
  -> show in web UI
  -> send Telegram alerts
```

### 3.6. Один источник правды для расчетов

В новом проекте должен быть один расчетный слой:

```text
customs_engine
  calculate_personal_import()
  calculate_company_import()
  calculate_recycling_fee()
  calculate_customs_fee()
  calculate_unified_rate()
  calculate_excise()
  calculate_vat()
  calculate_total_landed_cost()
```

Нельзя оставлять отдельные формулы в web, bot и scripts. Все каналы должны вызывать один и тот же сервис.

## 4. Полный план работ

### Этап 0. Продуктовая фиксация

Цель: зафиксировать границы MVP.

Работы:

- Утвердить название: **MileON Autohunter**.
- Описать целевых пользователей: частный покупатель, брокер, перекуп, команда импорта.
- Зафиксировать главный MVP-сценарий: найти авто -> посчитать полную стоимость -> оценить сделку -> отправить в работу.
- Определить валюты MVP: USD, EUR, GEL, RUB.
- Определить географию MVP: Грузия -> РФ, маршрут до Москвы как дефолтный профиль.
- Зафиксировать роли: `owner`, `admin`, `buyer`, `viewer`.

Результат:

- Product brief.
- MVP backlog.
- Список платных фич.

### Этап 1. Создание нового репозитория/каркаса

Цель: сделать чистую основу проекта.

Работы:

- Взять `georgiancarbenefits` как основу.
- Переименовать продукт, env-переменные, README, title API и UI.
- Обновить docker-compose names.
- Убрать старые артефакты, `.env`, session-файлы, generated JSON из будущего репозитория.
- Настроить `.gitignore`.
- Добавить `docs/architecture.md`, `docs/roadmap.md`, `docs/security.md`.
- Настроить базовый CI: lint backend, tests backend, build frontend.

Результат:

- Чистый проект `MileON Autohunter`.
- Запуск через Docker.
- Зеленый healthcheck backend/frontend.

### Этап 2. Multi-tenant SaaS ядро

Цель: сделать проект настоящим SaaS, а не одиночным калькулятором.

Работы:

- Добавить `Company`.
- Добавить связь пользователя с компанией.
- Добавить роли и permissions.
- Все записи `calculations`, `brand_policies`, `blacklists`, `subscriptions`, `closed_deals` привязать к `company_id`.
- Запретить передачу произвольного `company_id` в публичных query-параметрах.
- Все `company_id` брать из текущего пользователя.
- Добавить seed/demo company только для dev.

Результат:

- Пользователь видит только данные своей компании.
- API защищен на уровне dependency/service layer.

### Этап 3. Единая модель автомобиля

Цель: объединить разные `CarListing` из проектов.

Работы:

- Создать каноническую модель `VehicleListing`.
- Сохранить поля myauto: `source`, `source_listing_id`, `make`, `model`, `model_id`, `year`, `price`, `currency`, `engine_cc`, `horse_power`, `fuel_type`, `powertrain_kind`, `mileage_km`, `vin`, `category_id`, `location`, `dealer_id`, `images`, `url`.
- Добавить `VehicleListingSnapshot` для истории цены и доступности.
- Добавить `source_payload` JSONB для сырых данных, которые пока не нормализованы.
- Сделать миграции Alembic.
- Добавить уникальные индексы и upsert.

Результат:

- Один автомобильный справочник.
- Без дубликатов объявлений.
- Можно строить историю цен.

### Этап 4. MyAuto integration

Цель: сделать надежный клиент myauto.ge.

Работы:

- Вынести `myauto.py` в отдельный integration module.
- Сделать typed DTO для raw и normalized listing.
- Добавить retry, timeout, rate limit, user-agent/impersonation config.
- Добавить cache для марок/моделей.
- Добавить endpoint поиска.
- Добавить background job для регулярного парсинга.
- Добавить import by URL / ID.
- Добавить tests на normalizer.

Результат:

- Веб-каталог и бот используют один myauto-client.
- Объявления сохраняются и обновляются идемпотентно.

### Этап 5. Единый customs/cost engine

Цель: убрать дублирование финансовых расчетов.

Работы:

- Вынести `personal_import_customs.py` в домен `customs`.
- Перенести полезные ETC/CTP сценарии из `tks-api-main`.
- Создать единый метод `calculate_landed_cost`.
- Разделить calculation на cost items:
  - car price;
  - customs fee;
  - unified rate / duty;
  - recycling fee;
  - excise;
  - VAT;
  - logistics;
  - broker;
  - SBKTS/EPTS;
  - terminal;
  - other costs.
- Ввести versioned tariffs.
- Сохранять snapshot тарифной версии в каждом расчете.
- Добавить golden tests для контрольных кейсов.

Результат:

- Web, API и Telegram показывают одинаковый расчет.
- Тарифы можно обновлять управляемо.

### Этап 6. Deal scoring engine

Цель: добавить оценку выгодности и риска.

Работы:

- Перенести `scoring.py`, `pricing.py`, `risk.py`, `decision.py`, `decision_engine.py`.
- Переписать под каноническую модель `VehicleListing`.
- Сохранить score в таблицу `deal_scores`, а не считать тяжелые значения каждый раз.
- Добавить параметры компании:
  - minimum ROI;
  - target hold days;
  - brand whitelist/blacklist;
  - liquidity multiplier;
  - max purchase price;
  - risk tolerance.
- Добавить risk flags:
  - missing VIN;
  - suspicious low mileage;
  - USA import with damage;
  - structural damage;
  - technical blacklist;
  - price anomaly.
- Добавить decision: `buy`, `watch`, `skip`, `blocked`.

Результат:

- Страница "Лучшие сделки".
- Ранжирование по `buy_score`, `roi_percent`, `risk_score`.

### Этап 7. Market stats

Цель: дать scoring engine рыночную базу.

Работы:

- Рассчитывать median/q1/q3 по марке, модели, году, двигателю, пробегу.
- Исключать объявления без цены и невалидные записи.
- Обновлять stats по расписанию.
- Добавить fallback, если данных мало.
- Сохранять дату расчета market stats.

Результат:

- Deal score сравнивает авто не с пустотой, а с реальным рынком.

### Этап 8. Telegram как SaaS-канал

Цель: объединить Telegram-бот и alerts.

Работы:

- Переписать `myauto_moscow_bot` в backend integration.
- Сделать webhook endpoint.
- Команды:
  - `/start`;
  - `/help`;
  - отправка URL/ID myauto;
  - подписка на TOP deals;
  - отписка;
  - выбор компании, если пользователь состоит в нескольких.
- Inline actions:
  - `TAKEN`;
  - `WATCHING`;
  - `SKIP`;
  - `OPEN`;
  - `CALCULATE`.
- Все действия писать в `listing_actions`.

Результат:

- Telegram становится не отдельным ботом, а полноценным интерфейсом SaaS.

### Этап 9. Frontend MVP

Цель: дать удобный рабочий интерфейс.

Работы:

- Обновить branding на MileON Autohunter.
- Сделать dashboard:
  - лучшие сделки;
  - новые объявления;
  - последние расчеты;
  - Telegram status.
- Улучшить каталог:
  - filters;
  - sorting by score;
  - cost preview;
  - image gallery;
  - badges risk/ROI.
- Добавить страницу deal details.
- Добавить settings:
  - logistics profiles;
  - ROI thresholds;
  - brand policies;
  - technical blacklist;
  - Telegram subscriptions.

Результат:

- Пользователь может работать в продукте без прямого доступа к API.

### Этап 10. Админка и настройки тарифов

Цель: сделать эксплуатацию без правки кода.

Работы:

- Добавить admin-only раздел.
- Управление тарифными версиями.
- Управление логистическими профилями.
- Импорт/экспорт blacklist.
- Ручной запуск jobs.
- Просмотр ошибок интеграций.

Результат:

- Обновления тарифов и расходов управляются из UI или защищенного admin API.

### Этап 11. Безопасность

Цель: закрыть SaaS-риски до продакшена.

Работы:

- Удалить `.env`, session-файлы и токены из репозитория.
- Проверить git history на секреты.
- Ротировать все токены, которые могли быть в репозитории.
- Запретить дефолтный `SECRET_KEY=change_me` в production.
- Включить CORS только для нужных доменов.
- Добавить rate limit на auth, Telegram webhook, myauto URL import.
- Добавить audit log для важных действий.
- Добавить dependency-level permission checks.

Результат:

- Проект можно безопасно выкладывать в private/prod repo.

### Этап 12. Тесты и качество

Цель: стабилизировать расчеты и бизнес-логику.

Работы:

- Unit tests:
  - customs;
  - recycling;
  - scoring;
  - risk;
  - pricing;
  - myauto normalizer.
- API tests:
  - auth;
  - tenant isolation;
  - calculator;
  - cars;
  - deals.
- Frontend smoke tests.
- Golden tests для финансовых расчетов.
- mypy/pyright или строгая типизация на критичных модулях.
- ESLint/TypeScript strict на frontend.

Результат:

- Основные баги ловятся до релиза.

### Этап 13. Production deployment

Цель: подготовить SaaS к запуску.

Работы:

- Разделить env: dev/staging/prod.
- Настроить PostgreSQL managed или отдельный контейнер.
- Настроить migrations на deploy.
- Настроить backup БД.
- Настроить logs и error tracking.
- Настроить metrics:
  - API latency;
  - myauto failures;
  - parser job duration;
  - alerts sent;
  - calculation errors.
- Настроить домен и HTTPS.

Результат:

- Staging и production окружения.

## 5. Критические проблемы и план исправления

### Проблема 1. Нет единого источника правды для финансовых расчетов

Где видно:

- `georgiancarbenefits/backend/app/services/personal_import_customs.py`
- `georgiancarbenefits/backend/app/services/customs.py`
- `georgiancarbenefits/backend/app/services/recycling.py`
- `myauto_moscow_bot/bot.py`
- `tks-api-main/tks_api_official/calc.py`

Риск:

- Web, Telegram и backend могут показывать разные итоговые суммы.
- Тарифы 2025/2026 могут расходиться.
- Бизнес теряет доверие пользователей, если расчет "под ключ" плавает между каналами.

Нарушения:

- DRY: формулы дублируются.
- SRP: Telegram-бот одновременно парсит, считает, форматирует и хранит тарифы.
- DIP: UI/бот завязаны на конкретные формулы вместо доменного сервиса.

План исправления:

1. Создать домен `customs` / `costing`.
2. Сделать публичный сервис `calculate_landed_cost(input)`.
3. Разложить результат на typed cost items.
4. Вынести тарифы в versioned config/table.
5. Все каналы перевести на этот сервис: web, API, Telegram, batch scoring.
6. Добавить golden tests на 15-20 контрольных кейсов.
7. Запретить новые финансовые формулы вне `customs` domain.

### Проблема 2. Секреты, auth и tenant isolation сейчас недостаточны для SaaS

Где видно:

- `georgiancarbenefits/backend/app/core/config.py`: `secret_key = "change_me"`.
- В проектах есть `.env` файлы и Telegram `.session` файлы.
- В `Cardealscore` API принимает `company_id` из query и не имеет полноценной auth-модели.
- В `georgiancarbenefits` пользователь пока не привязан к компании.

Риск:

- Компрометация JWT при дефолтном секрете.
- Утечка Telegram/API credentials.
- Пользователь одной компании сможет запросить или изменить данные другой.
- Нельзя безопасно запускать B2B SaaS.

Нарушения:

- Отсутствует явная boundary model для tenant данных.
- Access control размазан или отсутствует.

План исправления:

1. Удалить `.env`, `.session`, локальные токены из будущего репозитория.
2. Проверить git history и ротировать все найденные секреты.
3. В production падать при `SECRET_KEY=change_me`.
4. Добавить `Company` и `UserCompanyMembership`.
5. Во всех protected endpoint брать `company_id` только из current user context.
6. Добавить permission dependency: `require_role(...)`, `get_current_company(...)`.
7. Написать API tests на запрет cross-company доступа.
8. Добавить rate limiting на auth и Telegram webhook.

### Проблема 3. Разные модели данных конфликтуют друг с другом

Где видно:

- `Cardealscore/mileon_saas/models.py` содержит B2B `CarListing` с company/scoring полями.
- `georgiancarbenefits/backend/app/schemas/cars.py` и `myauto.py` работают с другим представлением listing.
- История расчетов хранит часть параметров, но нет единой связи с сохраненным объявлением и snapshots.
- `Cardealscore` использует SQLite async, `georgiancarbenefits` - PostgreSQL sync SQLAlchemy.

Риск:

- Потеря данных при миграции.
- Дубликаты объявлений.
- Невозможность надежно считать market stats.
- Сложный frontend, потому что разные endpoints возвращают разные формы одного автомобиля.

Нарушения:

- SRP и ISP: модели пытаются быть одновременно raw listing, normalized listing, calculation input и scoring target.
- Нет явного anti-corruption layer между myauto API и доменной моделью.

План исправления:

1. Спроектировать каноническую модель `VehicleListing`.
2. Добавить `VehicleListingSnapshot` и `VehiclePriceHistory`.
3. Сырые данные хранить в `source_payload`, но не строить бизнес-логику напрямую на raw JSON.
4. Создать normalizer `myauto_raw -> VehicleListingUpsert`.
5. Ввести уникальный индекс `(source, source_listing_id)`.
6. Перенести scoring на каноническую модель.
7. Перевести все новые модули на PostgreSQL + Alembic.
8. Сохранить миграционные scripts для старых JSON/SQLite данных.

### Проблема 4. Ingestion и внешние интеграции небезопасны и плохо изолированы

Где видно:

- `Cardealscore/mileon_saas/api/routes/listings.py` endpoint `/listings/ingest` принимает `path`.
- `Cardealscore/mileon_saas/services/ingestion.py` читает файл через `Path(path)`.
- MyAuto-запросы выполняются прямо в API request path.
- Нет очереди, job status, retry policy, idempotency report.

Риск:

- Path-based ingest может привести к чтению неожиданных файлов на сервере.
- Долгие запросы к myauto.ge будут тормозить пользовательский API.
- При падении внешнего API пользователь получает пустой результат без понятной причины.
- Массовый парсинг может заблокировать backend.

Нарушения:

- SRP: API endpoint одновременно является командой запуска batch job.
- DIP: бизнес-логика зависит от конкретной файловой системы и текущей рабочей директории.

План исправления:

1. Удалить произвольный `path` из public/admin API.
2. Разрешить ingest только из заранее настроенного storage/import directory или object storage.
3. Перенести парсинг в background jobs.
4. Добавить таблицу `import_jobs` со статусом, ошибками, счетчиками.
5. Добавить retry/backoff для MyAuto.
6. Добавить timeout/circuit breaker/cache.
7. API должен запускать job и возвращать `job_id`, а не выполнять весь import синхронно.
8. Добавить audit log для ручных импортов.

### Проблема 5. Есть runtime-баги, слабая типизация и мало проверок вокруг критичной логики

Где видно:

- `Cardealscore/mileon_saas/api/routes/listings.py`: `evaluate_listing()` возвращает `ListingScores`, но код использует `scores.get(...)`. У Pydantic-модели нет такого dict API, endpoint TOP-5 может падать.
- ML-код частично закомментирован и оставляет неоднозначные ветки.
- Telegram форматирование и расчетная логика живут большими файлами.
- Тесты есть только частично и не покрывают интеграцию всех расчетов.

Риск:

- TOP-5 Telegram alert ломается в runtime.
- Финансовые регрессии не ловятся автоматически.
- Любое изменение scoring или тарифов может незаметно испортить расчеты.
- Команда будет бояться менять ядро продукта.

Нарушения:

- SRP: крупные модули делают слишком много.
- OCP: добавление нового сценария расчета требует правки существующих больших функций.
- LSP/typing: функции ожидают dict-like объекты, но получают Pydantic-модели.

План исправления:

1. Исправить `scores.get(...)` на доступ к атрибутам или `scores.model_dump()`.
2. Ввести строгие DTO для scoring summary.
3. Разбить Telegram-бот на modules: input parsing, listing fetch, calculation, formatting, delivery.
4. Добавить unit tests на `send_top5_telegram`.
5. Добавить type checks для backend critical modules.
6. Включить CI: pytest, ruff/flake8, frontend build.
7. Сделать regression suite для customs + scoring.
8. Удалить или изолировать недоделанный ML-код за feature flag.

## 6. MVP backlog

### Must-have

- Auth + companies + roles.
- MyAuto catalog.
- Import by URL/ID.
- Full landed cost calculation.
- Calculation history.
- Deal score.
- Best deals page.
- Telegram calculation by URL.
- Telegram TOP-5 alerts.
- Company settings: ROI, logistics, brand policies.
- Technical blacklist.
- Basic admin tariff config.

### Should-have

- Price history.
- Market stats refresh job.
- Auto.ru analog search helper.
- Export deals to CSV/XLSX.
- Saved searches.
- Alerts for price drops.
- Multiple logistics profiles.

### Later

- ML expected price.
- CRM pipeline for purchased cars.
- Payments/subscriptions.
- Dealer accounts.
- Browser extension.
- Mobile app.

## 7. Рекомендуемый порядок реализации

1. Сделать чистый `MileON Autohunter` repo на базе `georgiancarbenefits`.
2. Закрыть security baseline: secrets, auth, company model.
3. Объединить модель автомобиля.
4. Вынести единый customs/cost engine.
5. Перенести deal scoring из `Cardealscore`.
6. Добавить best deals UI.
7. Интегрировать Telegram как канал backend.
8. Добавить background jobs.
9. Добавить tests/CI.
10. Подготовить staging/prod.

## 8. Definition of Done для первого релиза

Первый релиз считается готовым, если:

- Пользователь регистрируется и попадает в компанию.
- Пользователь ищет авто на myauto.ge из web UI.
- Пользователь открывает карточку авто и видит полную стоимость ввоза.
- Пользователь видит `buy/watch/skip` решение и причину.
- История расчетов сохраняется.
- TOP-5 выгодных авто уходят в Telegram.
- Нельзя получить данные чужой компании.
- Все финансовые расчеты идут через один сервис.
- Есть тесты на ключевые расчетные сценарии.
- Проект запускается через Docker Compose.


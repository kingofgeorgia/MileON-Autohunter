# Manual Reference

## Navbar Auth Rendering

Module: `frontend/src/components/layout/Navbar.tsx`

Behavior:
- Keeps the locale switcher and navigation links SSR-safe in `Navbar.tsx`.
- Loads the auth-dependent controls from `NavbarAuthControls.tsx` with `ssr: false`, because the token source is `localStorage` and exists only in the browser.
- Updates the local auth flag immediately on logout before redirecting to the locale-specific login page.

## Locale Layout

Module: `frontend/src/app/[locale]/layout.tsx`

Behavior:
- Registers supported locales through `generateStaticParams()` for the App Router locale segment.
- Resolves invalid locale params to the configured default locale instead of triggering a false 404 for valid localized routes.
- Calls `setRequestLocale(...)` and `getMessages({locale})` explicitly so `next-intl` has a stable locale context for `/ru`, `/en`, and `/ka` pages.

## Frontend Dev Startup

Files:
- `frontend/package.json`
- `frontend/Dockerfile`

Behavior:
- The frontend `dev` script clears `.next` before starting `next dev`.
- This prevents stale Turbopack route cache in Docker from causing recurring false `404` responses on localized routes such as `/ru` and `/ru/login`.

## Exchange Rates Provider

Module: `backend/app/services/currency.py`

Behavior:
- Uses `open.er-api.com/v6/latest/USD` as the primary free exchange-rates source.
- Reads the endpoint from `EXCHANGE_API_URL` and caches the parsed RUB/EUR/GEL rates in memory for `EXCHANGE_CACHE_TTL_SECONDS`.
- Validates that the provider returned `result=success` and includes `RUB`, `EUR`, and `GEL` before updating cache.
- Logs the exact fallback failure as an exception before returning static reserve rates.
- Falls back to conservative static rates only when the remote provider is unavailable or returns an invalid payload.

## Personal Import Customs Helper

Module: `backend/app/services/personal_import_customs.py`

Behavior:
- Contains `calculatePersonalImportCustoms(input)` and `round2(value)`.
- Implements the deterministic formula for `physical person + personal use + passenger car`.
- Uses only `customs fee + unified rate + utilization fee`.
- Does not add VAT, excise, or commercial legal-entity logic.
- Automatically resolves `utilCoefficient` from the 2026 personal-use tables using `horsePower`, `engineCc`, `ageYears`, and `powertrainKind`.
- The helper no longer supports manual override for utilization coefficient or kW input; hp→kW conversion is always automatic.
- Includes a runnable example for the Lexus LX 600 case discussed during this session.

## Saved Power Inputs

Database / API behavior:
- `calculations` now stores `horse_power`, the computed `util_coefficient`, `powertrain_kind`, and `is_personal_use` alongside the existing calculation inputs.
- Calculator form now requires horsepower, shows the detected fuel type, and auto-fills powertrain kind from imported myauto listing data.
- When `powertrain_kind=EV`, the calculator UI switches the visible power field from hp to kW and converts the user-entered value back to hp before calling backend APIs.
- When `powertrain_kind=EV`, the engine-volume input is disabled on the frontend and `engine_volume_cc=0` is sent intentionally.
- Backend calculation always derives the utilization coefficient and kW value automatically from the available vehicle data.
- The backend personal-import helper now allows `engineCc=0` for `EV` and `SERIES_HYBRID`, while ICE-based paths still require a positive engine volume.
- When a calculation is submitted for an imported myauto listing, backend also remembers the entered horsepower in `learned_vehicle_powers` using `source_make`, `source_model`, and `source_model_id`.
- History API returns the saved horsepower input back to the frontend.

## Default Logistics

Frontend / API behavior:
- Calculator default logistics is now `170000` rubles before a listing is loaded.
- When an imported myauto listing has `category_id` `5` or `66`, calculator automatically switches logistics to `200000` rubles.
- Other imported classes use the standard `170000` rubles logistics default.
- Catalog search default logistics was also raised to `170000` rubles.

## RF Analog Price

Frontend behavior:
- The calculator still accepts manual input in `rf_analog_price_rub`.
- As a temporary replacement for automatic auto.ru parsing, the calculator now shows a button near the RF analog price field.
- That button opens a prepared auto.ru `used/sale/<make>/<model>/` search in a new tab using the loaded car's make, model, year, horsepower, and engine volume.
- Empty optional calculator fields are normalized to `null`, and invalid submits now show an explicit validation toast instead of failing silently.

## Calculator Results Summary

Module: `frontend/src/components/calculator/CalculatorResults.tsx`

Behavior:
- Shows a separate `totalCustoms` row before the final total.
- `totalCustoms` is computed on the client as `customs_fee_rub + customs_duty_rub + recycling_fee_rub`.
- `total_cost_rub` remains unchanged and still adds car price, customs-related charges, and logistics.

## Horsepower Fallback Lookup

Modules:
- `backend/app/services/vehicle_specs.py`
- `backend/app/data/vehicle_specs.json`
- `backend/app/services/myauto.py`

Behavior:
- `myauto.parse_car()` now exposes `horse_power`, `horse_power_source`, `fuel_type`, `powertrain_kind`, and `util_coefficient` in `CarListing`.
- Source priority is: raw listing `hp` field first, then learned horsepower from database, then local spec catalog fallback.
- The fallback catalog is now stored in external JSON and supports matching by ids plus make/model aliases.
- The current seeded catalog includes discussed models from this session: Lexus LX 600, Mercedes-Benz GLE 450, Tesla Model X 75D, and BMW M4 Competition xDrive.
- If `horse_power` is available, calculator and catalog estimates switch to the precise personal-use import formula and compute `util_coefficient` automatically.
- Fuel type is normalized from `fuel_type_id`, and powertrain kind is inferred from spec catalog when available or from the raw listing for obvious EV cases.
- `curl_cffi.requests` is loaded via runtime import in `myauto.py`, which keeps the container behavior unchanged while removing the unresolved-import warning in local analysis.

## Car Models Directory

Endpoint: `GET /cars/models?make_id=<man_id>`

Behavior:
- Returns normalized model options for the selected make from myauto `vehicle/models`.
- Public endpoint, intended for catalog filters without login.
- Uses backend caching per `make_id` to avoid repeated reference lookups.

## Car Makes Directory

Endpoint: `GET /cars/makes`

Behavior:
- Public endpoint for frontend catalog make select.
- Returns myauto make directory as-is from backend integration.

## Catalog Filters UI

Frontend catalog now uses dependent selects:
- Make select loads options from `/cars/makes`.
- Model select loads options from `/cars/models?make_id=<man_id>`.
- Changing make resets the currently selected model.
- Car cards display raw `make`, `model_id`, `car_model`, and the canonical `model` separately.
- Primary car title in UI is formatted as `make + model + car_model + year` when `car_model` differs from canonical `model`.
- Secondary metadata line was removed from UI; only the formatted primary title remains visible.
- Catalog cards now render the same photo carousel as calculator import preview.
- Clicking a catalog or calculator image opens a fullscreen viewer with arrows, thumbnails, and `Esc` close support.

## Car URL Import (Calculator)

Endpoint: `POST /cars/from-url`

Request body:
```json
{
  "url": "https://myauto.ge/ka/pr/<car_id>/..."
}
```

Behavior:
- Accepts public myauto links in `/pr/<id>` format.
- Trims spaces around pasted URLs before parsing.
- Returns normalized `CarListing` data used by calculator autofill.
- Reuses remembered horsepower from the database for the same `make` / `model` / `model_id` when the current listing has no raw horsepower value.
- Resolves model names from myauto `vehicle/models` reference using `man_id` and `model_id`, preferring the canonical directory value over ad-level `car_model` text.
- Also returns raw `model_id` and `car_model` from the original myauto listing for client-side analysis.
- Also returns `image_urls`, built from myauto `photo`, `pic_number`, and `photo_ver` fields.
- Calculator UI shows raw `make`, `model_id`, `car_model`, plus canonical `model` after link import.
- Calculator UI uses the same primary title formatting as catalog cards.
- Calculator UI renders the shared listing carousel with fullscreen photo viewing after car data is loaded from URL.

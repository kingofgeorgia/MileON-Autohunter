import time

import httpx

from mileon_saas.config import settings


def wait_for_api(timeout_seconds: int = 30) -> bool:
    deadline = time.time() + timeout_seconds
    url = f"{settings.api_base_url}/health"

    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=3.0)
            if response.status_code == 200:
                return True
        except httpx.HTTPError:
            time.sleep(1.0)

    return False


def ingest_latest() -> None:
    url = f"{settings.api_base_url}/api/listings/ingest"
    params = {
        "path": "cars_data.json",
        "company_id": settings.default_company_id,
    }
    response = httpx.post(url, params=params, timeout=15.0)
    response.raise_for_status()


def main() -> None:
    if not wait_for_api():
        raise SystemExit("API did not start in time")
    ingest_latest()


if __name__ == "__main__":
    main()

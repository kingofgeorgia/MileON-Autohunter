"""MyAuto API integration module.

Provides structured access to all MyAuto API endpoints for vehicles, 
manufacturers, models, categories, colors, locations, and other filters.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any

import cloudscraper
from fake_useragent import UserAgent


class VehicleType(IntEnum):
    """Vehicle types on MyAuto."""
    CAR = 0
    SPEC = 1
    MOTO = 2


@dataclass
class Manufacturer:
    """Vehicle manufacturer from API."""
    man_id: int
    title: str
    vehicle_types: list[int]
    
    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Manufacturer:
        return cls(
            man_id=data["man_id"],
            title=data["title"],
            vehicle_types=data.get("vehicle_types", []),
        )


@dataclass
class Model:
    """Vehicle model from API."""
    model_id: int
    title: str
    
    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Model:
        return cls(
            model_id=data["model_id"],
            title=data["title"],
        )


@dataclass
class Category:
    """Vehicle category from API."""
    category_id: int
    title: str
    vehicle_types: list[int]
    
    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Category:
        return cls(
            category_id=data["category_id"],
            title=data["title"],
            vehicle_types=data.get("vehicle_types", []),
        )


@dataclass
class FuelType:
    """Fuel type from API."""
    fuel_type_id: int
    title: str
    
    @classmethod
    def from_api(cls, data: dict[str, Any]) -> FuelType:
        return cls(
            fuel_type_id=data["fuel_type_id"],
            title=data["title"],
        )


@dataclass
class Color:
    """Color from API."""
    color_id: int
    title: str
    
    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Color:
        return cls(
            color_id=data["color_id"],
            title=data["title"],
        )


@dataclass
class Location:
    """Location from API."""
    location_id: int
    title: str
    
    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Location:
        return cls(
            location_id=data["location_id"],
            title=data["title"],
        )


@dataclass
class GearType:
    """Gear type from API."""
    gear_type_id: int
    title: str
    
    @classmethod
    def from_api(cls, data: dict[str, Any]) -> GearType:
        return cls(
            gear_type_id=data["gear_type_id"],
            title=data["title"],
        )


@dataclass
class DriveType:
    """Drive type from API."""
    drive_type_id: int
    title: str
    
    @classmethod
    def from_api(cls, data: dict[str, Any]) -> DriveType:
        return cls(
            drive_type_id=data["drive_type_id"],
            title=data["title"],
        )


class MyAutoAPI:
    """MyAuto API client for vehicle data."""
    
    def __init__(
        self,
        base_url: str = "https://api2.myauto.ge",
        language: str = "ka",
        timeout: int = 30,
    ):
        """Initialize API client.
        
        Args:
            base_url: API base URL
            language: Language code (ka, en)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.language = language
        self.timeout = timeout
        
        # Setup cloudscraper with headers
        self.scraper = cloudscraper.create_scraper()
        ua = UserAgent()
        self.scraper.headers.update({
            'User-Agent': ua.random,
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.myauto.ge/',
            'Origin': 'https://www.myauto.ge'
        })
    
    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """Make GET request to API."""
        url = f"{self.base_url}/{self.language}/{endpoint}"
        response = self.scraper.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
    
    def get_vehicle_types(self) -> list[dict[str, Any]]:
        """Fetch vehicle types."""
        return self._get("vehicle/types")
    
    def get_manufacturers(
        self,
        vehicle_types: list[VehicleType] | None = None,
    ) -> list[Manufacturer]:
        """Fetch manufacturers.
        
        Args:
            vehicle_types: Filter by vehicle types (None = all)
        """
        params = {}
        if vehicle_types:
            params["vehicle_types"] = ".".join(str(vt.value) for vt in vehicle_types)
        
        data = self._get("vehicle/mans", params)
        return [Manufacturer.from_api(item) for item in data]
    
    def get_models(
        self,
        man_id: int,
        vehicle_types: list[VehicleType] | None = None,
    ) -> list[Model]:
        """Fetch models for a manufacturer.
        
        Args:
            man_id: Manufacturer ID
            vehicle_types: Filter by vehicle types (None = all)
        """
        params = {"man_id": str(man_id)}
        if vehicle_types:
            params["vehicle_types"] = ".".join(str(vt.value) for vt in vehicle_types)
        
        data = self._get("vehicle/models", params)
        return [Model.from_api(item) for item in data]
    
    def get_categories(
        self,
        vehicle_types: list[VehicleType] | None = None,
    ) -> list[Category]:
        """Fetch categories.
        
        Args:
            vehicle_types: Filter by vehicle types (None = all)
        """
        params = {}
        if vehicle_types:
            params["vehicle_types"] = ".".join(str(vt.value) for vt in vehicle_types)
        
        data = self._get("vehicle/categories", params)
        return [Category.from_api(item) for item in data]
    
    def get_fuel_types(self) -> list[FuelType]:
        """Fetch fuel types."""
        data = self._get("vehicle/fuel-types")
        return [FuelType.from_api(item) for item in data]
    
    def get_colors(self) -> list[Color]:
        """Fetch colors."""
        data = self._get("vehicle/colors")
        return [Color.from_api(item) for item in data]
    
    def get_salon_colors(self) -> list[Color]:
        """Fetch salon (interior) colors."""
        data = self._get("vehicle/salon-colors")
        return [Color.from_api(item) for item in data]
    
    def get_locations(self) -> list[Location]:
        """Fetch locations."""
        data = self._get("vehicle/locations")
        return [Location.from_api(item) for item in data]
    
    def get_gear_types(self) -> list[GearType]:
        """Fetch gear types."""
        data = self._get("vehicle/gear-types")
        return [GearType.from_api(item) for item in data]
    
    def get_drive_types(
        self,
        vehicle_types: list[VehicleType] | None = None,
    ) -> list[DriveType]:
        """Fetch drive types.
        
        Args:
            vehicle_types: Filter by vehicle types (None = all)
        """
        params = {}
        if vehicle_types:
            params["vehicle_types"] = ".".join(str(vt.value) for vt in vehicle_types)
        
        data = self._get("vehicle/drive-types", params)
        return [DriveType.from_api(item) for item in data]
    
    def get_wheel_types(
        self,
        vehicle_types: list[VehicleType] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch wheel types.
        
        Args:
            vehicle_types: Filter by vehicle types (None = all)
        """
        params = {}
        if vehicle_types:
            params["vehicle_types"] = ".".join(str(vt.value) for vt in vehicle_types)
        
        return self._get("vehicle/wheel-types", params)


def main() -> int:
    """Example usage of MyAutoAPI."""
    api = MyAutoAPI()
    
    print("Fetching manufacturers...")
    manufacturers = api.get_manufacturers()
    print(f"Found {len(manufacturers)} manufacturers")
    print(f"Sample: {manufacturers[0]}")
    
    print("\nFetching models for BMW (man_id=3)...")
    models = api.get_models(man_id=3)
    print(f"Found {len(models)} models")
    if models:
        print(f"Sample: {models[0]}")
    
    # Try optional endpoints (may not be available)
    try:
        print("\nFetching categories...")
        categories = api.get_categories([VehicleType.CAR])
        print(f"Found {len(categories)} car categories")
        if categories:
            print(f"Sample: {categories[0]}")
    except Exception as e:
        print(f"Categories endpoint not available: {e}")
    
    try:
        print("\nFetching locations...")
        locations = api.get_locations()
        print(f"Found {len(locations)} locations")
        if locations:
            print(f"Sample: {locations[0]}")
    except Exception as e:
        print(f"Locations endpoint not available: {e}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import json
from pathlib import Path
from typing import TypedDict


class ServiceItem(TypedDict):
    id: str
    title: str
    duration_min: int
    price: int
    description: str


class CatalogService:
    def __init__(self, services_path: Path) -> None:
        self.services_path = services_path
        self._services = self._load_services()

    def _load_services(self) -> list[ServiceItem]:
        with self.services_path.open("r", encoding="utf-8") as file:
            raw_items = json.load(file)

        services: list[ServiceItem] = []
        for item in raw_items:
            services.append(
                ServiceItem(
                    id=str(item["id"]),
                    title=str(item["title"]),
                    duration_min=int(item["duration_min"]),
                    price=int(item["price"]),
                    description=str(item["description"]),
                )
            )
        return services

    def list_services(self) -> list[ServiceItem]:
        return list(self._services)

    def get_service(self, service_id: str) -> ServiceItem | None:
        for service in self._services:
            if service["id"] == service_id:
                return service
        return None

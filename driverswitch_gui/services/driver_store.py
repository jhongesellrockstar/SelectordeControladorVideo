from __future__ import annotations

from driverswitch_gui.services.driver_inventory import DriverInventoryService


class DriverStoreService:
    def __init__(self, inventory: DriverInventoryService) -> None:
        self.inventory = inventory

    def list_display_packages(self, active_inf: str = ""):
        return self.inventory.list_driver_store(active_inf=active_inf)

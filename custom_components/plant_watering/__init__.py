"""Plant Watering integration."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, PLATFORMS, STORE_VERSION


class PlantData:
    """Persist mutable watering data for one plant."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.store = Store(hass, STORE_VERSION, f"{DOMAIN}.{entry_id}")
        self.last_watered: datetime | None = None
        self.listeners: list[Callable[[], None]] = []

    async def async_load(self) -> None:
        data = await self.store.async_load() or {}
        value = data.get("last_watered")
        if value:
            try:
                self.last_watered = datetime.fromisoformat(value)
            except ValueError:
                self.last_watered = None

    async def async_set_last_watered(self, value: datetime) -> None:
        self.last_watered = value
        await self.store.async_save({"last_watered": value.isoformat()})
        for listener in self.listeners:
            listener()

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self.listeners.append(listener)

        def remove_listener() -> None:
            if listener in self.listeners:
                self.listeners.remove(listener)

        return remove_listener


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    plant = PlantData(hass, entry.entry_id)
    await plant.async_load()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = plant
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)

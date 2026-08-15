"""Plant Watering integration."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime as DateTime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store
from homeassistant.util import slugify

from .const import (
    CONF_PLANT_NAME,
    DOMAIN,
    PLATFORMS,
    SEASONS,
    SIGNAL_PLANTS_UPDATED,
    STORE_VERSION,
)

_LOGGER = logging.getLogger(__name__)

PLANT_ENTITY_KEYS: dict[str, tuple[str, ...]] = {
    "sensor": ("status", "current_interval", "current_water"),
    "number": tuple(
        f"{kind}_{season}"
        for season in SEASONS
        for kind in ("interval", "water")
    ),
    "datetime": ("last_watered",),
    "button": ("water_now",),
}

OVERVIEW_ENTITIES: tuple[tuple[str, str], ...] = (
    ("plant_watering_overview_status", "sensor.plant_watering_status"),
    ("plant_watering_plan", "sensor.plant_watering_plan"),
)


class PlantData:
    """Persist mutable watering data for one plant."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.store = Store(hass, STORE_VERSION, f"{DOMAIN}.{entry_id}")
        self.last_watered: DateTime | None = None
        self.listeners: list[Callable[[], None]] = []

    async def async_load(self) -> None:
        data = await self.store.async_load() or {}
        value = data.get("last_watered")
        if value:
            try:
                self.last_watered = DateTime.fromisoformat(value)
            except ValueError:
                self.last_watered = None

    async def async_set_last_watered(self, value: DateTime) -> None:
        self.last_watered = value
        await self.store.async_save({"last_watered": value.isoformat()})
        for listener in self.listeners:
            listener()
        async_dispatcher_send(self.hass, SIGNAL_PLANTS_UPDATED)

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self.listeners.append(listener)

        def remove_listener() -> None:
            if listener in self.listeners:
                self.listeners.remove(listener)

        return remove_listener


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entries and registered entity IDs."""
    if entry.version > 2:
        return False

    if entry.version == 1:
        registry = er.async_get(hass)
        config = {**entry.data, **entry.options}
        plant_slug = slugify(config[CONF_PLANT_NAME])

        for entity_domain, keys in PLANT_ENTITY_KEYS.items():
            for key in keys:
                _migrate_entity_id(
                    registry,
                    entity_domain,
                    f"{entry.entry_id}_{key}",
                    f"{entity_domain}.{plant_slug}_{key}",
                )

        for unique_id, desired_entity_id in OVERVIEW_ENTITIES:
            _migrate_entity_id(
                registry,
                "sensor",
                unique_id,
                desired_entity_id,
            )

        hass.config_entries.async_update_entry(entry, version=2)
        _LOGGER.info("Migrated %s to config entry version 2", entry.title)

    return True


def _migrate_entity_id(
    registry: er.EntityRegistry,
    entity_domain: str,
    unique_id: str,
    desired_entity_id: str,
) -> None:
    """Move one existing registry entity to its English technical ID."""
    current_entity_id = registry.async_get_entity_id(
        entity_domain, DOMAIN, unique_id
    )
    if current_entity_id is None or current_entity_id == desired_entity_id:
        return

    if registry.async_get(current_entity_id) is None:
        return

    conflicting_entry = registry.async_get(desired_entity_id)
    if conflicting_entry is not None:
        desired_object_id = desired_entity_id.split(".", 1)[1]
        available_entity_id = registry.async_get_available_entity_id(
            entity_domain, desired_object_id
        )
        _LOGGER.info(
            "Entity ID %s is occupied; migrating %s to %s instead",
            desired_entity_id,
            current_entity_id,
            available_entity_id,
        )
        desired_entity_id = available_entity_id

    registry.async_update_entity(
        current_entity_id, new_entity_id=desired_entity_id
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    plant = PlantData(hass, entry.entry_id)
    await plant.async_load()
    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data[entry.entry_id] = plant
    domain_data.setdefault("overview_owner", entry.entry_id)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_dispatcher_send(hass, SIGNAL_PLANTS_UPDATED)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
        async_dispatcher_send(hass, SIGNAL_PLANTS_UPDATED)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Move the overview sensors when their owning plant is deleted."""
    domain_data = hass.data.get(DOMAIN, {})
    if domain_data.get("overview_owner") != entry.entry_id:
        return

    replacements = [
        candidate
        for candidate in hass.config_entries.async_entries(DOMAIN)
        if candidate.entry_id != entry.entry_id
        and candidate.entry_id in domain_data
    ]
    if not replacements:
        domain_data.pop("overview_owner", None)
        return

    replacement = replacements[0]
    domain_data["overview_owner"] = replacement.entry_id
    await hass.config_entries.async_reload(replacement.entry_id)


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)

"""Shared Plant Watering entity helpers."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.util import dt as dt_util, slugify

from .const import (
    CONF_ICON,
    CONF_INTERVAL_PREFIX,
    CONF_PLANT_NAME,
    CONF_TEMPERATURE_ENTITY,
    CONF_WATER_PREFIX,
    DOMAIN,
    SEASON_NAMES,
)


def season_at(value: datetime) -> str:
    return {
        12: "winter",
        1: "winter",
        2: "winter",
        3: "spring",
        4: "spring",
        5: "spring",
        6: "summer",
        7: "summer",
        8: "summer",
        9: "autumn",
        10: "autumn",
        11: "autumn",
    }[value.month]


def watering_status(
    last_watered: datetime | None,
    interval_days: int,
    now: datetime,
) -> str:
    """Return the technical watering status for a plant."""
    if last_watered is None:
        return "unknown"

    next_watering = last_watered + timedelta(days=interval_days)
    remaining = next_watering - now
    if remaining.total_seconds() <= 0:
        watered_today = (
            dt_util.as_local(last_watered).date()
            == dt_util.as_local(now).date()
        )
        if interval_days == 0 and watered_today:
            return "due_again"
        return "due"
    if remaining <= timedelta(hours=24):
        return "tomorrow"
    return "ok"


class PlantEntity(Entity):
    _attr_has_entity_name = True
    entity_domain: str

    def __init__(self, entry: ConfigEntry, plant) -> None:
        self.entry = entry
        self.plant = plant
        self._attr_unique_id = f"{entry.entry_id}_{self.key}"
        self.entity_id = (
            f"{self.entity_domain}."
            f"{slugify(self.config[CONF_PLANT_NAME])}_{self.key}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=self.config[CONF_PLANT_NAME],
            manufacturer="Plant Watering",
            model="Plant",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.plant.add_listener(self.async_write_ha_state))

    @property
    def config(self) -> dict:
        return {**self.entry.data, **self.entry.options}

    @property
    def plant_icon(self) -> str:
        return self.config.get(CONF_ICON, "mdi:sprout")

    @property
    def current_season(self) -> str:
        return season_at(dt_util.now())

    @property
    def temperature(self) -> float | None:
        entity_id = self.config.get(CONF_TEMPERATURE_ENTITY)
        if not entity_id or not self.hass:
            return None
        try:
            return float(self.hass.states.get(entity_id).state)
        except (AttributeError, TypeError, ValueError):
            return None

    @property
    def heat_reduction(self) -> int:
        temp = self.temperature
        return 2 if temp is not None and temp >= 35 else 1 if temp is not None and temp >= 28 else 0

    @property
    def active_interval(self) -> int:
        base = int(self.config[f"{CONF_INTERVAL_PREFIX}{self.current_season}"])
        return max(0, base - self.heat_reduction)

    @property
    def active_water(self) -> int:
        return int(self.config[f"{CONF_WATER_PREFIX}{self.current_season}"])

    @property
    def next_watering(self) -> datetime | None:
        if self.plant.last_watered is None:
            return None
        return self.plant.last_watered + timedelta(days=self.active_interval)

    @property
    def status(self) -> str:
        return watering_status(
            self.plant.last_watered,
            self.active_interval,
            dt_util.now(),
        )

    @property
    def common_attributes(self) -> dict:
        return {
            "season": self.current_season,
            "season_name": SEASON_NAMES[self.current_season],
            "interval_days": self.active_interval,
            "water_ml": self.active_water,
            "temperature": self.temperature,
            "heat_reduction_days": self.heat_reduction,
            "last_watered": self.plant.last_watered.isoformat() if self.plant.last_watered else None,
            "next_watering": self.next_watering.isoformat() if self.next_watering else None,
        }

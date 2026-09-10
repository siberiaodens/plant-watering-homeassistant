"""Plant and integration-wide sensors for Plant Watering."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime, UnitOfVolume
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util, slugify

from .const import (
    CONF_ICON,
    CONF_INTERVAL_PREFIX,
    CONF_PLANT_NAME,
    CONF_TEMPERATURE_ENTITY,
    CONF_WATER_PREFIX,
    DOMAIN,
    SEASONS,
    SEASON_NAMES,
    SIGNAL_PLANTS_UPDATED,
    UPDATE_INTERVAL_MINUTES,
)
from .entity import PlantEntity, next_watering_at, season_at, watering_status

DUE_STATUSES = ("due", "due_again", "unknown")


async def async_setup_entry(hass, entry, async_add_entities):
    plant = hass.data[DOMAIN][entry.entry_id]
    entities = [
        PlantStatusSensor(entry, plant),
        CurrentIntervalSensor(entry, plant),
        CurrentWaterSensor(entry, plant),
    ]
    if hass.data[DOMAIN].get("overview_owner") == entry.entry_id:
        entities.extend([OverviewStatusSensor(), WateringPlanSensor()])
    async_add_entities(entities)

    @callback
    def _async_refresh_sensors(_now) -> None:
        """Refresh time-dependent state on the Home Assistant event loop."""
        for entity in entities:
            entity.async_write_ha_state()

    cancel = async_track_time_interval(
        hass,
        _async_refresh_sensors,
        timedelta(minutes=UPDATE_INTERVAL_MINUTES),
    )
    entry.async_on_unload(cancel)

    config = {**entry.data, **entry.options}
    temperature_entity = config.get(CONF_TEMPERATURE_ENTITY)
    if temperature_entity:
        @callback
        def _handle_temperature_change(_event) -> None:
            for entity in entities:
                entity.async_write_ha_state()
            async_dispatcher_send(hass, SIGNAL_PLANTS_UPDATED)

        cancel_temperature = async_track_state_change_event(
            hass,
            [temperature_entity],
            _handle_temperature_change,
        )
        entry.async_on_unload(cancel_temperature)


class PlantStatusSensor(PlantEntity, SensorEntity):
    entity_domain = "sensor"
    key = "status"
    _attr_translation_key = "status"
    _attr_icon = "mdi:watering-can"

    @property
    def native_value(self):
        return self.status

    @property
    def extra_state_attributes(self):
        return self.common_attributes


class CurrentIntervalSensor(PlantEntity, SensorEntity):
    entity_domain = "sensor"
    key = "current_interval"
    _attr_translation_key = "current_interval"
    _attr_native_unit_of_measurement = UnitOfTime.DAYS

    @property
    def native_value(self):
        return self.active_interval


class CurrentWaterSensor(PlantEntity, SensorEntity):
    entity_domain = "sensor"
    key = "current_water"
    _attr_translation_key = "current_water"
    _attr_device_class = SensorDeviceClass.VOLUME
    _attr_native_unit_of_measurement = UnitOfVolume.MILLILITERS

    @property
    def native_value(self):
        return self.active_water


def _loaded_plants(hass: HomeAssistant) -> list[tuple[ConfigEntry, Any]]:
    """Return every loaded plant entry and its mutable data."""
    domain_data = hass.data.get(DOMAIN, {})
    return [
        (entry, domain_data[entry.entry_id])
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.entry_id in domain_data
    ]


def _entity_id(hass: HomeAssistant, entry_id: str, platform: str, key: str) -> str | None:
    registry = er.async_get(hass)
    return registry.async_get_entity_id(platform, DOMAIN, f"{entry_id}_{key}")


def _snapshot(hass: HomeAssistant, entry: ConfigEntry, plant: Any) -> dict[str, Any]:
    """Build the current plan record for one plant."""
    config = {**entry.data, **entry.options}
    now = dt_util.now()
    season = season_at(now)
    temperature = None
    temperature_entity = config.get(CONF_TEMPERATURE_ENTITY)
    if temperature_entity:
        state = hass.states.get(temperature_entity)
        try:
            temperature = float(state.state) if state else None
        except (TypeError, ValueError):
            temperature = None

    heat_reduction = (
        2
        if temperature is not None and temperature >= 35
        else 1
        if temperature is not None and temperature >= 28
        else 0
    )
    intervals = {
        item: int(config[f"{CONF_INTERVAL_PREFIX}{item}"]) for item in SEASONS
    }
    water = {item: int(config[f"{CONF_WATER_PREFIX}{item}"]) for item in SEASONS}
    active_interval = max(0, intervals[season] - heat_reduction)
    next_watering = next_watering_at(plant.last_watered, active_interval)
    status = watering_status(plant.last_watered, active_interval, now)

    return {
        "name": config[CONF_PLANT_NAME],
        "icon": config.get(CONF_ICON, "mdi:sprout"),
        "status": status,
        "status_entity_id": _entity_id(hass, entry.entry_id, "sensor", "status"),
        "water_button_entity_id": _entity_id(hass, entry.entry_id, "button", "water_now"),
        "intervals": intervals,
        "water": water,
        "current_season": season,
        "current_interval_days": active_interval,
        "current_water_ml": water[season],
        "temperature": temperature,
        "heat_reduction_days": heat_reduction,
        "last_watered": plant.last_watered.isoformat() if plant.last_watered else None,
        "next_watering": next_watering.isoformat() if next_watering else None,
    }


def _plan(hass: HomeAssistant) -> dict[str, dict[str, Any]]:
    """Build a stable, human-readable mapping of all plants."""
    plan: dict[str, dict[str, Any]] = {}
    for entry, plant in _loaded_plants(hass):
        item = _snapshot(hass, entry, plant)
        key = slugify(item["name"])
        if key in plan:
            key = f"{key}_{entry.entry_id[:6]}"
        plan[key] = item
    return plan


class OverviewSensorBase(SensorEntity):
    """Base class for integration-wide sensors."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_PLANTS_UPDATED, self.async_write_ha_state
            )
        )


class OverviewStatusSensor(OverviewSensorBase):
    """Summarize due plants and the next watering date."""

    entity_id = "sensor.plant_watering_status"
    _attr_unique_id = "plant_watering_overview_status"
    _attr_translation_key = "overview_status"
    _attr_icon = "mdi:watering-can"

    @property
    def native_value(self) -> int:
        return len(self._due_items)

    @property
    def _items(self) -> list[dict[str, Any]]:
        return list(_plan(self.hass).values())

    @property
    def _due_items(self) -> list[dict[str, Any]]:
        return [item for item in self._items if item["status"] in DUE_STATUSES]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        items = self._items
        due = [item for item in items if item["status"] in DUE_STATUSES]
        upcoming = [item for item in items if item["next_watering"]]
        upcoming.sort(key=lambda item: item["next_watering"])
        next_item = due[0] if due else upcoming[0] if upcoming else None
        season = season_at(dt_util.now())
        next_watering = (
            "now"
            if due
            else next_item["next_watering"]
            if next_item
            else None
        )
        return {
            "plant_count": len(items),
            "due_plants": [item["name"] for item in due],
            "due_plant_names": ", ".join(item["name"] for item in due),
            "next_plant": next_item["name"] if next_item else None,
            "next_watering": next_watering,
            "season": season,
            "season_name": SEASON_NAMES[season],
            "heat_adjustment_active": any(item["heat_reduction_days"] > 0 for item in items),
        }


class WateringPlanSensor(OverviewSensorBase):
    """Expose the complete plan of all configured plants."""

    entity_id = "sensor.plant_watering_plan"
    _attr_unique_id = "plant_watering_plan"
    _attr_translation_key = "watering_plan"
    _attr_icon = "mdi:sprout"

    @property
    def native_value(self) -> str:
        return "ready"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        plan = _plan(self.hass)
        return {
            "plant_count": len(plan),
            "plan_json": plan,
        }

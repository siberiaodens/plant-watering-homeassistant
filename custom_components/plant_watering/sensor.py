"""Sensors for Plant Watering."""

from datetime import timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTime, UnitOfVolume
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN, SEASON_NAMES, UPDATE_INTERVAL_MINUTES
from .entity import PlantEntity


async def async_setup_entry(hass, entry, async_add_entities):
    plant = hass.data[DOMAIN][entry.entry_id]
    entities = [PlantStatusSensor(entry, plant), CurrentIntervalSensor(entry, plant), CurrentWaterSensor(entry, plant)]
    async_add_entities(entities)
    cancel = async_track_time_interval(hass, lambda now: [entity.async_write_ha_state() for entity in entities], timedelta(minutes=UPDATE_INTERVAL_MINUTES))
    entry.async_on_unload(cancel)


class PlantStatusSensor(PlantEntity, SensorEntity):
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
    key = "current_interval"
    _attr_translation_key = "current_interval"
    _attr_native_unit_of_measurement = UnitOfTime.DAYS

    @property
    def native_value(self):
        return self.active_interval


class CurrentWaterSensor(PlantEntity, SensorEntity):
    key = "current_water"
    _attr_translation_key = "current_water"
    _attr_device_class = SensorDeviceClass.VOLUME
    _attr_native_unit_of_measurement = UnitOfVolume.MILLILITERS

    @property
    def native_value(self):
        return self.active_water

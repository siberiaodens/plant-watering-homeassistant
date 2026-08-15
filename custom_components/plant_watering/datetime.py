"""Last watered date/time entity."""

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .entity import PlantEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([LastWateredEntity(entry, hass.data[DOMAIN][entry.entry_id])])


class LastWateredEntity(PlantEntity, DateTimeEntity):
    entity_domain = "datetime"
    key = "last_watered"
    _attr_translation_key = "last_watered"
    _attr_icon = "mdi:calendar-check"

    @property
    def native_value(self):
        return self.plant.last_watered

    async def async_set_value(self, value):
        if value.tzinfo is None:
            value = value.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        await self.plant.async_set_last_watered(value)

"""Water-now button."""

from homeassistant.components.button import ButtonEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .entity import PlantEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([WaterNowButton(entry, hass.data[DOMAIN][entry.entry_id])])


class WaterNowButton(PlantEntity, ButtonEntity):
    entity_domain = "button"
    key = "water_now"
    _attr_translation_key = "water_now"
    _attr_icon = "mdi:watering-can"

    async def async_press(self):
        await self.plant.async_set_last_watered(dt_util.now())

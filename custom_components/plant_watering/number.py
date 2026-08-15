"""Editable seasonal values."""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfTime, UnitOfVolume

from .const import CONF_INTERVAL_PREFIX, CONF_WATER_PREFIX, DOMAIN, SEASONS
from .entity import PlantEntity


async def async_setup_entry(hass, entry, async_add_entities):
    plant = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            SeasonNumber(entry, plant, season, kind)
            for season in SEASONS
            for kind in ("interval", "water")
        ]
    )


class SeasonNumber(PlantEntity, NumberEntity):
    entity_domain = "number"
    _attr_mode = NumberMode.BOX

    def __init__(self, entry, plant, season, kind):
        self.season = season
        self.kind = kind
        self.key = f"{kind}_{season}"
        self._attr_translation_key = self.key
        if kind == "interval":
            self._attr_native_min_value = 1
            self._attr_native_max_value = 365
            self._attr_native_step = 1
            self._attr_native_unit_of_measurement = UnitOfTime.DAYS
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 10000
            self._attr_native_step = 10
            self._attr_native_unit_of_measurement = UnitOfVolume.MILLILITERS
        super().__init__(entry, plant)

    @property
    def native_value(self):
        return self.config[self.key]

    async def async_set_native_value(self, value):
        options = {**self.entry.options, self.key: int(value)}
        self.hass.config_entries.async_update_entry(self.entry, options=options)

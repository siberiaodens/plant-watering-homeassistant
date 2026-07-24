"""Config flow for Plant Watering."""

from __future__ import annotations

import uuid

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    CONF_ICON,
    CONF_INTERVAL_PREFIX,
    CONF_PLANT_NAME,
    CONF_TEMPERATURE_ENTITY,
    CONF_WATER_PREFIX,
    DEFAULTS,
    DOMAIN,
    SEASONS,
)


def _schema(defaults: dict, include_name: bool = True) -> vol.Schema:
    fields: dict = {}
    if include_name:
        fields[vol.Required(CONF_PLANT_NAME, default=defaults.get(CONF_PLANT_NAME, ""))] = str
    fields[vol.Optional(CONF_ICON, default=defaults.get(CONF_ICON, "mdi:sprout"))] = selector.IconSelector()
    temperature_key = (
        vol.Optional(CONF_TEMPERATURE_ENTITY, default=defaults[CONF_TEMPERATURE_ENTITY])
        if defaults.get(CONF_TEMPERATURE_ENTITY)
        else vol.Optional(CONF_TEMPERATURE_ENTITY)
    )
    fields[temperature_key] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
    )
    for season in SEASONS:
        interval = f"{CONF_INTERVAL_PREFIX}{season}"
        water = f"{CONF_WATER_PREFIX}{season}"
        fields[vol.Required(interval, default=defaults.get(interval, DEFAULTS[interval]))] = selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, max=365, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="Tage")
        )
        fields[vol.Required(water, default=defaults.get(water, DEFAULTS[water]))] = selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=10000, step=10, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="ml")
        )
    return vol.Schema(fields)


class PlantWateringConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id(str(uuid.uuid4()))
            return self.async_create_entry(title=user_input[CONF_PLANT_NAME], data=user_input)
        return self.async_show_form(step_id="user", data_schema=_schema({}))

    @staticmethod
    def async_get_options_flow(config_entry):
        return PlantWateringOptionsFlow(config_entry)


class PlantWateringOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        current = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            name = user_input.pop(CONF_PLANT_NAME)
            self.hass.config_entries.async_update_entry(self.config_entry, title=name)
            user_input[CONF_PLANT_NAME] = name
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(step_id="init", data_schema=_schema(current))

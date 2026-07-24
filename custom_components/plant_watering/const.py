"""Constants for Plant Watering."""

DOMAIN = "plant_watering"
PLATFORMS = ["sensor", "number", "datetime", "button"]

CONF_PLANT_NAME = "plant_name"
CONF_ICON = "icon"
CONF_TEMPERATURE_ENTITY = "temperature_entity"
CONF_INTERVAL_PREFIX = "interval_"
CONF_WATER_PREFIX = "water_"

SEASONS = ("spring", "summer", "autumn", "winter")
SEASON_NAMES = {
    "spring": "Frühling",
    "summer": "Sommer",
    "autumn": "Herbst",
    "winter": "Winter",
}

DEFAULTS = {
    "interval_spring": 3,
    "interval_summer": 2,
    "interval_autumn": 4,
    "interval_winter": 10,
    "water_spring": 150,
    "water_summer": 200,
    "water_autumn": 150,
    "water_winter": 100,
}

STORE_VERSION = 1
UPDATE_INTERVAL_MINUTES = 15

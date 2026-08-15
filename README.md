# Plant Watering for Home Assistant

Plant Watering is a HACS custom integration that represents every plant as a Home Assistant device with a seasonal watering schedule.

## Features

- One config entry and Home Assistant device per plant
- Watering intervals and amounts for spring, summer, autumn, and winter
- Optional heat adjustment: one day shorter from 28 °C and two days shorter from 35 °C; the effective interval may reach zero days
- Entities for watering status, current interval, current amount, and last watering time
- A **Watered now** button
- Editable `number` entities for all seasonal values
- Persistent storage of the last watering time
- Integration-wide status and watering plan sensors
- English and German UI translations

Meteorological seasons change automatically on the first day of March, June, September, and December.

Configured seasonal intervals always remain at least one day. Heat adjustment is applied only to the effective interval and may reduce it to zero days. For example, if a plant has a summer interval of one day and the temperature reaches 28 °C, watering it in the morning does not postpone it until the next day: it receives the `due_again` status and becomes due again on the same day.

## Language model

All internal identifiers, states, attributes, units, source code, and documentation are English. Home Assistant localizes only the visible UI through:

- `strings.json` as the English source language
- `translations/en.json` for English
- `translations/de.json` for German

This keeps automations and templates independent of the selected Home Assistant language. Additional UI languages can be added later without changing the integration's technical interface.

## Installation

### HACS

1. Add this GitHub repository to HACS as a custom repository of type **Integration**.
2. Install **Plant Watering** and restart Home Assistant.
3. Open **Settings → Devices & services → Add integration** and search for **Plant Watering**.
4. Complete the setup dialog once for every plant.

## Plant entities

Entity IDs are generated from explicit English technical keys and do not depend on the selected UI language. They can still be customized in Home Assistant. The following example assumes a plant named `Basil`.

```yaml
type: custom:mushroom-template-card
entity: sensor.basil_status
primary: Basil
secondary: |-
  {% set next_watering = state_attr(entity, 'next_watering') %}
  {{ state_translated(entity) }}
  Last watered: {{ as_datetime(state_attr(entity, 'last_watered')).strftime('%Y-%m-%d') if state_attr(entity, 'last_watered') else 'Never' }}
  Interval: {{ state_attr(entity, 'interval_days') }} day(s)
  Amount: {{ state_attr(entity, 'water_ml') }} ml
multiline_secondary: true
icon: mdi:leaf
icon_color: >-
  {% set status = states(entity) %}
  {{ 'blue' if status in ['due', 'due_again'] else 'amber' if status == 'tomorrow' else 'red' if status == 'unknown' else 'green' }}
badge_icon: >-
  {% set status = states(entity) %}
  {{ 'mdi:water-plus' if status == 'due_again' else 'mdi:water' if status == 'due' else 'mdi:clock-alert-outline' if status == 'tomorrow' else 'mdi:alert-circle' if status == 'unknown' else 'mdi:check' }}
tap_action:
  action: perform-action
  perform_action: button.press
  target:
    entity_id: button.basil_water_now
  confirmation:
    text: Mark Basil as watered now?
hold_action:
  action: more-info
```

Automations can react directly to `sensor.<plant>_status`. Its technical states are:

- `unknown`: the plant has never been marked as watered
- `due`: watering is due now
- `due_again`: the plant was watered today but is due again because its effective interval is zero days
- `tomorrow`: watering is due within 24 hours
- `ok`: watering is not due yet

### Translated states in dashboard templates

`states(entity)` always returns the English technical state, such as `tomorrow`. Use Home Assistant's `state_translated(entity)` function when rendering that state for a user:

```jinja
{{ state_translated('sensor.basil_status') }}
```

Home Assistant renders the result in its configured language. Continue to use the raw state for conditions so templates remain language-independent:

```jinja
{% if states('sensor.basil_status') == 'tomorrow' %}
  {{ state_translated('sensor.basil_status') }}
{% endif %}
```

## Overall status and watering plan

The integration creates exactly two additional sensors covering all configured plants:

- **Plant Watering Status**: its state is the number of plants currently due. Plants that have never been marked as watered also count as due.
- **Plant Watering Plan**: its `plan_json` attribute contains the complete plan for every loaded plant.

Important attributes of the overall status sensor:

| Attribute | Content |
| --- | --- |
| `plant_count` | Total number of loaded plants |
| `due_plants` | List of the names of all due plants |
| `due_plant_names` | Due plant names as a comma-separated string |
| `next_plant` | Next plant to water |
| `next_watering` | Next ISO-formatted timestamp or `now` |
| `season` | Current technical season key |
| `season_name` | Current English season name |
| `heat_adjustment_active` | Whether at least one interval is shortened because of heat |

The central sensors use the IDs `sensor.plant_watering_status` and `sensor.plant_watering_plan`. The config-entry schema migration converts entity-registry entries created with localized IDs to English technical IDs. If a target ID is already occupied, Home Assistant assigns the next available English ID, such as `_2`.

### Entity ID migration

Earlier integration revisions allowed Home Assistant to derive entity IDs from localized display names. During the first startup with the new config-entry schema, every version 1 plant config entry is migrated to version 2 and its registered entities are renamed to English technical suffixes. For example:

| Previous localized ID | New technical ID |
| --- | --- |
| `sensor.basilikum_aktuelles_intervall` | `sensor.basilikum_current_interval` |
| `sensor.basilikum_aktuelle_wassermenge` | `sensor.basilikum_current_water` |
| `sensor.basilikum_giessstatus` | `sensor.basilikum_status` |
| `datetime.basilikum_zuletzt_gegossen` | `datetime.basilikum_last_watered` |
| `button.basilikum_jetzt_gegossen` | `button.basilikum_water_now` |

The plant-name portion remains the user-provided plant name. Only the integration-owned technical suffix is forced to English. Update YAML dashboards and automations that reference an older localized entity ID.

### Overall status card

```yaml
type: custom:mushroom-template-card
entity: sensor.plant_watering_status
primary: >-
  {% set count = states(entity) | int(0) %}
  💧 {{ count }} plant{% if count != 1 %}s{% endif %} due
secondary: >-
  {% set names = state_attr(entity, 'due_plant_names') %}
  {% if states(entity) | int(0) > 0 %}
    {{ names }}
  {% else %}
    No plants need watering today.
  {% endif %}
  {% if state_attr(entity, 'heat_adjustment_active') %}
    {{ '\n' }}🔥 Warm conditions: watering intervals have been shortened.
  {% endif %}
multiline_secondary: true
icon: mdi:watering-can
icon_color: >-
  {{ 'blue' if states(entity) | int(0) > 0 else 'green' }}
tap_action:
  action: more-info
grid_options:
  columns: full
```

### Watering plan Markdown card

```yaml
type: markdown
title: Watering plan
content: |-
  {% set plan = state_attr('sensor.plant_watering_plan', 'plan_json') or {} %}
  {% for key, plant in plan.items() %}
  {% set status = plant.status %}
  **{{ '💧' if status in ['due', 'due_again', 'unknown'] else '⏰' if status == 'tomorrow' else '✅' }} {{ plant.name }}**<br>
  {{ state_translated(plant.status_entity_id) if plant.status_entity_id else status }} · {{ plant.current_water_ml }} ml · every {{ plant.current_interval_days }} day(s)

  {% endfor %}
```

## Notification automation

This automation follows the behavior of the original YAML package and creates a persistent notification after sunrise and in the early evening whenever plants are due:

```yaml
automation:
  - alias: Plants – watering reminder
    mode: single
    triggers:
      - trigger: sun
        event: sunrise
        offset: "00:30:00"
      - trigger: time
        at: "18:00:00"
    conditions:
      - condition: numeric_state
        entity_id: sensor.plant_watering_status
        above: 0
    actions:
      - action: persistent_notification.create
        data:
          notification_id: plant_watering
          title: >-
            💧 {{ states('sensor.plant_watering_status') }} plants due
          message: >-
            Water today: {{ state_attr('sensor.plant_watering_status', 'due_plant_names') }}.

            Season: {{ state_attr('sensor.plant_watering_status', 'season_name') }}.
            Check the soil before watering.
```

Replace or supplement `persistent_notification.create` with the desired `notify.mobile_app_...` action to send a push notification.

## Watering plan data

The `plan_json` attribute is a mapping keyed by a slug derived from each plant name. Every plant record contains:

- `name`
- `icon`
- `status`
- `status_entity_id`
- `water_button_entity_id`
- `intervals`
- `water`
- `current_season`
- `current_interval_days`
- `current_water_ml`
- `temperature`
- `heat_reduction_days`
- `last_watered`
- `next_watering`

All keys and values intended for automations remain English regardless of the selected Home Assistant UI language.

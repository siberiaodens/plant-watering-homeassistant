# Plant Watering für Home Assistant

Eine HACS Custom Integration, die jede Pflanze als Gerät mit saisonalem Gießplan anlegt.

## Funktionen

- Eine Pflanze pro Config Entry/Home-Assistant-Gerät
- Gießintervall und Wassermenge für Frühling, Sommer, Herbst und Winter
- Optionale Hitzekorrektur: ab 28 °C ein Tag, ab 35 °C zwei Tage kürzer (mindestens ein Tag)
- Entitäten für Status, aktuelles Intervall, aktuelle Wassermenge und letztes Gießen
- Button **Jetzt gegossen**
- Alle Saisonwerte auch direkt als `number`-Entitäten bearbeitbar
- Persistentes Datum des letzten Gießens

Die meteorologischen Jahreszeiten wechseln automatisch am 1. März, Juni, September und Dezember.

## Installation

### HACS

1. Dieses GitHub-Repository in HACS als benutzerdefiniertes Repository vom Typ **Integration** hinzufügen.
2. **Plant Watering** installieren und Home Assistant neu starten.
3. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach **Plant Watering** suchen.
4. Den Dialog einmal pro Pflanze ausfüllen.

Zum lokalen Test kann `custom_components/plant_watering` direkt nach `/config/custom_components/plant_watering` kopiert werden.

> Vor einer Veröffentlichung in `manifest.json` bitte `OWNER` durch den tatsächlichen GitHub-Benutzernamen ersetzen.

## Mushroom-Karte

Die tatsächlichen Entity-IDs hängen vom Pflanzennamen ab. Dieses Beispiel muss entsprechend angepasst werden:

```yaml
type: custom:mushroom-template-card
entity: sensor.basilikum_giessstatus
primary: Basilikum
secondary: |-
  {% set next = state_attr(entity, 'next_watering') %}
  {{ states(entity) }}
  Zuletzt: {{ as_datetime(state_attr(entity, 'last_watered')).strftime('%d.%m.%Y') if state_attr(entity, 'last_watered') else 'Noch nie' }}
  Intervall: {{ state_attr(entity, 'interval_days') }} Tag(e)
  Menge: {{ state_attr(entity, 'water_ml') }} ml
multiline_secondary: true
icon: mdi:leaf
icon_color: >-
  {% set s = states(entity) %}
  {{ 'blue' if s == 'due' else 'amber' if s == 'tomorrow' else 'red' if s == 'unknown' else 'green' }}
badge_icon: >-
  {% set s = states(entity) %}
  {{ 'mdi:water' if s == 'due' else 'mdi:clock-alert-outline' if s == 'tomorrow' else 'mdi:alert-circle' if s == 'unknown' else 'mdi:check' }}
tap_action:
  action: perform-action
  perform_action: button.press
  target:
    entity_id: button.basilikum_jetzt_gegossen
  confirmation:
    text: Basilikum als jetzt gegossen markieren?
hold_action:
  action: more-info
```

Automationen können direkt auf `sensor.<pflanze>_giessstatus` mit Zustand `due` reagieren.

## Wechsel vom bisherigen YAML-Package

1. Zuerst alle Pflanzen in der Integration anlegen.
2. Bei jeder Pflanze über die Entität **Zuletzt gegossen** das bisherige Datum übernehmen.
3. Entity-IDs in Karten und Automationen auf die neuen Status- und Button-Entitäten umstellen.
4. Erst danach das bisherige Package aus `configuration.yaml` entfernen und Home Assistant neu starten.

Die alten `input_datetime`-Helfer sollten bis zum Abschluss der Migration erhalten bleiben. Die bisherige
Benachrichtigungsautomation lässt sich anschließend vereinfachen, indem sie auf Statusänderungen nach `due`
reagiert. Für mehrere Pflanzen kann in Home Assistant eine Gruppe der Statussensoren oder ein Template-Sensor
für die Anzahl fälliger Pflanzen angelegt werden.

# GIOŚ (Główny Inspektorat Ochrony Środowiska)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)

The component collects data about air quality from [GIOŚ](http://powietrze.gios.gov.pl/pjp/current) and present as sensors in Home Assitant.

## Minimal configuration
```yaml
sensor:
  - platform: gios
    station_id: 530
```

## Custom configuration example
```yaml
sensor:
  - platform: gios
    station_id: 530
    name: 'Air Quality'
    scan_interval: 2700
```

## Arguments

key | optional | type | default | description
-- | -- | -- | -- | --
`station_id` | False | integer | | ID of the measuring station
`scan_interval` | True | integer | 1800 | rate in seconds at which GIOŚ should be polled for new data

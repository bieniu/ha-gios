# GIOŚ (Główny Inspektorat Ochrony Środowiska)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)

![Screenshot](https://github.com/bieniu/ha-gios/blob/master/images/gios-ha.png?raw=true)

The component collects data about air quality in Poland from [GIOŚ](http://powietrze.gios.gov.pl/pjp/current) and present as sensors in Home Assitant.

## How to find station_id
- go to http://powietrze.gios.gov.pl/pjp/current
- find on the map a measurement station located closest to your home
- go to "More info" link
- look at site address, for ex. for this address http://powietrze.gios.gov.pl/pjp/current/station_details/chart/291 `station_id` is 291

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

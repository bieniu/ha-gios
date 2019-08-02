![Screenshot](https://github.com/bieniu/ha-gios/blob/master/images/gios-ha.png?raw=true)

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
    ignored_conditions:
      - pm25
      - so2
```

## Arguments
key | optional | type | default | description
-- | -- | -- | -- | --
`station_id` | False | integer | | ID of the measuring station
`scan_interval` | True | integer | 1800 | rate in seconds at which GIOŚ should be polled for new data, GIOS API regulations prohibit pool for data more often than every 30 minutes
`ignored_conditions` | True | list | | list of ignored conditions, available: `c6h6`, `co`, `no2`, `o3`, `pm25`, `pm10`, `so2`, `aqi`

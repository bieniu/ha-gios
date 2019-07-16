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

![Screenshot](https://github.com/bieniu/ha-gios/blob/master/images/gios-ha.png?raw=true)

You can add this integration to Home Assistant via `Configuration -> Integrations -> Add -> Airly` or `configuration.yaml` file. You can add this integration several times for different locations, e.g. home and work.

## How to find station_id
- go to http://powietrze.gios.gov.pl/pjp/current
- find on the map a measurement station located closest to your home
- go to "More info" link
- look at site address, for ex. for this address http://powietrze.gios.gov.pl/pjp/current/station_details/chart/291 `station_id` is 291

## Breaking change
Home Assistant 0.98+ allows disabling unnecessary entities in the entity registry. For this reason, the `ignored_conditions` argument has been removed.

## Configuration example
```yaml
sensor:
  - platform: gios
    station_id: 530
    name: 'Air Quality'
```

## Arguments
key | optional | type | default | description
-- | -- | -- | -- | --
`station_id` | False | integer | | ID of the measuring station
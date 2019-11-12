# GIOŚ (Główny Inspektorat Ochrony Środowiska)
[![GitHub Release][releases-shield]][releases]
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)
[![Community Forum][forum-shield]][forum]
[![Buy me a coffee][buy-me-a-coffee]](https://www.buymeacoffee.com/QnLdxeaqO)

![Screenshot](https://github.com/bieniu/ha-gios/blob/master/images/gios-ha.png?raw=true)

The integration collects data about air quality in Poland from [GIOŚ](http://powietrze.gios.gov.pl/pjp/current) and present as sensors in Home Assitant. You can add this to Home Assistant via `Configuration -> Integrations -> Add -> Airly` or `configuration.yaml` file. You can add this integration several times for different locations, e.g. home and work.

## How to find station_id
- go to http://powietrze.gios.gov.pl/pjp/current
- find on the map a measurement station located closest to your home
- go to "More info" link
- look at site address, for ex. for this address http://powietrze.gios.gov.pl/pjp/current/station_details/chart/291 `station_id` is 291

## Breaking change
Home Assistant 0.98+ allows disabling unnecessary entities in the entity registry. For this reason, the `monitored_conditions` argument has been removed.

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

[releases]: https://github.com/bieniu/ha-gios/releases
[releases-shield]: https://img.shields.io/github/release/bieniu/ha-gios.svg?style=popout
[forum]: https://community.home-assistant.io/t/gios-polish-glowny-inspektorat-ochrony-srodowiska-air-quality-data-integration/127519
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=popout
[buy-me-a-coffee]: https://img.shields.io/static/v1.svg?label=%20&message=Buy%20me%20a%20coffee&color=6f4e37&logo=buy%20me%20a%20coffee&logoColor=white

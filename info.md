[![Community Forum][forum-shield]][forum]  [![Buy me a coffee][buy-me-a-coffee-shield]][buy-me-a-coffee]  [![PayPal_Me][paypal-me-shield]][paypal-me]

## This integration is deprecated
Home Assistant 0.104 and newer includes official GIOŚ integration.
Differences between the official and custom version:
- no configurable `scan interval`
- data is represented in `air_quality` entity

These differences result from the requirements for official integrations. You can still use the custom version of the integration. If you want to use the official version, remove integration from Configuration -> Integrations, remove component's files from the `/config/custom_components` folder and restart Home Assistant.

![Screenshot](https://github.com/bieniu/ha-gios/blob/master/images/gios-ha.png?raw=true)

You can add this integration to Home Assistant via `Configuration -> Integrations -> button with + sign -> GIOŚ`. You can add this integration several times for different locations, e.g. home and work.

## How to find station_id
- go to http://powietrze.gios.gov.pl/pjp/current
- find on the map a measurement station located closest to your home
- go to "More info" link
- look at site address, for ex. for this address http://powietrze.gios.gov.pl/pjp/current/station_details/chart/291 `station_id` is 291

[forum]: https://community.home-assistant.io/t/gios-polish-glowny-inspektorat-ochrony-srodowiska-air-quality-data-integration/127519
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=popout
[buy-me-a-coffee-shield]: https://img.shields.io/static/v1.svg?label=%20&message=Buy%20me%20a%20coffee&color=6f4e37&logo=buy%20me%20a%20coffee&logoColor=white
[buy-me-a-coffee]: https://www.buymeacoffee.com/QnLdxeaqO
[paypal-me-shield]: https://img.shields.io/static/v1.svg?label=%20&message=PayPal.Me&logo=paypal
[paypal-me]: https://www.paypal.me/bieniu79

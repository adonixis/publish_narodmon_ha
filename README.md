# Publish Narodmon for Home Assistant

Custom integration that publishes Home Assistant sensor readings to [Народный мониторинг](https://narodmon.ru) using the Narodmon PRO TCP protocol (port 8283).

## Features

- Config flow UI — no YAML configuration required
- Select multiple `sensor` entities to publish
- Optional device name and coordinates entity (latitude/longitude attributes)
- Sends when values change (configurable interval, default 6 min)
- Force send if no changes for a long time (default 20 min)
- Reconfigure existing entries from the integration page

## Installation

### HACS

1. Add this repository as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories/) in HACS (category: Integration).
2. Install **Publish Narodmon**.
3. Restart Home Assistant.

### Manual

Copy the `custom_components/publish_narodmon` folder into your Home Assistant `custom_components` directory and restart.

## Configuration

1. Go to **Settings → Devices & services → Add integration**.
2. Search for **Publish Narodmon**.
3. Enter your device **MAC address** (as registered on narodmon.ru).
4. Optionally set a **device name** and **coordinates entity** (e.g. `zone.home` or a `person` entity).
5. Select **sensors** to publish.
6. Adjust send intervals if needed.

To change sensors or intervals later, open the integration entry and choose **Reconfigure**.

## Protocol

Data is sent to `narodmon.ru:8283` in the Narodmon PRO format:

```
#MAC#Name
#LAT#55.75
#LNG#37.62
#TEMP#22.5#Living room temperature
##
```

Sensor `device_class` values are mapped automatically (`temperature` → `TEMP`, `humidity` → `RH`, etc.). Duplicate types are numbered (`TEMP1`, `TEMP2`, …).

## Development

```bash
scripts/develop
```

## License

See [LICENSE](LICENSE).

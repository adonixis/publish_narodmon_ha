"""Constants for the Narodmon integration."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "publish_narodmon"

CONF_DEVICE_MAC = "device_mac"
CONF_DEVICE_NAME = "device_name"
CONF_COORDINATES_ENTITY = "coordinates_entity"
CONF_SENSORS = "sensors"
CONF_SEND_INTERVAL_CHANGED = "send_interval_changed"
CONF_SEND_INTERVAL_FORCE = "send_interval_force"

DEFAULT_SEND_INTERVAL_CHANGED = 360
DEFAULT_SEND_INTERVAL_FORCE = 1200

NARODMON_HOST = "narodmon.ru"
NARODMON_PORT = 8283
SOCKET_TIMEOUT = 10
SCHEDULER_INTERVAL = 60
STARTUP_DELAY = 30

DEVICE_CLASS_MAP: dict[str | None, str] = {
    "temperature": "TEMP",
    "humidity": "RH",
    "pressure": "PRESS",
    "battery": "BATCHARGE",
    "power": "W",
    "illuminance": "LIGHT",
    "signal_strength": "RSSI",
    None: "SENSOR",
}

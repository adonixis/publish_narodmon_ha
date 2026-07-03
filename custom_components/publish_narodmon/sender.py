"""Narodmon data sender."""

from __future__ import annotations

import collections
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util

from .client import send_payload
from .const import (
    CONF_COORDINATES_ENTITY,
    CONF_DEVICE_MAC,
    CONF_DEVICE_NAME,
    CONF_SEND_INTERVAL_CHANGED,
    CONF_SEND_INTERVAL_FORCE,
    CONF_SENSORS,
    DEFAULT_SEND_INTERVAL_CHANGED,
    DEFAULT_SEND_INTERVAL_FORCE,
    DEVICE_CLASS_MAP,
    LOGGER,
    SCHEDULER_INTERVAL,
    STARTUP_DELAY,
)
from .protocol import SensorReading, build_device_block, build_payload

if TYPE_CHECKING:
    from .data import NarodmonConfigEntry


class NarodmonSender:
    """Send Home Assistant sensor data to narodmon.ru."""

    def __init__(self, hass: HomeAssistant, entry: NarodmonConfigEntry) -> None:
        """Initialize the sender."""
        self.hass = hass
        self.entry = entry
        self._cancel_callbacks: list[Any] = []
        self._last_values: dict[str, str] = {}
        self._data_changed = False
        self._last_attempt_time: datetime | None = None
        self._last_send_time: datetime | None = None
        self._started = False
        self._sensor_types: dict[str, str] = {}

    async def async_start(self) -> None:
        """Subscribe to sensor changes and start the scheduler."""
        sensors = self._get_configured_sensors()
        if not sensors:
            LOGGER.error("No sensors configured for %s", self.entry.title)
            return

        self._build_sensor_types(sensors)

        @callback
        def _on_state_change(event: Event) -> None:
            new_state: State | None = event.data.get("new_state")
            if new_state is None or not self._is_valid_state(new_state.state):
                return

            entity_id = new_state.entity_id
            if entity_id not in sensors:
                return

            self._build_sensor_types(sensors)

            if self._last_values.get(entity_id) != new_state.state:
                self._last_values[entity_id] = new_state.state
                self._data_changed = True
                LOGGER.debug("Data changed: %s = %s", entity_id, new_state.state)

        for entity_id in sensors:
            self._cancel_callbacks.append(
                async_track_state_change_event(self.hass, [entity_id], _on_state_change)
            )

        @callback
        def _scheduler(_now: datetime) -> None:
            self._check_send()

        self._cancel_callbacks.append(
            async_track_time_interval(
                self.hass,
                _scheduler,
                timedelta(seconds=SCHEDULER_INTERVAL),
            )
        )

        @callback
        def _delayed_start(_now: datetime) -> None:
            self._started = True
            LOGGER.info("Narodmon sender started for %s", self.entry.title)

        self._cancel_callbacks.append(
            async_call_later(self.hass, STARTUP_DELAY, _delayed_start)
        )

    async def async_stop(self) -> None:
        """Cancel listeners and timers."""
        for cancel in self._cancel_callbacks:
            cancel()
        self._cancel_callbacks.clear()
        self._started = False

    def _get_configured_sensors(self) -> list[str]:
        """Return sensor entity IDs from the config entry."""
        sensors: list[str] = []
        for entity_id in self.entry.data.get(CONF_SENSORS, []):
            if not entity_id.startswith("sensor."):
                LOGGER.warning("Skipping non-sensor entity: %s", entity_id)
                continue
            sensors.append(entity_id)
        return sensors

    def _build_sensor_types(self, sensors: list[str]) -> None:
        """Map sensor entities to Narodmon type codes."""
        self._sensor_types = {}
        for entity_id in sensors:
            state = self.hass.states.get(entity_id)
            device_class = self._get_device_class(entity_id, state)
            self._sensor_types[entity_id] = DEVICE_CLASS_MAP.get(device_class, "SENSOR")

        count = collections.Counter(self._sensor_types.values())
        for sensor_type, type_count in count.items():
            if type_count <= 1:
                continue
            index = 1
            for entity_id, mapped_type in self._sensor_types.items():
                if mapped_type == sensor_type:
                    self._sensor_types[entity_id] = f"{sensor_type}{index}"
                    index += 1

    def _build_device_data(self) -> str:
        """Build the device header block for the Narodmon protocol."""
        latitude = None
        longitude = None
        coord_entity = self.entry.data.get(CONF_COORDINATES_ENTITY)
        if coord_entity:
            coord_state = self.hass.states.get(coord_entity)
            if coord_state is not None:
                latitude = coord_state.attributes.get("latitude")
                longitude = coord_state.attributes.get("longitude")

        return build_device_block(
            self.entry.data[CONF_DEVICE_MAC],
            device_name=self.entry.data.get(CONF_DEVICE_NAME),
            latitude=latitude,
            longitude=longitude,
        )

    def _get_device_class(self, entity_id: str, state: State | None) -> str | None:
        """Return a sensor device class from state or entity registry metadata."""
        if state is not None:
            return state.attributes.get("device_class")

        entity_entry = er.async_get(self.hass).async_get(entity_id)
        if entity_entry is None:
            return None

        return getattr(entity_entry, "original_device_class", None) or getattr(
            entity_entry, "device_class", None
        )

    @staticmethod
    def _is_valid_state(state: str | None) -> bool:
        """Return whether a state value can be sent."""
        return state not in (None, STATE_UNKNOWN, STATE_UNAVAILABLE)

    def _check_send(self) -> None:
        """Evaluate whether data should be sent now."""
        if not self._started:
            return

        now = dt_util.now()
        send_interval_changed = self.entry.data.get(
            CONF_SEND_INTERVAL_CHANGED, DEFAULT_SEND_INTERVAL_CHANGED
        )
        send_interval_force = self.entry.data.get(
            CONF_SEND_INTERVAL_FORCE, DEFAULT_SEND_INTERVAL_FORCE
        )

        if self._last_send_time is None:
            if (
                self._last_attempt_time is not None
                and (now - self._last_attempt_time).total_seconds()
                < send_interval_changed
            ):
                return
            LOGGER.debug("First send for %s", self.entry.title)
            self.hass.async_create_task(self.async_send_all())
            return

        delta = (now - self._last_send_time).total_seconds()

        if self._data_changed and delta >= send_interval_changed:
            LOGGER.debug("Sending due to changes for %s", self.entry.title)
            self.hass.async_create_task(self.async_send_all())
            return

        if delta >= send_interval_force:
            LOGGER.debug("Force send (timeout) for %s", self.entry.title)
            self.hass.async_create_task(self.async_send_all())

    async def async_send_all(self) -> None:
        """Collect sensor values and send them to Narodmon."""
        self._last_attempt_time = dt_util.now()
        sensors = self._get_configured_sensors()
        self._build_sensor_types(sensors)
        readings: list[SensorReading] = []

        for entity_id in sensors:
            state = self.hass.states.get(entity_id)
            if state is None or not self._is_valid_state(state.state):
                continue

            friendly_name = state.attributes.get("friendly_name", entity_id)
            sensor_type = self._sensor_types.get(entity_id, "SENSOR")
            readings.append(
                SensorReading(
                    sensor_type=sensor_type,
                    value=state.state,
                    name=friendly_name,
                )
            )

        if not readings:
            LOGGER.warning("No valid data to send for %s", self.entry.title)
            return

        payload = build_payload(self._build_device_data(), readings)
        LOGGER.debug("Sending data to Narodmon:\n%s", payload)

        try:
            reply = await self.hass.async_add_executor_job(send_payload, payload)
        except OSError as err:
            LOGGER.error("Connection error for %s: %s", self.entry.title, err)
            return

        self._last_send_time = dt_util.now()
        self._data_changed = False
        LOGGER.info(
            "Narodmon server reply for %s: %s",
            self.entry.title,
            reply.strip(),
        )

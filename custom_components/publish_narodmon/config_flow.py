"""Config flow for the Narodmon integration."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    CONF_COORDINATES_ENTITY,
    CONF_DEVICE_MAC,
    CONF_DEVICE_NAME,
    CONF_SEND_INTERVAL_CHANGED,
    CONF_SEND_INTERVAL_FORCE,
    CONF_SENSORS,
    DEFAULT_SEND_INTERVAL_CHANGED,
    DEFAULT_SEND_INTERVAL_FORCE,
    DOMAIN,
    LOGGER,
)
from .util import entity_exists

if TYPE_CHECKING:
    from homeassistant.helpers.typing import ConfigType

MAC_PATTERN = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|^[0-9A-Fa-f]{12}$")


def normalize_mac(mac: str) -> str:
    """Normalize a MAC address for unique_id storage."""
    return mac.strip().replace(":", "").replace("-", "").upper()


def _options_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the shared config schema."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_DEVICE_MAC,
                default=defaults.get(CONF_DEVICE_MAC, vol.UNDEFINED),
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.TEXT,
                ),
            ),
            vol.Optional(
                CONF_DEVICE_NAME,
                default=defaults.get(CONF_DEVICE_NAME, ""),
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.TEXT,
                ),
            ),
            vol.Optional(
                CONF_COORDINATES_ENTITY,
                default=defaults.get(CONF_COORDINATES_ENTITY, vol.UNDEFINED),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(),
            ),
            vol.Required(
                CONF_SENSORS,
                default=defaults.get(CONF_SENSORS, vol.UNDEFINED),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    multiple=True,
                ),
            ),
            vol.Optional(
                CONF_SEND_INTERVAL_CHANGED,
                default=defaults.get(
                    CONF_SEND_INTERVAL_CHANGED, DEFAULT_SEND_INTERVAL_CHANGED
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=60,
                    max=3600,
                    step=60,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                ),
            ),
            vol.Optional(
                CONF_SEND_INTERVAL_FORCE,
                default=defaults.get(
                    CONF_SEND_INTERVAL_FORCE, DEFAULT_SEND_INTERVAL_FORCE
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=300,
                    max=86400,
                    step=60,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                ),
            ),
        }
    )


class NarodmonConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Narodmon."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = self._validate_input(user_input)
            if not errors:
                mac = normalize_mac(user_input[CONF_DEVICE_MAC])
                await self.async_set_unique_id(mac)
                self._abort_if_unique_id_configured()

                title = user_input.get(CONF_DEVICE_NAME) or mac
                return self.async_create_entry(
                    title=title,
                    data=self._normalize_data(user_input),
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_options_schema(user_input),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            if normalize_mac(user_input[CONF_DEVICE_MAC]) != normalize_mac(
                reconfigure_entry.data[CONF_DEVICE_MAC]
            ):
                errors[CONF_DEVICE_MAC] = "mac_change_not_allowed"
            else:
                errors = self._validate_input(user_input)
                if not errors:
                    return self.async_update_reload_and_abort(
                        reconfigure_entry,
                        data=self._normalize_data(user_input),
                    )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_options_schema(reconfigure_entry.data),
            errors=errors,
        )

    def _validate_input(self, user_input: dict[str, Any]) -> dict[str, str]:
        """Validate user input and return field errors."""
        errors: dict[str, str] = {}
        mac = user_input.get(CONF_DEVICE_MAC, "").strip()

        if not mac or not MAC_PATTERN.match(mac):
            errors[CONF_DEVICE_MAC] = "invalid_mac"

        sensors = user_input.get(CONF_SENSORS) or []
        if not sensors:
            errors[CONF_SENSORS] = "sensors_required"
        else:
            missing = [
                entity_id
                for entity_id in sensors
                if not entity_exists(self.hass, entity_id)
            ]
            if missing:
                errors[CONF_SENSORS] = "entity_not_found"
                LOGGER.warning("Sensors not found: %s", ", ".join(missing))

        coord_entity = user_input.get(CONF_COORDINATES_ENTITY)
        if coord_entity and not entity_exists(self.hass, coord_entity):
            errors[CONF_COORDINATES_ENTITY] = "entity_not_found"

        changed = int(
            user_input.get(CONF_SEND_INTERVAL_CHANGED, DEFAULT_SEND_INTERVAL_CHANGED)
        )
        force = int(
            user_input.get(CONF_SEND_INTERVAL_FORCE, DEFAULT_SEND_INTERVAL_FORCE)
        )
        if force <= changed:
            errors["base"] = "invalid_intervals"

        return errors

    @staticmethod
    def _normalize_data(user_input: dict[str, Any]) -> ConfigType:
        """Normalize stored config entry data."""
        data: ConfigType = {
            CONF_DEVICE_MAC: user_input[CONF_DEVICE_MAC].strip(),
            CONF_SENSORS: list(user_input[CONF_SENSORS]),
            CONF_SEND_INTERVAL_CHANGED: int(
                user_input.get(
                    CONF_SEND_INTERVAL_CHANGED, DEFAULT_SEND_INTERVAL_CHANGED
                )
            ),
            CONF_SEND_INTERVAL_FORCE: int(
                user_input.get(CONF_SEND_INTERVAL_FORCE, DEFAULT_SEND_INTERVAL_FORCE)
            ),
        }

        device_name = (user_input.get(CONF_DEVICE_NAME) or "").strip()
        if device_name:
            data[CONF_DEVICE_NAME] = device_name

        coord_entity = user_input.get(CONF_COORDINATES_ENTITY)
        if coord_entity:
            data[CONF_COORDINATES_ENTITY] = coord_entity

        return data

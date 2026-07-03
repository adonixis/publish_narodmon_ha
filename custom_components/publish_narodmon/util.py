"""Shared helpers for the Publish Narodmon integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers import entity_registry as er

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def entity_exists(hass: HomeAssistant, entity_id: str) -> bool:
    """
    Return whether an entity exists in Home Assistant.

    BLE and other slow integrations may register entities before their
    first state is available in hass.states.
    """
    if hass.states.get(entity_id) is not None:
        return True
    return er.async_get(hass).async_get(entity_id) is not None

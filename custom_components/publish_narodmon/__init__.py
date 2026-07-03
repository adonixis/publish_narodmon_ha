"""Narodmon integration for Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .const import LOGGER
from .data import NarodmonData
from .sender import NarodmonSender

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import NarodmonConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: NarodmonConfigEntry) -> bool:
    """Set up Narodmon from a config entry."""
    sender = NarodmonSender(hass, entry)
    entry.runtime_data = NarodmonData(sender=sender)
    await sender.async_start()
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    LOGGER.debug("Narodmon entry loaded: %s", entry.title)
    return True


async def async_unload_entry(_hass: HomeAssistant, entry: NarodmonConfigEntry) -> bool:
    """Unload a config entry."""
    if entry.runtime_data is not None:
        await entry.runtime_data.sender.async_stop()
    return True


async def async_reload_entry(hass: HomeAssistant, entry: NarodmonConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)

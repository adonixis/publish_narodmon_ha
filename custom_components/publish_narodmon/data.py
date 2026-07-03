"""Custom types for the Narodmon integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .sender import NarodmonSender


@dataclass
class NarodmonData:
    """Runtime data for a Narodmon config entry."""

    sender: NarodmonSender


if TYPE_CHECKING:
    NarodmonConfigEntry = ConfigEntry[NarodmonData]

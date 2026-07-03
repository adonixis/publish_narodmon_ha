"""Narodmon PRO protocol payload builders."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SensorReading:
    """A single sensor value for the Narodmon payload."""

    sensor_type: str
    value: str
    name: str


def build_device_block(
    mac: str,
    *,
    device_name: str | None = None,
    latitude: float | str | None = None,
    longitude: float | str | None = None,
) -> str:
    """Build the device header block (#MAC#Name, optional #LAT/#LNG)."""
    data = f"#{mac}"
    if device_name:
        data += f"#{device_name}"
    if latitude is not None and longitude is not None:
        data += f"\n#LAT#{latitude}\n#LNG#{longitude}"
    return data


def build_sensor_lines(readings: list[SensorReading]) -> str:
    """Build sensor lines for the Narodmon payload."""
    return "".join(
        f"\n#{reading.sensor_type}#{reading.value}#{reading.name}"
        for reading in readings
    )


def build_payload(device_block: str, readings: list[SensorReading]) -> str:
    """Build a complete Narodmon PRO payload."""
    return device_block + build_sensor_lines(readings) + "\n##"

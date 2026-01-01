"""Sensor platform for My Custom Device integration."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    
    # Create sensor entities
    sensors = [
        MyCustomDeviceSensor(
            config_entry.entry_id,
            data["name"],
        )
    ]
    
    async_add_entities(sensors, update_before_add=True)


class MyCustomDeviceSensor(SensorEntity):
    """Representation of a My Custom Device sensor."""

    def __init__(self, entry_id: str, name: str) -> None:
        """Initialize the sensor."""
        self._entry_id = entry_id
        self._attr_name = f"{name} Sensor"
        self._attr_unique_id = f"{entry_id}_sensor"
        self._attr_native_value = None
        
        # Optional: Set device class and state class
        # self._attr_device_class = SensorDeviceClass.TEMPERATURE
        # self._attr_state_class = SensorStateClass.MEASUREMENT
        # self._attr_native_unit_of_measurement = "°C"

    async def async_update(self) -> None:
        """Fetch new state data for the sensor.
        
        This is the only method that should fetch new data for Home Assistant.
        """
        # TODO: Implement your update logic here
        # Example: self._attr_native_value = await fetch_device_value()
        _LOGGER.debug("Updating sensor state")
        # For now, just set a placeholder value
        self._attr_native_value = "Ready"

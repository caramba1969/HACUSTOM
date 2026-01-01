"""Sensor platform for Essent Dynamic Prices integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

import async_timeout
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

# Essent API endpoint
ESSENT_API_URL = "https://www.essent.nl/api/public/tariffmanagement/dynamic-prices/v1/"

# Scan interval: 30 minuten is prima
SCAN_INTERVAL = timedelta(minutes=30)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the sensor platform via YAML."""
    _LOGGER.info("Setting up Essent Sensor via YAML")
    async_add_entities([EssentDynamicPriceSensor()], True)

class EssentDynamicPriceSensor(SensorEntity):
    """Representation of an Essent Dynamic Price sensor."""

    def __init__(self) -> None:
        """Initialize the sensor."""
        self._attr_name = "Essent Dynamic Price"
        self._attr_unique_id = "essent_dynamic_price_sensor_yaml"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "EUR/kWh"
        self._attr_extra_state_attributes = {}
        self._prices_list = []

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        # Gebruik de centrale HA sessie in plaats van een nieuwe aan te maken
        session = async_get_clientsession(self.hass)
        
        try:
            async with async_timeout.timeout(10):
                response = await session.get(ESSENT_API_URL)
                if response.status != 200:
                    _LOGGER.error("Failed to fetch Essent prices. Status: %s", response.status)
                    return
                
                data = await response.json()
                _LOGGER.debug("Received data from Essent API: %s", data)
                
                # Sla de volledige lijst op in de attributen voor Power-Wheel of grafieken
                self._prices_list = self._get_prices_list(data)
                
                # Zoek de huidige prijs
                current_price = self._parse_current_price(self._prices_list)
                
                if current_price is not None:
                    self._attr_native_value = current_price
                else:
                    _LOGGER.warning("Could not determine current price from data")
                
                self._attr_extra_state_attributes = {
                    "last_update": dt_util.now().isoformat(),
                    "price_count": len(self._prices_list) if self._prices_list else 0,
                    # We zetten de lijst in de attributen zodat je ApexCharts kunt gebruiken
                    "prices": self._prices_list 
                }
                        
        except Exception as err:
            _LOGGER.error("Unexpected error updating Essent prices: %s", err)

    def _get_prices_list(self, data: dict | list) -> list:
        """Probeer de lijst met prijzen uit de JSON te halen."""
        if isinstance(data, list):
            return data
        
        for key in ["prices", "data", "tariffs", "items"]:
            if key in data and isinstance(data[key], list):
                return data[key]
        return []

    def _parse_current_price(self, prices_list: list) -> float | None:
        """Zoek de prijs die hoort bij het huidige uur."""
        if not prices_list:
            return None
        
        now = dt_util.now()
        
        # Mogelijke veldnamen voor tijd en prijs
        ts_keys = ["from", "readingDate", "timestamp", "start", "date"]
        val_keys = ["price", "value", "amount", "tariff"]

        for item in prices_list:
            # 1. Zoek de tijdstempel
            start_time = None
            for k in ts_keys:
                if k in item:
                    start_time = dt_util.parse_datetime(str(item[k]))
                    break
            
            if not start_time:
                continue

            # 2. Bepaal eindtijd (vaak 1 uur later bij dynamische prijzen)
            # Als er een 'till' of 'to' is gebruiken we die, anders +1 uur
            end_time = None
            for k in ["till", "to", "end"]:
                if k in item:
                    end_time = dt_util.parse_datetime(str(item[k]))
                    break
            if not end_time:
                end_time = start_time + timedelta(hours=1)

            # 3. Check of 'nu' in dit blok valt
            if start_time <= now < end_time:
                for k in val_keys:
                    if k in item:
                        try:
                            return float(item[k])
                        except (ValueError, TypeError):
                            continue
        return None
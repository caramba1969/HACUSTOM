"""Sensor platform for My Custom Device integration."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging

import aiohttp
import async_timeout

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Essent API endpoint
ESSENT_API_URL = "https://www.essent.nl/api/public/tariffmanagement/dynamic-prices/v1/"

# Scan interval: 30 minutes
SCAN_INTERVAL = timedelta(minutes=30)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    
    # Create sensor entities
    sensors = [
        EssentDynamicPriceSensor(
            config_entry.entry_id,
            data["name"],
        )
    ]
    
    async_add_entities(sensors, update_before_add=True)


class EssentDynamicPriceSensor(SensorEntity):
    """Representation of an Essent Dynamic Price sensor."""

    def __init__(self, entry_id: str, name: str) -> None:
        """Initialize the sensor."""
        self._entry_id = entry_id
        self._attr_name = "Essent Dynamic Price"
        self._attr_unique_id = f"{entry_id}_essent_dynamic_price"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "EUR/kWh"
        self._attr_extra_state_attributes = {}
        self._prices_list = []

    async def async_update(self) -> None:
        """Fetch new state data for the sensor.
        
        This is the only method that should fetch new data for Home Assistant.
        """
        try:
            # Fetch data from Essent API
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    async with session.get(ESSENT_API_URL) as response:
                        if response.status != 200:
                            _LOGGER.error(
                                "Failed to fetch Essent prices. Status: %s",
                                response.status
                            )
                            return
                        
                        data = await response.json()
                        _LOGGER.debug("Received data from Essent API")
                        _LOGGER.debug("JSON keys: %s", list(data.keys()))
                        _LOGGER.debug("Full JSON structure: %s", data)
                        
                        # Parse the data and find current price
                        current_price = self._parse_current_price(data)
                        
                        if current_price is not None:
                            self._attr_native_value = current_price
                            _LOGGER.debug("Current price set to: %s", current_price)
                        else:
                            _LOGGER.warning("Could not determine current price")
                        
                        # Store full price list in attributes
                        self._attr_extra_state_attributes = {
                            "prices": self._prices_list,
                            "last_update": dt_util.now().isoformat(),
                            "raw_data": data,
                        }
                        
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching Essent prices: %s", err)
        except Exception as err:
            _LOGGER.error("Unexpected error updating Essent prices: %s", err)

    def _parse_current_price(self, data: dict) -> float | None:
        """Parse the JSON data to find the current price.
        
        Args:
            data: The JSON data from the Essent API
            
        Returns:
            The current price or None if not found
        """
        # Debug: Log the structure to understand the API format
        _LOGGER.debug("Parsing price data...")
        
        # Common field names to check for price lists
        possible_list_keys = ["prices", "data", "tariffs", "rates", "items", "results"]
        prices_list = None
        
        # Try to find the prices list
        for key in possible_list_keys:
            if key in data:
                prices_list = data[key]
                _LOGGER.debug("Found prices list under key: %s", key)
                break
        
        # If data itself is a list
        if isinstance(data, list):
            prices_list = data
            _LOGGER.debug("Data is directly a list")
        
        if not prices_list:
            _LOGGER.error("Could not find prices list in response")
            return None
        
        if not isinstance(prices_list, list) or len(prices_list) == 0:
            _LOGGER.error("Prices list is empty or not a list")
            return None
        
        # Debug: Log first item structure
        _LOGGER.debug("First price item keys: %s", list(prices_list[0].keys()))
        _LOGGER.debug("First price item: %s", prices_list[0])
        
        # Store the full prices list
        self._prices_list = prices_list
        
        # Get current time (timezone aware)
        now = dt_util.now()
        _LOGGER.debug("Current time: %s", now)
        
        # Try to find the current price
        # Common field names for timestamp and price
        timestamp_keys = ["timestamp", "date", "datetime", "time", "validFrom", "from", "start"]
        price_keys = ["price", "rate", "tariff", "value", "amount"]
        
        for price_item in prices_list:
            # Find timestamp field
            timestamp = None
            timestamp_key_found = None
            for ts_key in timestamp_keys:
                if ts_key in price_item:
                    timestamp = price_item[ts_key]
                    timestamp_key_found = ts_key
                    break
            
            if timestamp is None:
                continue
            
            # Parse timestamp (could be ISO format string or Unix timestamp)
            try:
                if isinstance(timestamp, str):
                    price_time = dt_util.parse_datetime(timestamp)
                elif isinstance(timestamp, (int, float)):
                    price_time = datetime.fromtimestamp(timestamp, tz=dt_util.DEFAULT_TIME_ZONE)
                else:
                    continue
                
                if price_time is None:
                    continue
                
                # Check if this price is valid for current time
                # Assuming each price is valid until the next one starts
                # Find the next timestamp to determine the validity period
                price_index = prices_list.index(price_item)
                if price_index < len(prices_list) - 1:
                    next_timestamp = prices_list[price_index + 1].get(timestamp_key_found)
                    if next_timestamp:
                        if isinstance(next_timestamp, str):
                            next_time = dt_util.parse_datetime(next_timestamp)
                        else:
                            next_time = datetime.fromtimestamp(next_timestamp, tz=dt_util.DEFAULT_TIME_ZONE)
                        
                        if price_time <= now < next_time:
                            # This is the current price
                            return self._extract_price_value(price_item, price_keys)
                else:
                    # Last item in list, check if it's current
                    if price_time <= now:
                        return self._extract_price_value(price_item, price_keys)
                        
            except Exception as err:
                _LOGGER.debug("Error parsing timestamp: %s", err)
                continue
        
        _LOGGER.warning("No matching price found for current time")
        return None
    
    def _extract_price_value(self, price_item: dict, price_keys: list) -> float | None:
        """Extract the price value from a price item.
        
        Args:
            price_item: The price item dictionary
            price_keys: List of possible price field names
            
        Returns:
            The price value or None if not found
        """
        for price_key in price_keys:
            if price_key in price_item:
                try:
                    price_value = float(price_item[price_key])
                    _LOGGER.debug("Found current price: %s (key: %s)", price_value, price_key)
                    return price_value
                except (ValueError, TypeError) as err:
                    _LOGGER.error("Error converting price to float: %s", err)
        
        _LOGGER.warning("Could not find price field in item: %s", price_item)
        return None

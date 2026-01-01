"""Sensor platform for Essent Dynamic Prices integration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

import async_timeout
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_EURO, UnitOfEnergy, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Essent API endpoint
ESSENT_API_URL = "https://www.essent.nl/api/public/tariffmanagement/dynamic-prices/v1/"
SCAN_INTERVAL = timedelta(minutes=30)


@dataclass
class EssentSensorDescription(SensorEntityDescription):
    """Class describing Essent sensor entities."""
    value_fn: callable = None


# Define all the sensors shown in your screenshot
SENSOR_TYPES: tuple[EssentSensorDescription, ...] = (
    # --- Electricity Sensors ---
    EssentSensorDescription(
        key="electricity_price",
        name="Current electricity price",
        icon="mdi:lightning-bolt",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EssentSensorDescription(
        key="electricity_market_price",
        name="Current electricity market price",
        icon="mdi:lightning-bolt-outline",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EssentSensorDescription(
        key="electricity_price_excl_vat",
        name="Current electricity price excl. VAT",
        icon="mdi:currency-eur",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EssentSensorDescription(
        key="electricity_tax",
        name="Current electricity tax",
        icon="mdi:tax",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EssentSensorDescription(
        key="electricity_vat",
        name="Current electricity VAT",
        icon="mdi:percent",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    
    # --- Gas Sensors ---
    EssentSensorDescription(
        key="gas_price",
        name="Current gas price",
        icon="mdi:fire",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfVolume.CUBIC_METER}",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EssentSensorDescription(
        key="gas_market_price",
        name="Current gas market price",
        icon="mdi:fire-alert",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfVolume.CUBIC_METER}",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    
    # --- Statistics ---
    EssentSensorDescription(
        key="highest_price_today",
        name="Highest electricity price today",
        icon="mdi:chart-line-variant",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EssentSensorDescription(
        key="lowest_price_today",
        name="Lowest electricity price today",
        icon="mdi:chart-line-variant",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    # Create the coordinator to fetch data
    coordinator = EssentDataUpdateCoordinator(hass)
    await coordinator.async_config_entry_first_refresh()

    # Create entities based on the descriptions
    entities = [
        EssentSensor(coordinator, description, config_entry.entry_id)
        for description in SENSOR_TYPES
    ]
    
    async_add_entities(entities)


class EssentDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Essent data."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.session = async_get_clientsession(hass)

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            async with async_timeout.timeout(10):
                response = await self.session.get(ESSENT_API_URL)
                response.raise_for_status()
                data = await response.json()
                _LOGGER.debug("Received data from Essent API: %s", data)
                return self._parse_data(data)
        except Exception as err:
            _LOGGER.error("Error fetching data: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}")

    def _parse_data(self, data: dict) -> dict:
        """Parse the raw API data into a structured dictionary."""
        # NOTE: This logic needs to be adjusted based on the ACTUAL JSON structure
        # For now, we try to find the current price and populate a dict
        
        parsed = {}
        now = dt_util.now()
        
        # Helper to find price list
        prices_list = []
        if isinstance(data, list):
            prices_list = data
        else:
            for key in ["prices", "data", "tariffs", "items"]:
                if key in data and isinstance(data[key], list):
                    prices_list = data[key]
                    break
        
        # Find current price item
        current_item = None
        today_prices = []
        
        for item in prices_list:
            # Parse timestamp (simplified logic)
            ts_str = item.get("readingDate") or item.get("from") or item.get("date")
            if not ts_str:
                continue
                
            try:
                start_time = dt_util.parse_datetime(str(ts_str))
                if not start_time:
                    continue
                
                # Collect for stats
                if start_time.date() == now.date():
                    price = float(item.get("price", item.get("value", 0)))
                    today_prices.append(price)

                # Check if current
                # Assuming 1 hour validity if no end time
                end_time = start_time + timedelta(hours=1)
                if start_time <= now < end_time:
                    current_item = item
            except Exception:
                continue

        # Populate parsed data
        if current_item:
            # Map API fields to our internal keys
            # You will need to adjust these keys based on the real JSON
            parsed["electricity_price"] = float(current_item.get("price", 0))
            parsed["electricity_market_price"] = float(current_item.get("marketPrice", 0))
            parsed["electricity_price_excl_vat"] = float(current_item.get("priceExclVat", 0))
            # ... add other mappings
            
        if today_prices:
            parsed["highest_price_today"] = max(today_prices)
            parsed["lowest_price_today"] = min(today_prices)
            
        return parsed


class EssentSensor(CoordinatorEntity, SensorEntity):
    """Defines an Essent sensor."""

    entity_description: EssentSensorDescription

    def __init__(
        self,
        coordinator: EssentDataUpdateCoordinator,
        description: EssentSensorDescription,
        entry_id: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_name = description.name

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
            
        # Get the value from the parsed data using the key
        return self.coordinator.data.get(self.entity_description.key)

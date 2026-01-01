"""The My Custom Device integration."""
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the My Custom Device integration."""
    _LOGGER.info("My Custom Device integration is loading")
    return True

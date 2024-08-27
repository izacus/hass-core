"""Coordinator for retrieval of OpenHardwareMonitor data."""

from datetime import timedelta
import logging
from typing import Any

import requests

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class OpenHardwareMonitorCoordinator(DataUpdateCoordinator[dict[str, Any] | None]):
    """Coordinator handling data load for a given OWM instance."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=30)
        )
        self.hostname = config_entry.data.get(CONF_HOST)
        self.port = config_entry.data.get(CONF_PORT)

    async def _async_update_data(self):
        try:
            return await self.hass.async_add_executor_job(
                self._get_data, self.hostname, self.port
            )
        except Exception as e:
            raise UpdateFailed("Update failed.") from e

    def _get_data(self, host: str, port: int):
        data_url = f"http://{host}:" f"{port}/data.json"

        try:
            response = requests.get(data_url, timeout=30)
            return response.json()
        except requests.exceptions.ConnectionError:
            _LOGGER.debug("ConnectionError: Is OpenHardwareMonitor running?")
            raise

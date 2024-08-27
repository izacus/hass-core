"""Configuration flow for OpenHardwareMonitor integration."""

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

USER_DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_HOST): cv.string, vol.Optional(CONF_PORT, default=8085): cv.port}
)


class OhmConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Open Hardware Monitor."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure properties for OpenHardwareMonitor integration."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=USER_DATA_SCHEMA)
        return self.async_create_entry(title="OpenHardwareMonitor", data=user_input)

"""Config flow for Sensables.IO IAQ integration.

Version: 1.0.0
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("webhook_id", default="sensables_iaq"): cv.string,
        vol.Required("sensor_prefix", default="sensables"): cv.string,
        vol.Optional("location", default=""): cv.string,
        vol.Required("temperature_unit", default="celsius"): vol.In(["celsius", "fahrenheit"]),
        vol.Required("expire_after", default=3600): cv.positive_int,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.
    
    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # Validate webhook_id format (alphanumeric and underscores only)
    webhook_id = data["webhook_id"]
    if not webhook_id.replace("_", "").isalnum():
        raise InvalidWebhookId
    
    # Validate sensor_prefix format
    sensor_prefix = data["sensor_prefix"]
    if not sensor_prefix.replace("_", "").isalnum():
        raise InvalidSensorPrefix
    
    # Validate expire_after is reasonable (between 60 seconds and 7 days)
    expire_after = data["expire_after"]
    if not (60 <= expire_after <= 604800):  # 60 seconds to 7 days
        raise InvalidExpireAfter

    # Return info that you want to store in the config entry.
    return {
        "title": f"Sensables.IO IAQ ({data['webhook_id']})",
        "webhook_id": webhook_id,
        "sensor_prefix": sensor_prefix,
        "location": data.get("location", "").strip(),
        "temperature_unit": data.get("temperature_unit", "celsius"),
        "expire_after": expire_after,
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sensables.IO IAQ."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except InvalidWebhookId:
                errors["webhook_id"] = "invalid_webhook_id"
            except InvalidSensorPrefix:
                errors["sensor_prefix"] = "invalid_sensor_prefix"
            except InvalidExpireAfter:
                errors["expire_after"] = "invalid_expire_after"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Check if webhook_id is already configured
                await self.async_set_unique_id(user_input["webhook_id"])
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "webhook_url": f"http://your-home-assistant:8123/api/webhook/[webhook_id]"
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Sensables.IO IAQ."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
            except InvalidWebhookId:
                errors["webhook_id"] = "invalid_webhook_id"
            except InvalidSensorPrefix:
                errors["sensor_prefix"] = "invalid_sensor_prefix"
            except InvalidExpireAfter:
                errors["expire_after"] = "invalid_expire_after"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title="", data=user_input)

        # Get current values from config entry
        current_webhook_id = self._config_entry.data.get("webhook_id", "sensables_iaq")
        current_sensor_prefix = self._config_entry.data.get("sensor_prefix", "sensables")
        current_location = self._config_entry.data.get("location", "")
        current_temperature_unit = self._config_entry.data.get("temperature_unit", "celsius")
        current_expire_after = self._config_entry.data.get("expire_after", 3600)

        options_schema = vol.Schema(
            {
                vol.Required("webhook_id", default=current_webhook_id): cv.string,
                vol.Required("sensor_prefix", default=current_sensor_prefix): cv.string,
                vol.Optional("location", default=current_location): cv.string,
                vol.Required("temperature_unit", default=current_temperature_unit): vol.In(["celsius", "fahrenheit"]),
                vol.Required("expire_after", default=current_expire_after): cv.positive_int,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
            description_placeholders={
                "current_webhook_url": f"http://your-home-assistant:8123/api/webhook/{current_webhook_id}"
            },
        )


class InvalidWebhookId(HomeAssistantError):
    """Error to indicate webhook ID is invalid."""


class InvalidSensorPrefix(HomeAssistantError):
    """Error to indicate sensor prefix is invalid."""


class InvalidExpireAfter(HomeAssistantError):
    """Error to indicate expire_after value is invalid."""
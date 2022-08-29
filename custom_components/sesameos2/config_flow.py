"""Config flow for Sesame OS2 integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from pysesameos2.ble import CHBleManager
from pysesameos2.device import CHDeviceKey
from pysesameos2.const import CHDeviceLoginStatus

from bleak.exc import BleakDBusError, BleakError

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("mac_address"): str,
        vol.Required("secret_key"): str,
        vol.Required("pub_key"): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data["username"], data["password"]
    # )

    try:
        device = await CHBleManager().scan_by_address(
            ble_device_identifier=data["mac_address"], scan_duration=15
        )
    except ConnectionRefusedError:
        raise CannotConnect

    if device is None:
        raise CannotConnect

    device_key = CHDeviceKey()
    device_key.setSecretKey(data["secret_key"])
    device_key.setSesame2PublicKey(data["pub_key"])
    device.setKey(device_key)

    retry = 10
    while retry > 0:
        try:
            await device.connect()
            await device.wait_for_login()
            break
        except RuntimeError:
            raise InvalidAuth
        except (BleakDBusError,BleakError):
            retry -= 1
            continue
    # try:
    #     await device.connect()
    #     await device.wait_for_login()
    # except RuntimeError:
    #     raise InvalidAuth
    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    if device.getDeviceStatus().value == CHDeviceLoginStatus.UnLogin:
        _LOGGER.info("[SESAME]Login Failed")
        raise InvalidAuth

    uuid = device.getDeviceUUID()
    await device.disconnect()

    # Return info that you want to store in the config entry.
    return {
        "title": "Sesame OS2",
        "UUID": uuid,
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sesame OS2."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            await self.async_set_unique_id(info["UUID"].replace("-", ""))
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""

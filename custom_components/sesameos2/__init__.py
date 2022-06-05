"""The Sesame OS2 integration."""
from __future__ import annotations

from pysesameos2.ble import CHBleManager
from pysesameos2.device import CHDeviceKey
from pysesameos2.chsesame2 import CHSesame2

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.LOCK]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sesame OS2 from a config entry."""
    # TODO Store an API object for your platforms to access
    # hass.data[DOMAIN][entry.entry_id] = MyApi(...)

    config = entry.data
    device = await CHBleManager().scan_by_address(
        ble_device_identifier=config["mac_address"], scan_duration=15
    )
    device_key = CHDeviceKey()
    device_key.setSecretKey(config["secret_key"])
    device_key.setSesame2PublicKey(config["pub_key"])
    device.setKey(device_key)

    await device.connect()
    await device.wait_for_login()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = device

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        device: CHSesame2 = hass.data[DOMAIN][entry.entry_id]  # CHSesame2
        try:
            await device.disconnect()
        except NotImplementedError:
            pass
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

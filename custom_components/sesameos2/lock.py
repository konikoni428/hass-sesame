"""Support for Sesame, by CANDY HOUSE."""
from __future__ import annotations
import asyncio

from pysesameos2.chsesame2 import CHSesame2
from pysesameos2.device import CHDevices
from pysesameos2.const import CHDeviceLoginStatus, CHSesame2Status

from bleak.exc import BleakDBusError, BleakError

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import ATTR_BATTERY_LEVEL, ATTR_DEVICE_ID

from .const import DOMAIN


def get_model_name(device_model: str):
    """Convert pysesame3 device model to Real device model"""
    if device_model == "sesame_2":
        return "SESAME 3/4"
    elif device_model == "ssmbot_1":
        return "SESAME bot"
    elif device_model == "sesame_4":
        return "SESAME 3/4"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Sesame2 locks based on a config entry."""
    sesame = hass.data[DOMAIN][entry.entry_id]
    locks = []

    s2d = Sesame2Device(hass, sesame)
    await s2d.async_setup()

    locks.append(s2d)

    async_add_entities(locks)


class Sesame2Device(LockEntity):
    """Representation of a Sesame device."""

    def __init__(self, hass: HomeAssistant, sesame: CHSesame2) -> None:
        """Initialize the Sesame device."""
        self._sesame: CHSesame2 = sesame
        self.hass: HomeAssistant = hass

        # Cached properties from pysesame object.
        self._attr_unique_id: str | None = sesame.getDeviceUUID().replace("-", "")
        # self._attr_is_locked = sesame.mechStatus.isInLockRange()
        self._battery: int | None = None
        self.entity_id = f"sesameos2.{self._attr_unique_id}"

    async def async_setup(self) -> None:        
        while self._sesame.getDeviceStatus().value == CHDeviceLoginStatus.UnLogin:
            try:
                await self._sesame.connect()
                await self._sesame.wait_for_login()
            except (BleakDBusError,BleakError):
                pass
                # raise RuntimeError("[SESAME]Login Error")
        
        self._sesame.setDeviceStatusCallback(self._callback)
        self.hass.async_add_executor_job(self.init_update)

    async def async_lock(self, **kwargs) -> None:
        """Lock the lock."""
        await self._sesame.lock(history_tag="hass.io")

    async def async_unlock(self, **kwargs) -> None:
        """Unlock the lock."""
        await self._sesame.unlock(history_tag="hass.io")

    @callback
    def _callback(self, device: CHDevices) -> None:
        """Handle status update received."""
        if device.getDeviceStatus() == CHSesame2Status.NoBleSignal:
            return asyncio.run_coroutine_threadsafe(
                self.async_setup(), self.hass.loop
            )

        status = device.getMechStatus()
        if status is None:
            return
        self._attr_is_locked = status.isInLockRange()
        self._battery = status.getBatteryPercentage()
        self.async_write_ha_state()

    def init_update(self) -> None:
        """Update the internal state of the device."""
        status = self._sesame.getMechStatus()
        self._battery = status.getBatteryPercentage()
        self._attr_is_locked = status.isInLockRange()
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        return {
            # ATTR_DEVICE_ID: self._attr_unique_id,
            # ATTR_SERIAL_NO: self._serial,
            ATTR_BATTERY_LEVEL: self._battery,
        }

    @property
    def device_info(self):
        model = get_model_name(self._sesame.productModel.deviceModel())
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._attr_unique_id)
            },
            "name": f"Sesame {self._attr_unique_id}",
            "manufacturer": "CANDY HOUSE",
            "model": model,
        }

    @property
    def should_poll(self) -> bool:
        return False

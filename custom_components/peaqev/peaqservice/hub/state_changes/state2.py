import logging
import time
from datetime import datetime
from abc import abstractmethod

_LOGGER = logging.getLogger(__name__)


class IStateChanges:
    latest_nordpool_update = 0
    latest_outlet_update = 0

    def __init__(self, hub):
        self._hub = hub

    async def update_sensor(self, entity, value):
        update_session = await self._update_sensor(entity, value)
        if self._hub.options.price.price_aware is True:
            if entity != self._hub.nordpool.nordpool_entity and (not self._hub.hours.is_initialized or time.time() - self.latest_nordpool_update > 60):
                """tweak to provoke nordpool to update more often"""
                self.latest_nordpool_update = time.time()
                await self._hub.nordpool.update_nordpool()
        await self._handle_sensor_attribute()
        if self._hub.charger.session_active and update_session and hasattr(self._hub.sensors, "carpowersensor"):
            self._hub.charger.session.session_energy = self._hub.sensors.carpowersensor.value
            if self._hub.options.price.price_aware is True:
                self._hub.charger.session.session_price = float(self._hub.nordpool.state)
        if self._hub.scheduler.schedule_created is True:
            self._hub.scheduler.update()
        if entity in self._hub.chargingtracker_entities and self._hub.is_initialized:
            await self._hub.charger.charge()

    @abstractmethod
    async def _update_sensor(self, entity, value) -> bool:
        pass

    @abstractmethod
    async def _handle_outlet_updates(self):
        pass

    async def _handle_sensor_attribute(self) -> None:
        if hasattr(self._hub.sensors, "carpowersensor"):
            if self._hub.sensors.carpowersensor.use_attribute:
                entity = self._hub.sensors.carpowersensor
                try:
                    val = self._hub.hass.states.get(entity.entity).attributes.get(entity.attribute)
                    if val is not None:
                        self._hub.sensors.carpowersensor.value = val
                        self._hub.sensors.power.update(
                            carpowersensor_value=self._hub.sensors.carpowersensor.value,
                            config_sensor_value=None
                        )
                    return
                except Exception as e:
                    _LOGGER.debug(f"Unable to get attribute-state for {entity.entity}|{entity.attribute}. {e}")

    async def _update_chargerobject_switch(self, value) -> None:
        self._hub.sensors.chargerobject_switch.value = value
        self._hub.sensors.chargerobject_switch.updatecurrent()
        await self._handle_outlet_updates()

    async def _update_total_energy_and_peak(self, value) -> None:
        self._hub.sensors.totalhourlyenergy.value = value
        self._hub.sensors.current_peak.value = self._hub.sensors.locale.data.query_model.observed_peak
        self._hub.sensors.locale.data.query_model.try_update(
            new_val=float(value),
            timestamp=datetime.now()
        )

import logging
import time
from custom_components.peaqev.peaqservice.hub.state_changes.istate_changes import IStateChanges
from custom_components.peaqev.peaqservice.chargertypes.models.chargertypes_enum import ChargerType

_LOGGER = logging.getLogger(__name__)


class StateChanges(IStateChanges):
    def __init__(self, hub):
        self._hub = hub
        super().__init__(hub)

    async def _update_sensor(self, entity, value) -> bool:
        update_session = False
        match entity:
            case self._hub.configpower_entity:
                self._hub.sensors.power.update(
                    carpowersensor_value=self._hub.sensors.carpowersensor.value,
                    config_sensor_value=value
                )
                update_session = True
                self._hub.power_canary.total_power = self._hub.sensors.power.total.value
            case self._hub.sensors.carpowersensor.entity:
                if self._hub.sensors.carpowersensor.use_attribute:
                    pass
                else:
                    self._hub.sensors.carpowersensor.value = value
                    self._hub.sensors.power.update(
                        carpowersensor_value=self._hub.sensors.carpowersensor.value,
                        config_sensor_value=None
                    )
                update_session = True
                self._hub.sensors.chargerobject_switch.updatecurrent()
                self._hub.power_canary.total_power = self._hub.sensors.power.total.value
                await self._handle_outlet_updates()
            case self._hub.sensors.chargerobject.entity:
                self._hub.sensors.chargerobject.value = value
            case self._hub.sensors.chargerobject_switch.entity:
                await self._update_chargerobject_switch(value)
            case self._hub.sensors.totalhourlyenergy.entity:
                await self._update_total_energy_and_peak(value)
            case self._hub.sensors.powersensormovingaverage.entity:
                self._hub.sensors.powersensormovingaverage.value = value
            case self._hub.sensors.powersensormovingaverage24.entity:
                self._hub.sensors.powersensormovingaverage24.value = value
            case self._hub.nordpool.nordpool_entity:
                await self._hub.nordpool.update_nordpool()
                update_session = True
        return update_session
    
    async def _handle_outlet_updates(self):
        if self._hub.chargertype.domainname is ChargerType.Outlet:
            old_state = self._hub.sensors.chargerobject.value
            if time.time() - self.latest_outlet_update < 10:
                return
            self.latest_outlet_update = time.time()
            if self._hub.sensors.carpowersensor.value > 0:
                self._hub.sensors.chargerobject.value = "charging"
            else:
                self._hub.sensors.chargerobject.value = "connected"
            if old_state != self._hub.sensors.chargerobject.value:
                _LOGGER.debug(f"smartoutlet is now {self._hub.sensors.chargerobject.value}")


class StateChangesLite(IStateChanges):
    def __init__(self, hub):
        self._hub = hub
        super().__init__(hub)

    async def _update_sensor(self, entity, value) -> bool:
        match entity:
            case self._hub.sensors.carpowersensor.entity:
                if self._hub.sensors.carpowersensor.use_attribute:
                    pass
                else:
                    self._hub.sensors.carpowersensor.value = value
                    await self._handle_outlet_updates()
                    self._hub.sensors.chargerobject_switch.updatecurrent()
            case self._hub.sensors.chargerobject.entity:
                self._hub.sensors.chargerobject.value = value
            case self._hub.sensors.chargerobject_switch.entity:
                await self._update_chargerobject_switch(value)
            case self._hub.sensors.current_peak.entity:
                self._hub.sensors.current_peak.value = value
            case self._hub.sensors.totalhourlyenergy.entity:
                await self._update_total_energy_and_peak(value)
            case self._hub.nordpool.nordpool_entity:
                await self._hub.nordpool.update_nordpool()
        return False
    
    async def _handle_outlet_updates(self):
        if self._hub.chargertype.domainname is ChargerType.Outlet:
            old_state = self._hub.sensors.chargerobject.value
            if time.time() - self.latest_outlet_update < 10:
                return
            self.latest_outlet_update = time.time()
            if self._hub.sensors.carpowersensor.value > 0:
                self._hub.sensors.chargerobject.value = "charging"
            else:
                self._hub.sensors.chargerobject.value = "connected"
            if old_state != self._hub.sensors.chargerobject.value:
                _LOGGER.debug(f"smartoutlet is now {self._hub.sensors.chargerobject.value}")


class StateChangesNoCharger(IStateChanges):
    def __init__(self, hub):
        self._hub = hub
        super().__init__(hub)

    async def _update_sensor(self, entity, value) -> bool:
        update_session = False
        match entity:
            case self._hub.configpower_entity:
                self._hub.sensors.power.update(
                    carpowersensor_value=0,
                    config_sensor_value=value
                )
                update_session = True
                self._hub.power_canary.total_power = self._hub.sensors.power.total.value
            case self._hub.sensors.totalhourlyenergy.entity:
                await self._update_total_energy_and_peak(value)
            case self._hub.sensors.powersensormovingaverage.entity:
                self._hub.sensors.powersensormovingaverage.value = value
            case self._hub.sensors.powersensormovingaverage24.entity:
                self._hub.sensors.powersensormovingaverage24.value = value
            case self._hub.nordpool.nordpool_entity:
                await self._hub.nordpool.update_nordpool()
                update_session = True
        return update_session


class StateChanges2:
    def __init__(self, hub):
        self._hub = hub
        self._funcs = {}

    def _set_value(func, val) -> None:
        func = val

    def _set_powersensor_moving_average(self) -> None:
        self._funcs[self._hub.sensors.powersensormovingaverage.entity] = lambda x: self._set_value(self._hub.sensors.powersensormovingaverage.value, x)
        self._funcs[self._hub.sensors.powersensormovingaverage24.entity] = lambda x: self._set_value(self._hub.sensors.powersensormovingaverage24.value, x)
    
    def _set_total_hourly_energy(self) -> None:
        self._funcs[self._hub.sensors.totalhourlyenergy.entity] = lambda x: self._update_total_energy_and_peak(x)

    def _set_nordpool(self) -> None:
        self._funcs[self._hub.nordpool.nordpool_entity] = lambda : self._hub.nordpool.update_nordpool()
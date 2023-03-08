import logging
import time
from abc import abstractmethod
from datetime import datetime, timedelta

from peaqevcore.models.chargecontroller_states import ChargeControllerStates

from custom_components.peaqev.peaqservice.chargertypes.models.chargertypes_enum import ChargerType
from custom_components.peaqev.peaqservice.util.constants import CHARGERCONTROLLER

_LOGGER = logging.getLogger(__name__)

DONETIMEOUT = 180
DEBUGLOG_TIMEOUT = 60


class IChargeController:
    def __init__(self, hub, charger_states):
        super().__init__()
        self._hub = hub
        self.name: str = f"{self._hub.hubname} {CHARGERCONTROLLER}"
        self._status_type: ChargeControllerStates = ChargeControllerStates.Idle
        self._is_initalized: bool = False
        self._latest_charger_start = time.time()
        self._latest_debuglog = 0
        self._charger_states: dict = charger_states

    @property
    def status_type(self) -> ChargeControllerStates:
        return self._status_type

    @status_type.setter
    def status_type(self, val) -> None:
        if val != self._status_type:
            self._hub.observer.broadcast("chargecontroller status changed")
            self._status_type = val

    @property
    def latest_charger_start(self) -> float:
        return self._latest_charger_start

    @latest_charger_start.setter
    def latest_charger_start(self, val):
        self._latest_charger_start = val

    @property
    def status(self) -> str:
        ret = ChargeControllerStates.Error
        if not self.is_initialized:
            return "Hub not ready. Check logs!"
        match self._hub.chargertype.type:
            case ChargerType.Outlet:
                ret = self._get_status_outlet()
            case ChargerType.NoCharger:
                ret = self._get_status_no_charger()
            case _:
                ret = self._get_status()
        self._status_type = ret
        return ret.name

    @property
    def is_initialized(self) -> bool:
        if not self._hub.is_initialized:
            return False
        if self._hub.is_initialized and not self._is_initalized:
            self._is_initalized = True
            self.__debug_log("Chargecontroller is initialized and ready to work!")
        return True

    @property
    def non_hours_display_model(self) -> list:
        ret = []
        for i in self._hub.non_hours:
            if i < datetime.now().hour and len(self._hub.prices_tomorrow) > 0:
                ret.append(f"{str(i)}⁺¹")
            elif i >= datetime.now().hour:
                ret.append(str(i))
        return ret

    @property
    def caution_hours_display_model(self) -> dict:
        ret = {}
        if len(self._hub.dynamic_caution_hours) > 0:
            for h in self._hub.dynamic_caution_hours:
                if h < datetime.now().hour:
                    hh = f"{h}⁺¹"
                else:
                    hh = h
                ret[hh] = f"{str((int(self._hub.dynamic_caution_hours[h] * 100)))}%"
        return ret

    @property
    def current_charge_permittance_display_model(self) -> str:
        ret = 100
        hour = datetime.now().hour
        if hour in self._hub.non_hours:
            ret = 0
        elif hour in self._hub.dynamic_caution_hours.keys():
            ret = int(self._hub.dynamic_caution_hours.get(hour) * 100)
        return f"{str(ret)}%"

    @property
    def state_display_model(self) -> str:
        hour = datetime.now().hour
        ret = "Charging allowed"
        if self._hub.timer.is_override:  #todo: composition
            return self._hub.timer.override_string  #todo: composition
        if hour in self._hub.non_hours:
            ret = self._calculate_stop_len(self._hub.non_hours)
        elif hour in self._hub.dynamic_caution_hours.keys():
            val = self._hub.dynamic_caution_hours.get(hour)
            ret = f"Charging allowed at {int(val * 100)}% of peak"
        return ret

    def _get_status_outlet(self) -> ChargeControllerStates:
        ret = ChargeControllerStates.Error
        update_timer = False

        if not self._hub.enabled:
            update_timer = True
            ret = ChargeControllerStates.Disabled
        elif self._hub.charger_done:
            ret = ChargeControllerStates.Done
        elif datetime.now().hour in self._hub.non_hours and self._hub.timer.is_override is False:  #todo: composition
            update_timer = True
            ret = ChargeControllerStates.Stop
        elif self._hub.chargertype.entities.powerswitch == "on" and self._hub.chargertype.entities.powermeter < 1:  #todo: composition
            ret = self._get_status_connected()
            update_timer = (ret == ChargeControllerStates.Stop)
        else:
            ret = self._get_status_charging()
            update_timer = True
        if update_timer is True:
            self.latest_charger_start = time.time()
        return ret

    def _get_status(self) -> ChargeControllerStates:
        _state = self._hub.get_chargerobject_value()
        ret = ChargeControllerStates.Error
        update_timer = True

        if not self._hub.enabled:
            ret = ChargeControllerStates.Disabled
        elif _state in self._charger_states.get(ChargeControllerStates.Done):
            self._hub.observer.broadcast("update charger done", True)
            ret = ChargeControllerStates.Done
            update_timer = False
        elif _state in self._charger_states.get(ChargeControllerStates.Idle):
            ret = ChargeControllerStates.Idle
            if self._hub.charger_done:
                self._hub.observer.broadcast("update charger done", False)
        elif self._hub.sensors.power.killswitch.is_dead:  #todo: composition
            ret = ChargeControllerStates.Error
        elif _state not in self._charger_states.get(ChargeControllerStates.Idle) and self._hub.charger_done:
            ret = ChargeControllerStates.Done
            update_timer = False
        elif datetime.now().hour in self._hub.non_hours and not self._hub.timer.is_override:  #todo: composition
            ret = ChargeControllerStates.Stop
        elif _state in self._charger_states.get(ChargeControllerStates.Connected):
            ret = self._get_status_connected(_state)
            update_timer = (ret == ChargeControllerStates.Stop)
        elif _state in self._charger_states.get(ChargeControllerStates.Charging):
            ret = self._get_status_charging()
        if update_timer:
            self.latest_charger_start = time.time()
        if ret == ChargeControllerStates.Error:
            _LOGGER.error(f"Chargecontroller returned faulty state. Charger reported {self._hub.get_chargerobject_value()} as state.")
        return ret

    def _get_status_no_charger(self) -> ChargeControllerStates:
        ret = ChargeControllerStates.Error
        update_timer = True

        if not self._hub.enabled:
            ret = ChargeControllerStates.Disabled
        elif datetime.now().hour in self._hub.non_hours and not self._hub.timer.is_override:
            ret = ChargeControllerStates.Stop
        else:
            ret = ChargeControllerStates.Start
        if update_timer:
            self.latest_charger_start = time.time()
        return ret

    def _is_done(self, charger_state) -> bool:
        if len(self._charger_states.get(ChargeControllerStates.Done)) > 0:
            _states_test = charger_state in self._charger_states.get(ChargeControllerStates.Done)
            if _states_test:
                self.__debug_log(f"'is_done' reported that charger is Done based on current charger state")
            return _states_test
        _regular_test = time.time() - self.latest_charger_start > DONETIMEOUT
        if _regular_test:
            self.__debug_log(f"'is_done' reported that charger is Done because of idle-charging for more than {DONETIMEOUT} seconds.")
        return _regular_test

    def __debug_log(self, message: str):
        if time.time() - self._latest_debuglog > DEBUGLOG_TIMEOUT:
            _LOGGER.debug(message)
            self._latest_debuglog = time.time()

    @staticmethod
    def _defer_start(non_hours: list) -> bool:
        """Defer starting if next hour is a non-hour and minute is 50 or greater, to avoid short running times."""
        if (datetime.now() + timedelta(hours=1)).hour in non_hours:
            return datetime.now().minute >= 50
        return False

    @abstractmethod
    def _get_status_charging(self) -> ChargeControllerStates:
        pass

    @abstractmethod
    def _get_status_connected(self, charger_state=None) -> ChargeControllerStates:
        pass

    @staticmethod
    def _get_stopped_string(h) -> str:
        val = h + 1 if h + 1 < 24 else h + 1 - 24
        if len(str(val)) == 1:
            return f"Charging stopped until 0{val}:00"
        return f"Charging stopped until {val}:00"

    @staticmethod
    def _getuneven(first, second) -> bool:
        if second > first:
            return first - (second - 24) != 1
        return first - second != 1

    @staticmethod
    def _calculate_stop_len(nonhours) -> str:
        ret = ""
        for idx, h in enumerate(nonhours):
            if idx + 1 < len(nonhours):
                if IChargeController._getuneven(nonhours[idx + 1], nonhours[idx]):
                    ret = IChargeController._get_stopped_string(h)
                    break
            elif idx + 1 == len(nonhours):
                ret = IChargeController._get_stopped_string(h)
                break
        return ret

import logging
import time
from datetime import datetime

from custom_components.peaqev.peaqservice.chargecontroller.chargecontrollerbase import ChargeControllerBase
from custom_components.peaqev.peaqservice.util.chargerstates import CHARGECONTROLLER
from custom_components.peaqev.peaqservice.util.constants import CHARGERCONTROLLER

_LOGGER = logging.getLogger(__name__)
DONETIMEOUT = 180


class ChargeController(ChargeControllerBase):
    def __init__(self, hub):
        self._hub = hub
        self.name = f"{self._hub.hubname} {CHARGERCONTROLLER}"
        self._status = CHARGECONTROLLER.Idle
        self._latestchargerstart = time.time()

    @property
    def latest_charger_start(self) -> float:
        return self._latestchargerstart

    @latest_charger_start.setter
    def latest_charger_start(self, val):
        self._latestchargerstart = val

    @property
    def below_startthreshold(self) -> bool:
        return self._below_startthreshold(
            predicted_energy=self._hub.prediction.predictedenergy,
            current_peak=self._hub.currentpeak.value,
            threshold_start=self._hub.threshold.start
        )

    @property
    def above_stopthreshold(self) -> bool:
        return self._above_stopthreshold(
            predicted_energy=self._hub.prediction.predictedenergy,
            current_peak=self._hub.currentpeak.value,
            threshold_stop=self._hub.threshold.stop
        )

    @property
    def status(self):
        return self._get_status()

    def update_latestchargerstart(self):
        self.latest_charger_start = time.time()

    def _get_status(self):
        ret = CHARGECONTROLLER.Error
        update_timer = False
        charger_state = self._hub.chargerobject.value.lower()

        # return self._let_charge(
        #     charger_state = self._hub.chargerobject.value.lower(),
        #     charger_enabled = self._hub.charger_enabled.value,
        #     charger_done = self._hub.charger_done.value,
        #     total_hourly_energy = self._hub.totalhourlyenergy.value,
        #     car_power_sensor = self._hub.carpowersensor.value,
        #     non_hours = self._hub.nonhours,
        #     now_hour = datetime.now().hour,
        #     charger_states = self._hub.chargertype.charger.chargerstates
        # )

        if charger_state in self._hub.chargertype.charger.chargerstates[CHARGECONTROLLER.Idle]:
            update_timer = True
            ret = CHARGECONTROLLER.Idle
        elif charger_state in self._hub.chargertype.charger.chargerstates[CHARGECONTROLLER.Connected] and self._hub.charger_enabled.value is False:
            update_timer = True
            ret = CHARGECONTROLLER.Connected
        elif charger_state not in self._hub.chargertype.charger.chargerstates[CHARGECONTROLLER.Idle] and self._hub.charger_done.value is True:
            ret = CHARGECONTROLLER.Done
        elif datetime.now().hour in self._hub.non_hours:
            update_timer = True
            ret = CHARGECONTROLLER.Stop
        elif charger_state in self._hub.chargertype.charger.chargerstates[CHARGECONTROLLER.Connected]:
            if self._hub.carpowersensor.value < 1 and time.time() - self.latest_charger_start > DONETIMEOUT:
                ret = CHARGECONTROLLER.Done
            else:
                if self.below_startthreshold and self._hub.totalhourlyenergy.value > 0:
                    ret = CHARGECONTROLLER.Start
                else:
                    update_timer = True
                    ret = CHARGECONTROLLER.Stop
        elif charger_state in self._hub.chargertype.charger.chargerstates[CHARGECONTROLLER.Charging]:
            update_timer = True
            if self.above_stopthreshold and self._hub.totalhourlyenergy.value > 0:
                ret = CHARGECONTROLLER.Stop
            else:
                ret = CHARGECONTROLLER.Start

        if update_timer is True:
            self.update_latestchargerstart()
        return ret



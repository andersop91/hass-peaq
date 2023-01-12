import logging
import time

from homeassistant.core import HomeAssistant
from peaqevcore.hub.hub_options import HubOptions
from peaqevcore.models.chargerstates import CHARGERSTATES
from peaqevcore.models.chargertype.calltype import CallType
from peaqevcore.models.chargertype.servicecalls_dto import ServiceCallsDTO
from peaqevcore.models.chargertype.servicecalls_options import ServiceCallsOptions
from peaqevcore.services.chargertype.chargertype_base import ChargerBase

import custom_components.peaqev.peaqservice.chargertypes.entitieshelper as helper
from custom_components.peaqev.peaqservice.chargertypes.models.entities_postmodel import EntitiesPostModel
from custom_components.peaqev.peaqservice.util.constants import (
    CHARGER,
    CHARGERID,
    CURRENT,
)

_LOGGER = logging.getLogger(__name__)
# docs: https://github.com/fondberg/easee_hass


class Easee(ChargerBase):
    def __init__(self, hass: HomeAssistant, huboptions: HubOptions, auth_required: bool = False):
        self._hass = hass
        self._chargerid = huboptions.charger.chargerid
        self._auth_required = auth_required
        self.options.powerswitch_controls_charging = False
        self.entities.imported_entityendings = self.entity_endings
        self.chargerstates[CHARGERSTATES.Idle] = ["disconnected"]
        self.chargerstates[CHARGERSTATES.Connected] = ["awaiting_start", "ready_to_charge"]
        self.chargerstates[CHARGERSTATES.Charging] = ["charging"]
        self.chargerstates[CHARGERSTATES.Done] = ["completed"]

        entitiesobj = helper.set_entitiesmodel(
            self._hass,
            EntitiesPostModel(
                self.domain_name,
                self.entities.entityschema,
                self.entities.imported_entityendings
            )
        )
        self.entities.imported_entities = entitiesobj.imported_entities
        self.entities.entityschema = entitiesobj.entityschema

        self.set_sensors()
        self.max_amps = self.get_allowed_amps()

        self._set_servicecalls(
            domain=self.domain_name,
            model=ServiceCallsDTO(
                on= self.call_on if self._auth_required is True else self.call_resume,
                off= self.call_off if self._auth_required is True else self.call_pause,
                pause= self.call_pause,
                resume=self.call_resume,
                update_current=self.call_update_current
            ),
            options=self.servicecalls_options
        )

    @property
    def domain_name(self) -> str:
        """declare the domain name as stated in HA"""
        return "easee"

    @property
    def entity_endings(self) -> list:
        """declare a list of strings with sensor-endings to help peaqev find the correct sensor-schema."""
        return [
            "_dimmer", "_downlight",
            "_current", "_voltage",
            "_output_limit", "_cost_per_kwh",
            "_enable_idle_current", "_is_enabled",
            "_cable_locked_permanently", "_smart_charging",
            "_max_charger_limit", "_energy_per_hour",
            "_lifetime_energy", "_session_energy",
            "_power", "_status",
            "_online", "_cable_locked"
        ]

    @property
    def native_chargerstates(self) -> list:
        """declare a list of the native-charger states available for the type."""
        return [
            "disconnected",
            "awaiting_start",
            "charging",
            "ready_to_charge",
            "completed",
            "error"
        ]

    @property
    def call_on(self) -> CallType:
        return CallType("action_command", {
            "charger_id":     self._chargerid,
            "action_command": "start"
        })

    @property
    def call_off(self) -> CallType:
        return CallType("action_command", {
            "charger_id":     self._chargerid,
            "action_command": "stop"
        })

    @property
    def call_resume(self) -> CallType:
        return CallType("set_charger_dynamic_limit", {
            "current": "7",
            "charger_id": self._chargerid
        })

    @property
    def call_pause(self) -> CallType:
        return CallType("set_charger_dynamic_limit", {
            "current": "0",
            "charger_id": self._chargerid
        })

    @property
    def call_update_current(self) -> CallType:
        return CallType("set_charger_dynamic_limit", {
            CHARGER:   "charger_id",
            CHARGERID: self._chargerid,
            CURRENT:   "current"
        })

    @property
    def servicecalls_options(self) -> ServiceCallsOptions:
        return ServiceCallsOptions(
                allowupdatecurrent=True,
                update_current_on_termination=False,
                switch_controls_charger=False
            )

    def getentities(self, domain: str = None, endings: list = None):
        if len(self.entities.entityschema) < 1:
            domain = self.domain_name if domain is None else domain
            endings = self.entities.imported_entityendings if endings is None else endings

            entities = helper.get_entities_from_hass(self._hass, domain)

            if len(entities) < 1:
                _LOGGER.error(f"no entities found for {domain} at {time.time()}")
            else:
                _endings = endings
                candidate = ""

                for e in entities:
                    splitted = e.split(".")
                    for ending in _endings:
                        if splitted[1].endswith(ending):
                            candidate = splitted[1].replace(ending, '')
                            break
                    if len(candidate) > 1:
                        break

                if candidate == "":
                    _LOGGER.exception(f"Unable to find valid sensorschema for your {domain}.")
                else:
                    self.entities.entityschema = candidate
                    _LOGGER.debug(f"entityschema is: {self.entities.entityschema} at {time.time()}")
                    self.entities.imported_entities = entities

    def set_sensors(self):
        amp_sensor = f"sensor.{self.entities.entityschema}_dynamic_charger_limit"
        if not self._validate_sensor(amp_sensor):
            amp_sensor = f"sensor.{self.entities.entityschema}_max_charger_limit"
        self.entities.maxamps = f"sensor.{self.entities.entityschema}_max_charger_limit"
        self.entities.chargerentity = f"sensor.{self.entities.entityschema}_status"
        self.entities.powermeter = f"sensor.{self.entities.entityschema}_power"
        self.options.powermeter_factor = 1000
        self.entities.powerswitch = f"switch.{self.entities.entityschema}_is_enabled"
        self.entities.ampmeter = amp_sensor
        self.options.ampmeter_is_attribute = False

    def get_allowed_amps(self) -> int:
        try:
            ret = self._hass.states.get(self.entities.maxamps)
            if ret is not None:
                return int(ret.state)
            return 16
        except:
            _LOGGER.warning("Unable to get max amps for circuit. Setting max amps to 16.")
            return 16

    def _validate_sensor(self, sensor: str) -> bool:
        ret = self._hass.states.get(sensor)
        if ret is None:
            return False
        if ret.state == "Null":
            return False
        return True

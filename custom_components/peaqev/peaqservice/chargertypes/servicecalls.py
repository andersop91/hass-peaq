import logging

from custom_components.peaqev.peaqservice.chargertypes.calltype import CallType
from custom_components.peaqev.peaqservice.util.constants import (
    DOMAIN,
    ON,
    OFF,
    RESUME,
    PAUSE,
    PARAMS,
    UPDATECURRENT,
)

_LOGGER = logging.getLogger(__name__)


class ServiceCalls:
    def __init__(
            self,
            domain: str,
            on_call: CallType,
            off_call: CallType,
            pause_call: CallType = None,
            resume_call: CallType = None,
            allowupdatecurrent: bool = False,
            update_current_call: str = None,
            update_current_params: dict = None,
            update_current_on_termination: bool = False
    ):
        self._domain = domain
        self._allowupdatecurrent = allowupdatecurrent
        self._update_current_on_termination = update_current_on_termination
        self._on = on_call
        self._off = off_call
        self._pause = pause_call if pause_call is not None else off_call
        self._resume = resume_call if resume_call is not None else on_call
        self._update_current = CallType(update_current_call, update_current_params)
        self._validate_servicecalls()

    @property
    def allowupdatecurrent(self) -> bool:
        return self._allowupdatecurrent

    @property
    def allow_update_current_on_termination(self) -> bool:
        return self._update_current_on_termination

    @property
    def domain(self) -> str:
        return self._domain

    @property
    def on(self) -> CallType:
        return self._on

    @property
    def off(self) -> CallType:
        return self._off

    @property
    def pause(self) -> CallType:
        return self._pause

    @property
    def resume(self) -> CallType:
        return self._resume

    @property
    def update_current(self) -> CallType:
        return self._update_current

    def get_call(self, call) -> dict:
        ret = {}
        ret[DOMAIN] = self.domain
        calltype = self._get_call_type(call)
        ret[call] = calltype.call
        ret["params"] = calltype.params
        if call is UPDATECURRENT:
            ret[PARAMS] = self.update_current.params
        return ret

    def _get_call_type(self, call) -> CallType:
        _callsdict = {
            ON: self.on,
            OFF: self.off,
            PAUSE: self.pause,
            RESUME: self.resume,
            UPDATECURRENT: self.update_current
        }
        return _callsdict.get(call)

    def _validate_servicecalls(self):
        pass
        #assertions = [self.domain.call, self.on.call, self.off.call, self.pause.call, self.resume.call]
        #try:
        #    for a in assertions:
        #        assert len(a) > 0
        #except Exception as e:
        #    _LOGGER.error("Peaqev could not initialize servicecalls", e)

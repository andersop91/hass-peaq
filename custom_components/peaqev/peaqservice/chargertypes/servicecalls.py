import logging

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


class CallType:
    def __init__(self, call: str, params: dict = {}):
        self._call = call
        self._params = params

    @property
    def call(self) -> str:
        return self._call

    @property
    def params(self) -> dict:
        return self._params


class ServiceCalls:
    def __init__(
            self,
            domain: str,
            on_call: str,
            off_call: str,
            pause_call: str = None,
            resume_call: str = None,
            on_off_params: dict = {},
            allowupdatecurrent: bool = False,
            update_current_call: str = None,
            update_current_params: dict = None,
    ):
        self._domain = domain
        self._allowupdatecurrent = allowupdatecurrent
        self._on = CallType(on_call, on_off_params)
        self._off = CallType(off_call, on_off_params)
        self._pause = CallType(pause_call if pause_call is not None else off_call, on_off_params)
        self._resume = CallType(resume_call if resume_call is not None else on_call, on_off_params)
        self._update_current = CallType(update_current_call, update_current_params)
        self._validate_servicecalls()

    @property
    def allowupdatecurrent(self) -> bool:
        return self._allowupdatecurrent

    @property
    def domain(self) -> CallType:
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
        ret[call] = self._get_call_type(call)
        ret["params"] = self._get_call_type_params(call)
        if call is UPDATECURRENT:
            ret[PARAMS] = self.update_current.params
        return ret

    def _get_call_type_params(self, call) -> dict:
        _callsdict = {
            ON: self.on.params,
            OFF: self.off.params,
            PAUSE: self.pause.params,
            RESUME: self.resume.params
        }
        return _callsdict.get(call)

    def _get_call_type(self, call):
        _callsdict = {
            ON: self.on.call,
            OFF: self.off.call,
            PAUSE: self.pause.call,
            RESUME: self.resume.call,
            UPDATECURRENT: self.update_current.call
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

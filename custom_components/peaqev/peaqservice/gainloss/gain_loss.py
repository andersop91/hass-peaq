from peaqevcore.models.locale.enums.time_periods import TimePeriods
import logging

CONSUMPTION = "consumption"
COST = "cost"

_LOGGER = logging.getLogger(__name__)

class GainLoss:
    def __init__(self, hub):
        self._daily_average: float = None
        self._monthly_average: float = None
        self._hub = hub
        self._hub.observer.add("monthly average price changed", self._update_monthly_average)
        self._hub.observer.add("daily average price changed", self._update_daily_average)
        # self.entities = {
        #     TimePeriods.Daily: {
        #         CONSUMPTION: "sensor.peaqev_energy_including_car_daily",
        #         COST: "sensor.peaqev_energy_cost_integral_daily"
        #     },
        #     TimePeriods.Monthly: {
        #         CONSUMPTION: "sensor.peaqev_energy_including_car_monthly",
        #         COST: "sensor.peaqev_energy_cost_integral_monthly"
        #     }
        # }

    def state(self, time_period: TimePeriods) -> float:
        ret = 0
        consumption = self._hub.state_machine.states.get(self._get_entity(time_period, CONSUMPTION))
        cost = self._hub.state_machine.states.get(self._get_entity(time_period, COST))
        if consumption is not None and cost is not None:
            if any([
                consumption.state == "unknown",
                cost.state == "unknown"
            ]):
                #_LOGGER.debug("consumption or cost was state 'unknown'")
                return ret
            average = self._get_average(time_period)
            cost_divided = float(cost.state)# / 1000
            consumptionf = float(consumption.state)
            if consumptionf > 0 and cost_divided > 0 and average is not None:
                net = cost_divided / consumptionf
                ret = round((net / average) - 1,4)
                _LOGGER.debug(f"calculating ret-{time_period.value} {ret} for consumption: {consumptionf}, cost: {cost_divided}, average: {average}")
            # else:
            #     _LOGGER.debug(f"consumption: {consumptionf}, cost: {cost_divided}, average: {average}")
        return ret

    def _update_monthly_average(self, val):
        if isinstance(val, float):
            self._monthly_average = val

    def _update_daily_average(self, val):
        if isinstance(val, float):
            self._daily_average = val

    def _get_monthly_average(self)-> float:
        return self._monthly_average

    def _get_daily_average(self) -> float:
        return self._daily_average

    def _get_average(self, time_period: TimePeriods) -> float:
        ret = {
            TimePeriods.Monthly: self._get_monthly_average,
            TimePeriods.Daily: self._get_daily_average
        }
        return ret.get(time_period)()

    @staticmethod
    def _get_entity(time_period: TimePeriods, resulttype: str):
        ret = {
            TimePeriods.Daily:   {
                CONSUMPTION: "sensor.peaqev_energy_including_car_daily",
                COST:        "sensor.peaqev_energy_cost_integral_daily"
            },
            TimePeriods.Monthly: {
                CONSUMPTION: "sensor.peaqev_energy_including_car_monthly",
                COST:        "sensor.peaqev_energy_cost_integral_monthly"
            }
        }
        return ret.get(time_period).get(resulttype)
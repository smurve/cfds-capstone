import logging
from .Clock import Clock
from .abstract import AbstractStatistician, AbstractParticipant


class Statistician(AbstractStatistician):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_chart_data(self, **queryargs):
        self.logger.debug(f"{self.osid()}: get_chart_data not implemented yet.")

    def report_transaction(self, symbol: str, volume: float, price: float, clock: Clock):
        self.logger.debug(f"{self.osid()}: report_transaction not implemented yet.")

    def register_participant(self, other_participant: AbstractParticipant, **kwargs):
        self.logger.error(f"{self.osid()}: Statisticians don't register other participants")

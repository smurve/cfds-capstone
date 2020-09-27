from typing import List
import ray

from . import AbstractMarketScenario
from .AbstractInvestor import AbstractInvestor
from ..ray import RayInvestor


class SynchronousMarketScenario(AbstractMarketScenario):

    def __init__(self):
        self.investors: List[AbstractInvestor] = []

    def register_investors(self, *investors):
        self.investors += investors

    def tick(self):
        for investor in self.investors:
            investor.tick()

    def identify_investors(self):
        return [inv.identify() for inv in self.investors]

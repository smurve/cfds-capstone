from typing import List
import ray

from . import AbstractMarketScenario
from .AbstractInvestor import AbstractInvestor
from ..ray import RayInvestor


class RayMarketScenario(AbstractMarketScenario):

    def __init__(self):
        self.investors: List[AbstractInvestor] = []

    def register_investors(self, *investors):
        self.investors += [RayInvestor.remote(investor)
                           for investor in investors]

    def tick(self):
        for investor in self.investors:
            investor.tick()

    def identify_investors(self):
        return [ray.get(inv.identify.remote())  # noqa (remote not recognized)
                for inv in self.investors]
